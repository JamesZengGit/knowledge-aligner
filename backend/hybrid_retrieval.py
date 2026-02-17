"""
Hybrid Retrieval System for Knowledge Aligner
Combines SQL filtering with semantic vector search for <40ms performance
Two-stage approach: SQL filter → semantic search on candidates
"""

import asyncio
import asyncpg
import numpy as np
import time
import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

@dataclass
class RetrievalResult:
    """Single decision result with similarity score"""
    decision_id: int
    decision_text: str
    author_name: str
    author_role: str
    affected_components: List[str]
    referenced_reqs: List[str]
    timestamp: datetime
    before_after: dict
    similarity_score: float
    embedding: Optional[List[float]] = None

@dataclass
class RetrievalStats:
    """Performance statistics for retrieval"""
    total_time_ms: float
    sql_filter_time_ms: float
    semantic_search_time_ms: float
    candidates_found: int
    final_results: int
    query_type: str  # 'sql_only', 'semantic_only', 'hybrid'

class HybridRetrieval:
    """
    High-performance hybrid retrieval system
    Stage 1: SQL filtering (components, time, author) - ~10ms
    Stage 2: Semantic similarity on candidates - ~30ms
    Total target: <40ms for 10K decisions
    """

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.model = None
        self.db_pool = None

    async def init_model(self):
        """Load sentence-transformers model for query encoding"""
        if not self.model:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)

    async def init_db_pool(self, database_url: str):
        """Initialize PostgreSQL connection pool"""
        if not self.db_pool:
            self.db_pool = await asyncpg.create_pool(
                database_url,
                min_size=5,
                max_size=20,
                command_timeout=10  # Fast timeout for performance
            )

    async def sql_filter(self,
                        user_components: List[str],
                        time_filter_days: int = 30,
                        author_filter: Optional[str] = None,
                        decision_type: Optional[str] = None,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """
        Stage 1: Fast SQL filtering based on structured criteria
        Target: <10ms for 10K decisions
        """
        start_time = time.perf_counter()

        async with self.db_pool.acquire() as conn:
            # Build dynamic query based on filters
            conditions = ["embedding_status = 'embedded'"]
            params = []
            param_count = 0

            # Component overlap filter (most important)
            if user_components:
                param_count += 1
                conditions.append(f"affected_components && ${param_count}")
                params.append(user_components)

            # Time filter
            param_count += 1
            conditions.append(f"timestamp >= ${param_count}")
            params.append(datetime.now() - timedelta(days=time_filter_days))

            # Author filter
            if author_filter:
                param_count += 1
                conditions.append(f"author_user_id = ${param_count}")
                params.append(author_filter)

            # Decision type filter
            if decision_type:
                param_count += 1
                conditions.append(f"decision_type = ${param_count}")
                params.append(decision_type)

            # Limit parameter
            param_count += 1
            params.append(limit)

            query = f"""
                SELECT decision_id, decision_text, author_name, author_role,
                       affected_components, referenced_reqs, timestamp,
                       before_after, embedding, similarity_score
                FROM decisions
                WHERE {' AND '.join(conditions)}
                ORDER BY timestamp DESC
                LIMIT ${param_count}
            """

            rows = await conn.fetch(query, *params)

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(f"SQL filter: {len(rows)} candidates in {duration_ms:.2f}ms")

        return [dict(row) for row in rows]

    async def semantic_search(self,
                             query_text: str,
                             candidates: List[Dict[str, Any]],
                             limit: int = 20) -> List[RetrievalResult]:
        """
        Stage 2: Semantic similarity search on SQL-filtered candidates
        Target: <30ms for 100 candidates
        """
        if not candidates:
            return []

        start_time = time.perf_counter()

        # Initialize model if needed
        if not self.model:
            await self.init_model()

        # Encode query text
        query_embedding = self.model.encode([query_text], normalize_embeddings=True)[0]

        # Calculate similarities
        results = []
        for candidate in candidates:
            # Extract embedding from database
            if candidate['embedding']:
                decision_embedding = np.array(candidate['embedding'])

                # Calculate cosine similarity
                similarity = np.dot(query_embedding, decision_embedding)
            else:
                # Fallback for missing embeddings
                similarity = 0.0

            result = RetrievalResult(
                decision_id=candidate['decision_id'],
                decision_text=candidate['decision_text'],
                author_name=candidate['author_name'],
                author_role=candidate['author_role'],
                affected_components=candidate['affected_components'],
                referenced_reqs=candidate['referenced_reqs'],
                timestamp=candidate['timestamp'],
                before_after=candidate['before_after'] or {},
                similarity_score=similarity,
                embedding=candidate['embedding']
            )
            results.append(result)

        # Sort by similarity and limit results
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        final_results = results[:limit]

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(f"Semantic search: {len(final_results)} results in {duration_ms:.2f}ms")

        return final_results

    async def hybrid_search(self,
                           user_id: str,
                           query_text: str = "",
                           user_components: List[str] = None,
                           time_filter_days: int = 30,
                           limit: int = 20) -> Tuple[List[RetrievalResult], RetrievalStats]:
        """
        Main hybrid search function
        Combines SQL filtering with semantic search for optimal performance
        """
        total_start = time.perf_counter()

        # Get user components if not provided
        if user_components is None:
            user_components = await self.get_user_components(user_id)

        # Stage 1: SQL filtering
        sql_start = time.perf_counter()
        candidates = await self.sql_filter(
            user_components=user_components,
            time_filter_days=time_filter_days,
            limit=min(100, limit * 5)  # Get more candidates than needed
        )
        sql_time_ms = (time.perf_counter() - sql_start) * 1000

        # Determine search strategy
        if not query_text.strip():
            # Pure SQL filtering (component-based)
            results = []
            for candidate in candidates[:limit]:
                result = RetrievalResult(
                    decision_id=candidate['decision_id'],
                    decision_text=candidate['decision_text'],
                    author_name=candidate['author_name'],
                    author_role=candidate['author_role'],
                    affected_components=candidate['affected_components'],
                    referenced_reqs=candidate['referenced_reqs'],
                    timestamp=candidate['timestamp'],
                    before_after=candidate['before_after'] or {},
                    similarity_score=candidate['similarity_score'] or 0.0
                )
                results.append(result)

            semantic_time_ms = 0
            query_type = 'sql_only'

        else:
            # Stage 2: Semantic search on candidates
            semantic_start = time.perf_counter()
            results = await self.semantic_search(query_text, candidates, limit)
            semantic_time_ms = (time.perf_counter() - semantic_start) * 1000
            query_type = 'hybrid'

        total_time_ms = (time.perf_counter() - total_start) * 1000

        # Create performance stats
        stats = RetrievalStats(
            total_time_ms=total_time_ms,
            sql_filter_time_ms=sql_time_ms,
            semantic_search_time_ms=semantic_time_ms,
            candidates_found=len(candidates),
            final_results=len(results),
            query_type=query_type
        )

        logger.info(f"Hybrid search: {len(results)} results in {total_time_ms:.1f}ms ({query_type})")

        return results, stats

    async def pure_semantic_search(self,
                                  query_text: str,
                                  limit: int = 20,
                                  similarity_threshold: float = 0.5) -> List[RetrievalResult]:
        """
        Pure semantic search using pgvector similarity
        For comparison with hybrid approach
        """
        if not self.model:
            await self.init_model()

        start_time = time.perf_counter()

        # Encode query
        query_embedding = self.model.encode([query_text], normalize_embeddings=True)[0]
        embedding_list = query_embedding.tolist()

        async with self.db_pool.acquire() as conn:
            # Use pgvector similarity operator
            query = """
                SELECT decision_id, decision_text, author_name, author_role,
                       affected_components, referenced_reqs, timestamp,
                       before_after, embedding <=> $1 as similarity
                FROM decisions
                WHERE embedding_status = 'embedded'
                  AND embedding <=> $1 < $2
                ORDER BY embedding <=> $1
                LIMIT $3
            """

            rows = await conn.fetch(query, embedding_list, 1.0 - similarity_threshold, limit)

        # Convert to results
        results = []
        for row in rows:
            result = RetrievalResult(
                decision_id=row['decision_id'],
                decision_text=row['decision_text'],
                author_name=row['author_name'],
                author_role=row['author_role'],
                affected_components=row['affected_components'],
                referenced_reqs=row['referenced_reqs'],
                timestamp=row['timestamp'],
                before_after=row['before_after'] or {},
                similarity_score=1.0 - row['similarity']  # Convert distance to similarity
            )
            results.append(result)

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(f"Pure semantic search: {len(results)} results in {duration_ms:.1f}ms")

        return results

    async def get_user_components(self, user_id: str) -> List[str]:
        """Get user's owned components from database"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT owned_components
                FROM user_profiles
                WHERE user_id = $1
            """, user_id)

            return row['owned_components'] if row else []

    async def benchmark_performance(self,
                                   test_queries: List[str],
                                   user_id: str = 'alice') -> Dict[str, Any]:
        """
        Benchmark different retrieval strategies
        Compare SQL-only, hybrid, and pure semantic performance
        """
        logger.info(f"Benchmarking with {len(test_queries)} queries")

        user_components = await self.get_user_components(user_id)
        results = {
            'sql_only': [],
            'hybrid': [],
            'pure_semantic': []
        }

        for query in test_queries:
            # SQL-only (component filtering)
            start = time.perf_counter()
            sql_candidates = await self.sql_filter(user_components, limit=20)
            sql_time = (time.perf_counter() - start) * 1000
            results['sql_only'].append(sql_time)

            # Hybrid search
            _, hybrid_stats = await self.hybrid_search(user_id, query)
            results['hybrid'].append(hybrid_stats.total_time_ms)

            # Pure semantic search
            start = time.perf_counter()
            await self.pure_semantic_search(query)
            semantic_time = (time.perf_counter() - start) * 1000
            results['pure_semantic'].append(semantic_time)

        # Calculate statistics
        benchmark_results = {}
        for method, times in results.items():
            benchmark_results[method] = {
                'avg_time_ms': np.mean(times),
                'p50_time_ms': np.percentile(times, 50),
                'p95_time_ms': np.percentile(times, 95),
                'p99_time_ms': np.percentile(times, 99),
                'min_time_ms': np.min(times),
                'max_time_ms': np.max(times)
            }

        return benchmark_results

    async def close(self):
        """Clean up resources"""
        if self.db_pool:
            await self.db_pool.close()

# CLI for testing and benchmarking
async def main():
    import argparse
    import os

    parser = argparse.ArgumentParser(description='Hybrid Retrieval System')
    parser.add_argument('--query', type=str, help='Test query')
    parser.add_argument('--user-id', type=str, default='alice', help='User ID for filtering')
    parser.add_argument('--benchmark', action='store_true', help='Run performance benchmark')
    parser.add_argument('--limit', type=int, default=20, help='Number of results')

    args = parser.parse_args()

    # Initialize retrieval system
    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/knowledge_aligner')
    retriever = HybridRetrieval()

    try:
        await retriever.init_db_pool(database_url)

        if args.benchmark:
            # Run benchmark with test queries
            test_queries = [
                "motor torque requirements",
                "power supply capacity",
                "firmware update security",
                "PCB design changes",
                "component selection"
            ]

            results = await retriever.benchmark_performance(test_queries, args.user_id)

            print("Performance Benchmark Results:")
            for method, stats in results.items():
                print(f"\n{method.upper()}:")
                print(f"  Average: {stats['avg_time_ms']:.1f}ms")
                print(f"  P95: {stats['p95_time_ms']:.1f}ms")
                print(f"  P99: {stats['p99_time_ms']:.1f}ms")

        elif args.query:
            # Single query test
            results, stats = await retriever.hybrid_search(
                user_id=args.user_id,
                query_text=args.query,
                limit=args.limit
            )

            print(f"Query: '{args.query}'")
            print(f"Performance: {stats.total_time_ms:.1f}ms total ({stats.query_type})")
            print(f"  SQL Filter: {stats.sql_filter_time_ms:.1f}ms")
            print(f"  Semantic: {stats.semantic_search_time_ms:.1f}ms")
            print(f"Results: {len(results)}")

            for i, result in enumerate(results[:5]):
                print(f"\n{i+1}. [{result.decision_id}] {result.author_name}")
                print(f"   Similarity: {result.similarity_score:.3f}")
                print(f"   Components: {result.affected_components}")
                print(f"   Text: {result.decision_text[:100]}...")

        else:
            print("Use --query 'text' for search or --benchmark for performance testing")

    finally:
        await retriever.close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())