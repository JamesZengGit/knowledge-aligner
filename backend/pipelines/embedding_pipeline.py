"""Batch embedding pipeline using sentence-transformers."""

import os
import numpy as np
from typing import List, Tuple
from sentence_transformers import SentenceTransformer
import psycopg2
import psycopg2.extras
from datetime import datetime
import logging
from dotenv import load_dotenv

load_dotenv()

class EmbeddingPipeline:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize embedding pipeline with sentence transformer model."""
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = 768  # Dimension for all-MiniLM-L6-v2
        self.batch_size = int(os.getenv("BATCH_SIZE", 1000))

        # Database connection
        self.db_url = os.getenv("DATABASE_URL")

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def run_batch_embedding(self) -> Dict[str, int]:
        """Run batch embedding process for pending decisions."""
        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

                # Fetch pending decisions
                pending_decisions = self._fetch_pending_decisions(cursor)

                if not pending_decisions:
                    self.logger.info("No pending decisions found for embedding")
                    return {"processed": 0, "succeeded": 0, "failed": 0}

                # Process in batches
                total_processed = 0
                total_succeeded = 0
                total_failed = 0

                for batch_start in range(0, len(pending_decisions), self.batch_size):
                    batch_end = min(batch_start + self.batch_size, len(pending_decisions))
                    batch = pending_decisions[batch_start:batch_end]

                    succeeded, failed = self._process_batch(cursor, batch)

                    total_processed += len(batch)
                    total_succeeded += succeeded
                    total_failed += failed

                    conn.commit()

                    self.logger.info(f"Processed batch {batch_start//self.batch_size + 1}: "
                                   f"{succeeded} succeeded, {failed} failed")

                return {
                    "processed": total_processed,
                    "succeeded": total_succeeded,
                    "failed": total_failed
                }

        except Exception as e:
            self.logger.error(f"Batch embedding failed: {e}")
            raise

    def _fetch_pending_decisions(self, cursor) -> List[Dict]:
        """Fetch decisions with pending embedding status."""
        query = """
        SELECT decision_id, decision_text, affected_components, referenced_reqs
        FROM decisions
        WHERE embedding_status = 'pending'
        ORDER BY timestamp DESC
        LIMIT %s
        """

        cursor.execute(query, (self.batch_size * 10,))  # Fetch more than one batch
        return cursor.fetchall()

    def _process_batch(self, cursor, decisions: List[Dict]) -> Tuple[int, int]:
        """Process a batch of decisions for embedding."""
        try:
            # Prepare texts for embedding
            texts = []
            for decision in decisions:
                # Combine decision text with metadata for richer embeddings
                text = self._prepare_text_for_embedding(decision)
                texts.append(text)

            # Generate embeddings
            self.logger.info(f"Generating embeddings for {len(texts)} decisions")
            embeddings = self.model.encode(texts, batch_size=32, show_progress_bar=False)

            # Update database
            succeeded = 0
            failed = 0

            for decision, embedding in zip(decisions, embeddings):
                try:
                    self._update_decision_embedding(cursor, decision['decision_id'], embedding)
                    succeeded += 1
                except Exception as e:
                    self.logger.error(f"Failed to update decision {decision['decision_id']}: {e}")
                    self._mark_embedding_failed(cursor, decision['decision_id'])
                    failed += 1

            return succeeded, failed

        except Exception as e:
            self.logger.error(f"Batch processing failed: {e}")
            # Mark all as failed
            for decision in decisions:
                self._mark_embedding_failed(cursor, decision['decision_id'])
            return 0, len(decisions)

    def _prepare_text_for_embedding(self, decision: Dict) -> str:
        """Prepare text for embedding by combining decision text with metadata."""
        components = " ".join(decision.get('affected_components', []))
        requirements = " ".join(decision.get('referenced_reqs', []))

        # Combine with weighted importance
        text_parts = [
            decision['decision_text'],  # Main content
        ]

        if components:
            text_parts.append(f"Components: {components}")

        if requirements:
            text_parts.append(f"Requirements: {requirements}")

        return " | ".join(text_parts)

    def _update_decision_embedding(self, cursor, decision_id: int, embedding: np.ndarray):
        """Update decision with generated embedding."""
        # Convert numpy array to list for PostgreSQL
        embedding_list = embedding.tolist()

        update_query = """
        UPDATE decisions
        SET embedding = %s, embedding_status = 'embedded', updated_at = %s
        WHERE decision_id = %s
        """

        cursor.execute(update_query, (embedding_list, datetime.now(), decision_id))

    def _mark_embedding_failed(self, cursor, decision_id: int):
        """Mark decision embedding as failed."""
        update_query = """
        UPDATE decisions
        SET embedding_status = 'failed', updated_at = %s
        WHERE decision_id = %s
        """

        cursor.execute(update_query, (datetime.now(), decision_id))

    def embed_single_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text (for query purposes)."""
        return self.model.encode([text])[0]

    def get_embedding_stats(self) -> Dict[str, int]:
        """Get statistics about embedding status."""
        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor()

                stats_query = """
                SELECT
                    embedding_status,
                    COUNT(*) as count
                FROM decisions
                GROUP BY embedding_status
                """

                cursor.execute(stats_query)
                results = cursor.fetchall()

                stats = {"pending": 0, "embedded": 0, "failed": 0}
                for status, count in results:
                    stats[status] = count

                return stats

        except Exception as e:
            self.logger.error(f"Failed to get embedding stats: {e}")
            return {"error": str(e)}

    def cleanup_failed_embeddings(self) -> int:
        """Reset failed embeddings to pending for retry."""
        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor()

                cleanup_query = """
                UPDATE decisions
                SET embedding_status = 'pending', updated_at = %s
                WHERE embedding_status = 'failed'
                """

                cursor.execute(cleanup_query, (datetime.now(),))
                count = cursor.rowcount
                conn.commit()

                self.logger.info(f"Reset {count} failed embeddings to pending")
                return count

        except Exception as e:
            self.logger.error(f"Failed to cleanup embeddings: {e}")
            return 0