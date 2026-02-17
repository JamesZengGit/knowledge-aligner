"""
Two-Tier Context Orchestrator
Bridges Redis live buffer + SQL persistent storage with atomic decision creation
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import asdict

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    logging.warning("asyncpg not available, SQL operations will fail")

from redis_context_buffer import RedisContextBuffer, LiveContextMessage
from realtime_entity_extraction import RealtimeEntityExtractor, ExtractedEntities, ContextMatcher
from context_aware_responder import CachedContextResponder

logger = logging.getLogger(__name__)

class TwoTierOrchestrator:
    """
    Orchestrates real-time context flow between Redis + SQL

    Core workflow:
    1. Message arrives → Entity extraction (~200ms)
    2. Atomic write: Redis buffer + SQL decision
    3. Context injection on subsequent messages
    4. Gap detection when context overlap found
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        postgres_url: str = "postgresql://postgres:postgres@localhost:5432/knowledge_aligner",
        anthropic_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        # Components
        self.redis_buffer = RedisContextBuffer(redis_url)
        self.entity_extractor = RealtimeEntityExtractor(anthropic_api_key, openai_api_key)
        self.context_matcher = ContextMatcher()
        self.context_responder = CachedContextResponder(anthropic_api_key, openai_api_key)

        # Database
        self.postgres_url = postgres_url
        self.db_pool: Optional[asyncpg.Pool] = None

        # Performance tracking
        self.stats = {
            "messages_processed": 0,
            "context_injections": 0,
            "gaps_created": 0,
            "avg_processing_time_ms": 0.0,
            "redis_failures": 0,
            "sql_failures": 0
        }

    async def initialize(self):
        """Initialize Redis and PostgreSQL connections"""
        try:
            # Initialize Redis
            await self.redis_buffer.connect()

            # Initialize PostgreSQL pool
            if ASYNCPG_AVAILABLE:
                self.db_pool = await asyncpg.create_pool(
                    self.postgres_url,
                    min_size=2,
                    max_size=10,
                    command_timeout=30
                )
                logger.info("✅ Connected to PostgreSQL")
            else:
                logger.warning("⚠️  PostgreSQL unavailable - SQL operations disabled")

            logger.info("🚀 Two-tier orchestrator initialized")

        except Exception as e:
            logger.error(f"❌ Failed to initialize orchestrator: {e}")
            raise

    async def shutdown(self):
        """Cleanup connections"""
        await self.redis_buffer.disconnect()
        if self.db_pool:
            await self.db_pool.close()
        logger.info("🔌 Two-tier orchestrator shutdown complete")

    async def process_incoming_message(
        self,
        message_id: str,
        channel_id: str,
        user_id: str,
        message_text: str,
        timestamp: Optional[datetime] = None
    ) -> Dict:
        """
        Process incoming Slack message through two-tier pipeline

        Returns: {
            "decision_created": bool,
            "context_injected": bool,
            "gap_created": bool,
            "processing_time_ms": float,
            "response": Optional[str]
        }
        """
        start_time = time.time()
        timestamp = timestamp or datetime.now()

        try:
            # Step 1: Extract entities from message (~200ms)
            logger.debug(f"🔍 Extracting entities from message {message_id}")
            entities = await self.entity_extractor.extract_entities_fast(
                message_text, user_id, channel_id
            )

            # Step 2: Check if this creates a decision
            decision_id = None
            if self._is_decision_worthy(entities, message_text):
                decision_id = await self._create_decision_record(
                    message_id, channel_id, user_id, message_text,
                    entities, timestamp
                )

            # Step 3: Add to Redis buffer (with decision_id if created)
            context_message = LiveContextMessage(
                message_id=message_id,
                user_id=user_id,
                text=message_text,
                entities={
                    'reqs': entities.reqs,
                    'components': entities.components,
                    'users_mentioned': entities.users_mentioned,
                    'topics': entities.topics,
                    'confidence': entities.confidence,
                },
                decision_id=decision_id,
                timestamp=timestamp.isoformat(),
                channel_id=channel_id
            )

            redis_success = await self.redis_buffer.add_message(channel_id, context_message)
            if not redis_success:
                self.stats["redis_failures"] += 1

            # Step 4: Check for context injection opportunity
            context_result = await self._check_context_injection(
                channel_id, entities, user_id, message_id, message_text
            )

            # Update stats
            processing_time = (time.time() - start_time) * 1000
            self.stats["messages_processed"] += 1
            self.stats["avg_processing_time_ms"] = (
                (self.stats["avg_processing_time_ms"] * (self.stats["messages_processed"] - 1) +
                 processing_time) / self.stats["messages_processed"]
            )

            if context_result.get("context_injected"):
                self.stats["context_injections"] += 1

            if context_result.get("gap_created"):
                self.stats["gaps_created"] += 1

            return {
                "decision_created": bool(decision_id),
                "decision_id": decision_id,
                "entities_extracted": len(entities.reqs + entities.components),
                "extraction_time_ms": entities.extraction_time_ms,
                "processing_time_ms": processing_time,
                **context_result
            }

        except Exception as e:
            logger.error(f"Failed to process message {message_id}: {e}")
            return {
                "decision_created": False,
                "context_injected": False,
                "gap_created": False,
                "processing_time_ms": (time.time() - start_time) * 1000,
                "error": str(e)
            }

    def _is_decision_worthy(self, entities: ExtractedEntities, message_text: str) -> bool:
        """
        Determine if message represents an engineering decision

        Criteria:
        - Contains REQ-XXX references
        - Has 2+ components mentioned
        - Contains decision keywords
        - High entity extraction confidence
        """
        # REQ mentions are strong decision indicators
        if entities.reqs:
            return True

        # Multiple components + decision keywords
        decision_keywords = [
            'decision', 'decided', 'approved', 'selected', 'chose',
            'updated', 'changed', 'requirement', 'spec', 'requirement'
        ]

        has_decision_keyword = any(
            keyword in message_text.lower() for keyword in decision_keywords
        )

        if len(entities.components) >= 2 and has_decision_keyword:
            return True

        # High confidence extraction with engineering topics
        if entities.confidence > 0.8 and len(entities.topics) >= 2:
            return True

        return False

    async def _create_decision_record(
        self,
        message_id: str,
        channel_id: str,
        user_id: str,
        message_text: str,
        entities: ExtractedEntities,
        timestamp: datetime
    ) -> Optional[str]:
        """
        Create decision record in PostgreSQL
        Returns decision_id for Redis linking
        """
        if not self.db_pool:
            logger.warning("No database pool - skipping decision creation")
            return None

        try:
            # Generate decision ID with timestamp
            decision_id = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{message_id[:8]}"

            async with self.db_pool.acquire() as conn:
                # Create decision record
                await conn.execute("""
                    INSERT INTO decisions (
                        decision_id, thread_id, timestamp, author_user_id,
                        decision_text, affected_components, referenced_reqs,
                        embedding_status
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending')
                """,
                    decision_id,
                    f"{channel_id}_{message_id}",  # thread_id
                    timestamp,
                    user_id,
                    message_text,
                    json.dumps(entities.components),
                    json.dumps(entities.reqs)
                )

                logger.info(f"📝 Created decision record {decision_id}")
                return decision_id

        except Exception as e:
            logger.error(f"Failed to create decision record: {e}")
            self.stats["sql_failures"] += 1
            return None

    async def _check_context_injection(
        self,
        channel_id: str,
        b_entities: ExtractedEntities,
        user_id: str,
        message_id: str,
        message_text: str = ""
    ) -> Dict:
        """
        Check if context should be injected based on entity overlap
        Create gaps and generate responses when overlap detected
        """
        try:
            # Get recent context from Redis buffer
            context_messages = await self.redis_buffer.get_recent_context(
                channel_id, max_messages=30, max_age_minutes=120
            )

            if not context_messages:
                return {"context_injected": False, "gap_created": False}

            # Extract entities from context messages
            buffer_entities = []
            for msg in context_messages:
                # Convert dict back to ExtractedEntities
                entities_dict = msg.entities
                entities_obj = ExtractedEntities(
                    reqs=entities_dict.get('reqs', []),
                    components=entities_dict.get('components', []),
                    users_mentioned=entities_dict.get('users_mentioned', []),
                    topics=entities_dict.get('topics', []),
                    confidence=entities_dict.get('confidence', 0.6),
                    extraction_time_ms=0
                )
                buffer_entities.append(entities_obj)

            # Check for context injection
            should_inject, confidence, score = self.context_matcher.should_inject_context(
                b_entities, buffer_entities, confidence_threshold='medium'
            )

            if not should_inject:
                return {"context_injected": False, "gap_created": False}

            # Find matching context messages
            matching_contexts = []
            for msg in context_messages:
                msg_entities_dict = msg.entities
                msg_entities = ExtractedEntities(
                    reqs=msg_entities_dict.get('reqs', []),
                    components=msg_entities_dict.get('components', []),
                    users_mentioned=msg_entities_dict.get('users_mentioned', []),
                    topics=msg_entities_dict.get('topics', []),
                    confidence=msg_entities_dict.get('confidence', 0.6),
                    extraction_time_ms=0
                )

                msg_confidence, msg_score = self.context_matcher.calculate_overlap_score(
                    b_entities, [msg_entities]
                )

                if msg_confidence in ['high', 'medium']:
                    matching_contexts.append({
                        'message': msg,
                        'confidence': msg_confidence,
                        'score': msg_score
                    })

            # Create gap if missing stakeholder detected
            gap_created = False
            if matching_contexts:
                gap_id = await self._create_gap_if_needed(
                    b_entities, matching_contexts, user_id
                )
                gap_created = bool(gap_id)

            # Generate context-aware response using LLM
            response_obj = await self.context_responder.generate_response(
                message_text,  # user_message
                b_entities,    # user_entities
                matching_contexts,
                user_id,
                gap_created,
                gap_id if gap_created else None
            )
            response = response_obj.response_text

            return {
                "context_injected": True,
                "gap_created": gap_created,
                "confidence": confidence,
                "score": score,
                "matching_contexts_count": len(matching_contexts),
                "response": response
            }

        except Exception as e:
            logger.error(f"Context injection check failed: {e}")
            return {"context_injected": False, "gap_created": False, "error": str(e)}

    async def _create_gap_if_needed(
        self,
        b_entities: ExtractedEntities,
        matching_contexts: List[Dict],
        user_id: str
    ) -> Optional[str]:
        """
        Create gap record if missing stakeholder detected
        Gap: B should have been included in original decision discussion
        """
        if not self.db_pool:
            return None

        try:
            # Check if user was mentioned in any matching context
            user_was_mentioned = any(
                f"@{user_id}" in ctx['message'].entities.get('users_mentioned', [])
                for ctx in matching_contexts
            )

            if user_was_mentioned:
                return None  # User was already included

            # Generate gap description with context
            gap_id = await self._generate_gap_id()
            description = self._generate_gap_description(
                b_entities, matching_contexts, user_id
            )

            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO gaps (
                        gap_id, type, severity, description,
                        assignee_id, recommendation
                    ) VALUES ($1, 'missing_stakeholder', 'warning', $2, $3, $4)
                """,
                    gap_id,
                    description,
                    user_id,
                    f"Include {user_id} in future discussions about overlapping components"
                )

                logger.info(f"⚠️  Created gap {gap_id} for missing stakeholder {user_id}")
                return gap_id

        except Exception as e:
            logger.error(f"Failed to create gap: {e}")
            return None

    def _generate_gap_description(
        self,
        b_entities: ExtractedEntities,
        matching_contexts: List[Dict],
        user_id: str
    ) -> str:
        """Generate descriptive gap text with context"""
        overlapping_components = set()
        overlapping_reqs = set()

        for ctx in matching_contexts:
            msg_entities = ctx['message'].entities
            overlapping_components.update(
                set(b_entities.components) & set(msg_entities.get('components', []))
            )
            overlapping_reqs.update(
                set(b_entities.reqs) & set(msg_entities.get('reqs', []))
            )

        components_str = ', '.join(overlapping_components)
        reqs_str = ', '.join(overlapping_reqs)

        description_parts = []
        if overlapping_reqs:
            description_parts.append(f"Requirements {reqs_str} mentioned")
        if overlapping_components:
            description_parts.append(f"Components {components_str} discussed")

        context_info = ' and '.join(description_parts)

        return (f"User {user_id} mentioned {context_info} that were previously "
                f"discussed without their involvement. Consider including them "
                f"in future related decisions.")

    async def _generate_gap_id(self) -> str:
        """Generate unique gap ID"""
        if not self.db_pool:
            return f"gap_{int(time.time())}"

        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchval(
                    "SELECT COALESCE(MAX(CAST(gap_id AS INTEGER)), 0) + 1 FROM gaps"
                )
                return str(result)
        except Exception:
            return f"gap_{int(time.time())}"

    async def _generate_context_response(
        self,
        b_entities: ExtractedEntities,
        matching_contexts: List[Dict],
        user_id: str
    ) -> str:
        """
        Generate context-aware response for user
        This would integrate with LLM for full responses
        """
        if not matching_contexts:
            return "No relevant context found."

        # For now, return structured context summary
        # In production, this would feed into Sonnet for natural language response
        context_summary = []

        for ctx in matching_contexts:
            msg = ctx['message']
            context_summary.append(
                f"Related discussion by {msg.user_id}: {msg.text[:100]}..."
            )

        overlapping_components = set()
        for ctx in matching_contexts:
            msg_entities = ctx['message'].entities
            overlapping_components.update(
                set(b_entities.components) & set(msg_entities.get('components', []))
            )

        response = (
            f"Found {len(matching_contexts)} related discussions about "
            f"{', '.join(overlapping_components)}. "
            f"Context: {' | '.join(context_summary[:2])}"
        )

        return response

    async def get_stats(self) -> Dict:
        """Get orchestrator performance statistics"""
        redis_stats = await self.redis_buffer.get_channel_stats("hardware-team")  # Example

        return {
            **self.stats,
            "redis_connected": bool(self.redis_buffer.redis_client),
            "postgres_connected": bool(self.db_pool),
            "sample_redis_stats": redis_stats
        }

# Context manager for easy usage
class TwoTierManager:
    """Context manager for two-tier orchestrator"""

    def __init__(self, **kwargs):
        self.orchestrator = TwoTierOrchestrator(**kwargs)

    async def __aenter__(self):
        await self.orchestrator.initialize()
        return self.orchestrator

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.orchestrator.shutdown()

# Testing and example usage
if __name__ == "__main__":
    import asyncio

    async def test_two_tier_flow():
        """Test complete two-tier workflow"""
        async with TwoTierManager() as orchestrator:
            # Simulate Engineer A posts about motor
            result_a = await orchestrator.process_incoming_message(
                message_id="msg_001",
                channel_id="hardware-team",
                user_id="alice",
                message_text="Updated REQ-245 motor torque from 2.0Nm to 2.5Nm based on customer feedback"
            )

            print("Engineer A message result:")
            print(json.dumps(result_a, indent=2))

            # Wait a bit (simulate time passing)
            await asyncio.sleep(1)

            # Simulate Engineer B asks about motor 5 minutes later
            result_b = await orchestrator.process_incoming_message(
                message_id="msg_002",
                channel_id="hardware-team",
                user_id="bob",
                message_text="What's the current motor power requirements for the new specs?"
            )

            print("\nEngineer B message result:")
            print(json.dumps(result_b, indent=2))

            # Get orchestrator stats
            stats = await orchestrator.get_stats()
            print(f"\nOrchestrator stats:")
            print(json.dumps(stats, indent=2))

    # Run test
    asyncio.run(test_two_tier_flow())