"""Hybrid retrieval system combining SQL filtering and semantic search."""

import os
import psycopg2
import psycopg2.extras
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from src.embedding_pipeline import EmbeddingPipeline
from src.models import DecisionType
from dotenv import load_dotenv
import logging

load_dotenv()

class HybridRetriever:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        self.embedding_pipeline = EmbeddingPipeline()
        self.similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", 0.7))

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def search_decisions(
        self,
        query: str,
        user_id: Optional[str] = None,
        components: Optional[List[str]] = None,
        decision_types: Optional[List[DecisionType]] = None,
        time_range_days: int = 30,
        limit: int = 20
    ) -> List[Dict]:
        """
        Hybrid search combining SQL filtering and semantic similarity.

        Args:
            query: Text query for semantic search
            user_id: Filter by decisions affecting user's components
            components: Filter by specific components
            decision_types: Filter by decision types
            time_range_days: Only include decisions from last N days
            limit: Maximum number of results
        """
        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

                # Stage 1: SQL filtering (fast)
                sql_filtered_ids = self._sql_filter(
                    cursor, user_id, components, decision_types, time_range_days
                )

                if not sql_filtered_ids:
                    self.logger.info("No decisions found matching SQL filters")
                    return []

                # Stage 2: Semantic search on filtered results (slower but targeted)
                if query:
                    query_embedding = self.embedding_pipeline.embed_single_text(query)
                    semantic_results = self._semantic_search(
                        cursor, query_embedding, sql_filtered_ids, limit
                    )
                else:
                    # If no query, return SQL filtered results ordered by recency
                    semantic_results = self._get_recent_decisions(
                        cursor, sql_filtered_ids, limit
                    )

                # Stage 3: Enrich with full context
                enriched_results = self._enrich_results(cursor, semantic_results)

                return enriched_results

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            raise

    def _sql_filter(
        self,
        cursor,
        user_id: Optional[str],
        components: Optional[List[str]],
        decision_types: Optional[List[DecisionType]],
        time_range_days: int
    ) -> List[int]:
        """Fast SQL filtering to reduce search space."""

        # Base query with time filtering
        base_conditions = ["timestamp >= %s"]
        params = [datetime.now() - timedelta(days=time_range_days)]

        # User's component filter
        if user_id:
            user_components = self._get_user_components(cursor, user_id)
            if user_components:
                base_conditions.append("affected_components && %s")
                params.append(user_components)

        # Specific components filter
        if components:
            base_conditions.append("affected_components && %s")
            params.append(components)

        # Decision type filter
        if decision_types:
            type_values = [dt.value for dt in decision_types]
            base_conditions.append("decision_type = ANY(%s)")
            params.append(type_values)

        # Only include decisions with embeddings
        base_conditions.append("embedding_status = 'embedded'")

        where_clause = " AND ".join(base_conditions)

        query = f"""
        SELECT decision_id
        FROM decisions
        WHERE {where_clause}
        ORDER BY timestamp DESC
        """

        cursor.execute(query, params)
        results = cursor.fetchall()

        decision_ids = [row['decision_id'] for row in results]
        self.logger.info(f"SQL filtering found {len(decision_ids)} decisions")

        return decision_ids

    def _semantic_search(
        self,
        cursor,
        query_embedding: np.ndarray,
        candidate_ids: List[int],
        limit: int
    ) -> List[Tuple[int, float]]:
        """Perform semantic search on pre-filtered candidates."""

        if not candidate_ids:
            return []

        # Convert numpy array to list for PostgreSQL
        query_embedding_list = query_embedding.tolist()

        # Use pgvector's cosine similarity
        query = """
        SELECT
            decision_id,
            1 - (embedding <=> %s) as similarity
        FROM decisions
        WHERE decision_id = ANY(%s)
            AND embedding IS NOT NULL
        ORDER BY similarity DESC
        LIMIT %s
        """

        cursor.execute(query, (query_embedding_list, candidate_ids, limit))
        results = cursor.fetchall()

        # Filter by similarity threshold
        filtered_results = [
            (row['decision_id'], row['similarity'])
            for row in results
            if row['similarity'] >= self.similarity_threshold
        ]

        self.logger.info(f"Semantic search returned {len(filtered_results)} results above threshold")

        return filtered_results

    def _get_recent_decisions(
        self,
        cursor,
        candidate_ids: List[int],
        limit: int
    ) -> List[Tuple[int, float]]:
        """Get recent decisions when no query is provided."""

        if not candidate_ids:
            return []

        query = """
        SELECT decision_id
        FROM decisions
        WHERE decision_id = ANY(%s)
        ORDER BY timestamp DESC
        LIMIT %s
        """

        cursor.execute(query, (candidate_ids, limit))
        results = cursor.fetchall()

        # Return with dummy similarity score
        return [(row['decision_id'], 1.0) for row in results]

    def _enrich_results(
        self,
        cursor,
        decision_results: List[Tuple[int, float]]
    ) -> List[Dict]:
        """Enrich search results with full decision context."""

        if not decision_results:
            return []

        decision_ids = [result[0] for result in decision_results]
        similarity_scores = {result[0]: result[1] for result in decision_results}

        # Fetch full decision data
        query = """
        SELECT
            d.decision_id,
            d.thread_id,
            d.timestamp,
            d.author_user_id,
            d.decision_type,
            d.decision_text,
            d.affected_components,
            d.referenced_reqs,
            u.user_name,
            u.role
        FROM decisions d
        JOIN user_profiles u ON d.author_user_id = u.user_id
        WHERE d.decision_id = ANY(%s)
        """

        cursor.execute(query, (decision_ids,))
        decisions = cursor.fetchall()

        # Fetch decision details
        details_query = """
        SELECT decision_id, detail_name, detail_value
        FROM decision_details
        WHERE decision_id = ANY(%s)
        """

        cursor.execute(details_query, (decision_ids,))
        details_rows = cursor.fetchall()

        # Group details by decision_id
        details_by_decision = {}
        for detail in details_rows:
            decision_id = detail['decision_id']
            if decision_id not in details_by_decision:
                details_by_decision[decision_id] = {}
            details_by_decision[decision_id][detail['detail_name']] = detail['detail_value']

        # Fetch relationships
        relationships_query = """
        SELECT
            source_decision_id,
            target_decision_id,
            relationship_type,
            confidence
        FROM decision_relationships
        WHERE source_decision_id = ANY(%s) OR target_decision_id = ANY(%s)
        """

        cursor.execute(relationships_query, (decision_ids, decision_ids))
        relationships = cursor.fetchall()

        # Group relationships by decision
        relationships_by_decision = {}
        for rel in relationships:
            for decision_id in [rel['source_decision_id'], rel['target_decision_id']]:
                if decision_id in decision_ids:
                    if decision_id not in relationships_by_decision:
                        relationships_by_decision[decision_id] = []
                    relationships_by_decision[decision_id].append(dict(rel))

        # Build enriched results
        enriched = []
        for decision in decisions:
            decision_id = decision['decision_id']

            result = {
                'decision_id': decision_id,
                'thread_id': decision['thread_id'],
                'timestamp': decision['timestamp'],
                'author_user_id': decision['author_user_id'],
                'author_name': decision['user_name'],
                'author_role': decision['role'],
                'decision_type': decision['decision_type'],
                'decision_text': decision['decision_text'],
                'affected_components': decision['affected_components'],
                'referenced_reqs': decision['referenced_reqs'],
                'similarity_score': similarity_scores.get(decision_id, 0.0),
                'details': details_by_decision.get(decision_id, {}),
                'relationships': relationships_by_decision.get(decision_id, [])
            }

            enriched.append(result)

        # Sort by similarity score (or timestamp if no scores)
        if any(r['similarity_score'] > 0 for r in enriched):
            enriched.sort(key=lambda x: x['similarity_score'], reverse=True)
        else:
            enriched.sort(key=lambda x: x['timestamp'], reverse=True)

        return enriched

    def _get_user_components(self, cursor, user_id: str) -> List[str]:
        """Get components owned by a specific user."""
        query = "SELECT owned_components FROM user_profiles WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()

        return result['owned_components'] if result else []

    def get_related_decisions(
        self,
        decision_id: int,
        relationship_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get decisions related to a specific decision."""

        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

                # Build relationship filter
                rel_filter = ""
                params = [decision_id, decision_id]

                if relationship_types:
                    rel_filter = "AND relationship_type = ANY(%s)"
                    params.append(relationship_types)

                query = f"""
                SELECT
                    d.decision_id,
                    d.timestamp,
                    d.author_user_id,
                    d.decision_type,
                    d.decision_text,
                    d.affected_components,
                    d.referenced_reqs,
                    u.user_name,
                    r.relationship_type,
                    r.confidence
                FROM decision_relationships r
                JOIN decisions d ON (
                    d.decision_id = CASE
                        WHEN r.source_decision_id = %s THEN r.target_decision_id
                        ELSE r.source_decision_id
                    END
                )
                JOIN user_profiles u ON d.author_user_id = u.user_id
                WHERE (r.source_decision_id = %s OR r.target_decision_id = %s)
                {rel_filter}
                ORDER BY r.confidence DESC, d.timestamp DESC
                LIMIT %s
                """

                params.append(limit)
                cursor.execute(query, params)

                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            self.logger.error(f"Failed to get related decisions: {e}")
            return []