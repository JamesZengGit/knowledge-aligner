"""
Database Manager for Knowledge Aligner
Replaces in-memory simple_server.py with PostgreSQL backend
Maintains existing API compatibility while adding production capabilities
"""

import asyncio
import asyncpg
import json
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

try:
    from .hybrid_retrieval import HybridRetrieval
    from .entity_extraction import EntityExtractor
except ImportError:
    # Direct imports when running as script
    from hybrid_retrieval import HybridRetrieval
    from entity_extraction import EntityExtractor

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Production database manager with connection pooling
    Replaces mock data with PostgreSQL + pgvector
    """

    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv(
            'DATABASE_URL',
            'postgresql://postgres:postgres@localhost:5432/knowledge_aligner'
        )
        self.db_pool = None
        self.retriever = None
        self.extractor = None

    async def init_pool(self):
        """Initialize database connection pool"""
        if not self.db_pool:
            self.db_pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                command_timeout=30
            )

            # Initialize retrieval and extraction systems
            self.retriever = HybridRetrieval()
            await self.retriever.init_db_pool(self.database_url)

            self.extractor = EntityExtractor()
            await self.extractor.init_claude_client()
            await self.extractor.init_db_pool(self.database_url)

            logger.info("Database manager initialized")

    @asynccontextmanager
    async def get_connection(self):
        """Context manager for database connections"""
        if not self.db_pool:
            await self.init_pool()

        async with self.db_pool.acquire() as conn:
            yield conn

    # User Management
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile by ID"""
        async with self.get_connection() as conn:
            row = await conn.fetchrow("""
                SELECT user_id, user_name, role, owned_components, email
                FROM user_profiles
                WHERE user_id = $1
            """, user_id)

            return dict(row) if row else None

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all user profiles"""
        async with self.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT user_id, user_name, role, owned_components, email
                FROM user_profiles
                ORDER BY user_name
            """)

            return [dict(row) for row in rows]

    # Decision Management
    async def get_decisions(self,
                           user_id: str = None,
                           limit: int = 50,
                           offset: int = 0) -> List[Dict[str, Any]]:
        """Get decisions with optional user filtering"""
        async with self.get_connection() as conn:
            if user_id:
                # Filter by user's owned components
                user = await self.get_user(user_id)
                if not user:
                    return []

                query = """
                    SELECT decision_id, thread_id, timestamp, author_user_id, author_name,
                           author_role, decision_type, decision_text, affected_components,
                           referenced_reqs, similarity_score, before_after
                    FROM decisions
                    WHERE affected_components && $1
                    ORDER BY timestamp DESC
                    LIMIT $2 OFFSET $3
                """
                rows = await conn.fetch(query, user['owned_components'], limit, offset)
            else:
                query = """
                    SELECT decision_id, thread_id, timestamp, author_user_id, author_name,
                           author_role, decision_type, decision_text, affected_components,
                           referenced_reqs, similarity_score, before_after
                    FROM decisions
                    ORDER BY timestamp DESC
                    LIMIT $1 OFFSET $2
                """
                rows = await conn.fetch(query, limit, offset)

            # Convert to dictionaries and handle JSON fields
            decisions = []
            for row in rows:
                decision = dict(row)
                # Convert arrays and JSON properly
                decision['affected_components'] = list(decision['affected_components'])
                decision['referenced_reqs'] = list(decision['referenced_reqs']) if decision['referenced_reqs'] else []
                decision['before_after'] = decision['before_after'] or {}
                decisions.append(decision)

            return decisions

    async def get_decision(self, decision_id: int) -> Optional[Dict[str, Any]]:
        """Get single decision by ID"""
        async with self.get_connection() as conn:
            row = await conn.fetchrow("""
                SELECT decision_id, thread_id, timestamp, author_user_id, author_name,
                       author_role, decision_type, decision_text, affected_components,
                       referenced_reqs, similarity_score, before_after, embedding_status
                FROM decisions
                WHERE decision_id = $1
            """, decision_id)

            if row:
                decision = dict(row)
                decision['affected_components'] = list(decision['affected_components'])
                decision['referenced_reqs'] = list(decision['referenced_reqs']) if decision['referenced_reqs'] else []
                decision['before_after'] = decision['before_after'] or {}
                return decision

            return None

    # Gap Detection (Database-backed)
    async def get_gaps(self, user_id: str = "alice") -> List[Dict[str, Any]]:
        """
        Get role-specific gaps using database
        Replaces simple_server.py in-memory gap detection
        """
        user = await self.get_user(user_id)
        if not user:
            return []

        async with self.get_connection() as conn:
            # Get decisions affecting user's components
            user_decisions = await conn.fetch("""
                SELECT decision_id, author_user_id, author_name, author_role,
                       decision_text, affected_components, referenced_reqs,
                       timestamp, before_after
                FROM decisions
                WHERE affected_components && $1
                ORDER BY timestamp DESC
            """, user['owned_components'])

            # Get current priorities from decision_details
            priorities = await conn.fetch("""
                SELECT decision_id, detail_value->>'priority' as priority
                FROM decision_details
                WHERE detail_name = 'user_priority'
            """)

            priority_map = {row['decision_id']: int(row['priority']) for row in priorities if row['priority']}

            # Generate gaps
            user_specific_gaps = []
            for decision in user_decisions:
                decision_dict = dict(decision)
                affected_user_components = [
                    c for c in decision_dict['affected_components']
                    if c in user['owned_components']
                ]

                # Calculate dynamic priority
                component_overlap = len(affected_user_components)
                is_author = decision_dict['author_user_id'] == user_id
                priority = priority_map.get(decision_dict['decision_id'])

                if priority is None:
                    if is_author:
                        priority = 3 + component_overlap
                    else:
                        priority = 1 if component_overlap >= 2 else 2 if component_overlap == 1 else 5

                # Create gap for missing stakeholder
                if decision_dict['author_user_id'] != user_id:
                    gap = {
                        "type": "missing_stakeholder",
                        "severity": "critical" if priority <= 2 else "warning",
                        "description": f"Decision REQ-{decision_dict['decision_id']:03d} affects your {', '.join(affected_user_components)} but you weren't included",
                        "decision_id": decision_dict['decision_id'],
                        "recommendation": f"Contact meeting host {decision_dict['author_name']} ({decision_dict['author_role']}) to request inclusion in REQ-{decision_dict['decision_id']:03d}",
                        "timestamp": decision_dict['timestamp'].isoformat(),
                        "priority": priority,
                        "entities": {
                            "missing_person": {"id": user_id, "name": user['user_name'], "role": user['role']},
                            "meeting_host": {"name": decision_dict['author_name'], "role": decision_dict['author_role']},
                            "affected_components": affected_user_components
                        }
                    }
                    user_specific_gaps.append(gap)

            return user_specific_gaps

    async def update_gap_priority(self, decision_id: int, priority: int, user_id: str = None) -> bool:
        """Update gap priority in database"""
        async with self.get_connection() as conn:
            try:
                await conn.execute("""
                    INSERT INTO decision_details (decision_id, detail_name, detail_value)
                    VALUES ($1, 'user_priority', $2)
                    ON CONFLICT (decision_id, detail_name)
                    DO UPDATE SET detail_value = $2
                """, decision_id, json.dumps({
                    "priority": priority,
                    "updated_by": user_id or "system",
                    "updated_at": datetime.now().isoformat()
                }))
                return True
            except Exception as e:
                logger.error(f"Failed to update gap priority: {e}")
                return False

    # Chat Integration (OpenAI with Database Context)
    async def get_chat_context(self, user_id: str, message: str = "") -> Dict[str, Any]:
        """
        Get chat context using database + hybrid retrieval
        Enhanced version of simple_server.py chat logic
        """
        user = await self.get_user(user_id)
        if not user:
            return {"error": "User not found"}

        # Get user's relevant decisions using hybrid retrieval
        if message.strip():
            results, stats = await self.retriever.hybrid_search(
                user_id=user_id,
                query_text=message,
                limit=10
            )
            user_decisions = [
                {
                    'decision_id': r.decision_id,
                    'decision_text': r.decision_text,
                    'author_name': r.author_name,
                    'affected_components': r.affected_components,
                    'timestamp': r.timestamp.isoformat(),
                    'similarity_score': r.similarity_score
                }
                for r in results
            ]
        else:
            # Component-based filtering for general context
            user_decisions = await self.get_decisions(user_id, limit=10)

        # Get priority gaps
        priority_gaps = await self.get_gaps(user_id)

        # Sort by priority (lowest number = highest priority)
        priority_gaps = sorted(priority_gaps, key=lambda x: x.get('priority', 999))

        context = {
            "user": user,
            "recent_decisions": user_decisions,
            "priority_gaps": priority_gaps,
            "retrieval_stats": getattr(stats, '__dict__', {}) if message.strip() else None
        }

        return context

    # System Status
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        async with self.get_connection() as conn:
            # Basic counts
            stats = await conn.fetchrow("""
                SELECT
                    (SELECT COUNT(*) FROM user_profiles) as users,
                    (SELECT COUNT(*) FROM decisions) as decisions,
                    (SELECT COUNT(*) FROM slack_messages) as messages,
                    (SELECT COUNT(*) FROM decision_relationships) as relationships
            """)

            # Embedding status
            embedding_stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) FILTER (WHERE embedding_status = 'embedded') as embedded,
                    COUNT(*) FILTER (WHERE embedding_status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE embedding_status = 'failed') as failed
                FROM decisions
            """)

            return {
                "users": stats['users'],
                "decisions": stats['decisions'],
                "messages": stats['messages'],
                "relationships": stats['relationships'],
                "embeddings": dict(embedding_stats),
                "database_url": self.database_url.split('@')[-1] if '@' in self.database_url else "localhost",
                "ai_enabled": bool(os.getenv('ANTHROPIC_API_KEY')) and bool(os.getenv('OPENAI_API_KEY'))
            }

    # Batch Processing Integration
    async def process_pending_embeddings(self, batch_size: int = 100) -> int:
        """Process pending embeddings using embedding pipeline"""
        try:
            from .embedding_pipeline import EmbeddingPipeline
        except ImportError:
            from embedding_pipeline import EmbeddingPipeline

        pipeline = EmbeddingPipeline()
        await pipeline.init_db_pool()

        try:
            return await pipeline.batch_process(batch_size=batch_size, max_batches=1)
        finally:
            await pipeline.close()

    async def process_slack_messages(self, limit: int = 100) -> int:
        """Process Slack messages using entity extraction"""
        return await self.extractor.batch_process_messages(limit)

    async def close(self):
        """Clean up resources"""
        if self.retriever:
            await self.retriever.close()
        if self.extractor:
            await self.extractor.close()
        if self.db_pool:
            await self.db_pool.close()

# Global instance for FastAPI integration
db_manager = DatabaseManager()