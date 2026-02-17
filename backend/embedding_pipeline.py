#!/usr/bin/env python3
"""
Batch Embedding Pipeline for Knowledge Aligner
Uses sentence-transformers for local embedding generation
Target: Process 100-1000 decisions in batches for <40ms retrieval
"""

import asyncio
import asyncpg
import numpy as np
import os
import sys
import logging
from typing import List, Tuple, Optional
from datetime import datetime
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmbeddingPipeline:
    """
    Batch embedding pipeline using sentence-transformers
    Processes pending decisions and generates 768-dimensional embeddings
    """

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize with sentence-transformers model
        all-MiniLM-L6-v2: 384MB, 768 dimensions, good performance/speed balance
        """
        self.model_name = model_name
        self.model = None
        self.db_pool = None

    async def init_model(self):
        """Load sentence-transformers model"""
        logger.info(f"Loading sentence-transformers model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        logger.info("Model loaded successfully")

    async def init_db_pool(self):
        """Initialize PostgreSQL connection pool"""
        database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/knowledge_aligner')
        logger.info(f"Connecting to database: {database_url}")

        self.db_pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        logger.info("Database connection pool created")

    async def get_pending_decisions(self, batch_size: int = 100) -> List[Tuple[int, str]]:
        """
        Fetch decisions with pending embedding status
        Returns list of (decision_id, decision_text) tuples
        """
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT decision_id, decision_text
                FROM decisions
                WHERE embedding_status = 'pending'
                ORDER BY created_at ASC
                LIMIT $1
            """
            rows = await conn.fetch(query, batch_size)
            return [(row['decision_id'], row['decision_text']) for row in rows]

    async def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for batch of texts
        Returns numpy array of shape (n_texts, 768)
        """
        if not self.model:
            await self.init_model()

        logger.info(f"Generating embeddings for {len(texts)} texts")
        start_time = datetime.now()

        # Generate embeddings
        embeddings = self.model.encode(
            texts,
            batch_size=32,  # Process in mini-batches for memory efficiency
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True  # Normalize for cosine similarity
        )

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Generated {len(embeddings)} embeddings in {duration:.2f}s ({duration/len(texts):.3f}s per text)")

        return embeddings

    async def update_embeddings(self, decision_ids: List[int], embeddings: np.ndarray) -> int:
        """
        Update database with generated embeddings
        Returns number of updated records
        """
        async with self.db_pool.acquire() as conn:
            updated_count = 0

            # Start transaction for batch update
            async with conn.transaction():
                for decision_id, embedding in zip(decision_ids, embeddings):
                    try:
                        # Convert numpy array to list for JSON storage
                        embedding_list = embedding.tolist()

                        await conn.execute("""
                            UPDATE decisions
                            SET embedding = $1::vector,
                                embedding_status = 'embedded',
                                updated_at = NOW()
                            WHERE decision_id = $2
                        """, embedding_list, decision_id)

                        updated_count += 1

                    except Exception as e:
                        logger.error(f"Failed to update decision {decision_id}: {e}")
                        # Mark as failed for retry
                        await conn.execute("""
                            UPDATE decisions
                            SET embedding_status = 'failed',
                                updated_at = NOW()
                            WHERE decision_id = $1
                        """, decision_id)

            logger.info(f"Updated {updated_count} decisions with embeddings")
            return updated_count

    async def create_vector_index(self):
        """
        Create pgvector index after embeddings are populated
        This enables fast similarity search
        """
        async with self.db_pool.acquire() as conn:
            # Check if we have enough embeddings to justify index creation
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM decisions WHERE embedding_status = 'embedded'
            """)

            if count < 100:
                logger.info(f"Only {count} embeddings available, skipping index creation")
                return

            # Create ivfflat index for vector similarity
            logger.info("Creating pgvector index for fast similarity search...")

            try:
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_decisions_embedding
                    ON decisions USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                """)
                logger.info("pgvector index created successfully")

                # Analyze table for query optimization
                await conn.execute("ANALYZE decisions;")

            except Exception as e:
                logger.error(f"Failed to create vector index: {e}")

    async def batch_process(self, batch_size: int = 100, max_batches: Optional[int] = None) -> int:
        """
        Main batch processing loop
        Processes all pending decisions in batches
        """
        if not self.db_pool:
            await self.init_db_pool()

        total_processed = 0
        batch_count = 0

        while True:
            # Check if we've hit max batches limit
            if max_batches and batch_count >= max_batches:
                logger.info(f"Reached max batches limit: {max_batches}")
                break

            # Get pending decisions
            pending = await self.get_pending_decisions(batch_size)
            if not pending:
                logger.info("No more pending decisions to process")
                break

            batch_count += 1
            logger.info(f"Processing batch {batch_count}: {len(pending)} decisions")

            # Extract texts and IDs
            decision_ids = [item[0] for item in pending]
            texts = [item[1] for item in pending]

            # Generate embeddings
            embeddings = await self.generate_embeddings(texts)

            # Update database
            updated = await self.update_embeddings(decision_ids, embeddings)
            total_processed += updated

            logger.info(f"Batch {batch_count} complete: {updated}/{len(pending)} updated")

        # Create vector index if we processed enough data
        if total_processed > 0:
            await self.create_vector_index()

        logger.info(f"Batch processing complete: {total_processed} total decisions processed")
        return total_processed

    async def get_embedding_stats(self) -> dict:
        """Get statistics about embedding status"""
        async with self.db_pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_decisions,
                    COUNT(*) FILTER (WHERE embedding_status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE embedding_status = 'embedded') as embedded,
                    COUNT(*) FILTER (WHERE embedding_status = 'failed') as failed,
                    COUNT(*) FILTER (WHERE embedding_status = 'stale') as stale,
                    AVG(array_length(string_to_array(decision_text, ' '), 1)) as avg_word_count
                FROM decisions
            """)

            return dict(stats)

    async def close(self):
        """Clean up resources"""
        if self.db_pool:
            await self.db_pool.close()
            logger.info("Database connection pool closed")

async def main():
    """CLI entry point for batch embedding"""
    import argparse

    parser = argparse.ArgumentParser(description='Knowledge Aligner Embedding Pipeline')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Number of decisions to process per batch')
    parser.add_argument('--max-batches', type=int, default=None,
                       help='Maximum number of batches to process (for testing)')
    parser.add_argument('--stats', action='store_true',
                       help='Show embedding statistics and exit')
    parser.add_argument('--model', type=str, default='all-MiniLM-L6-v2',
                       help='Sentence-transformers model to use')

    args = parser.parse_args()

    # Initialize pipeline
    pipeline = EmbeddingPipeline(model_name=args.model)

    try:
        await pipeline.init_db_pool()

        if args.stats:
            # Show statistics
            stats = await pipeline.get_embedding_stats()
            print("Embedding Statistics:")
            print(f"  Total decisions: {stats['total_decisions']}")
            print(f"  Pending: {stats['pending']}")
            print(f"  Embedded: {stats['embedded']}")
            print(f"  Failed: {stats['failed']}")
            print(f"  Stale: {stats['stale']}")
            print(f"  Avg words per decision: {stats['avg_word_count']:.1f}")
            return

        # Run batch processing
        total_processed = await pipeline.batch_process(
            batch_size=args.batch_size,
            max_batches=args.max_batches
        )

        print(f"Successfully processed {total_processed} decisions")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)

    finally:
        await pipeline.close()

if __name__ == '__main__':
    asyncio.run(main())