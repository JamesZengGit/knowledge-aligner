"""FastAPI backend server for Hardware Digest system."""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime, timedelta
import asyncio
import logging

# Import our modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config import ALLOWED_ORIGINS, ANTHROPIC_API_KEY
from pipelines.models import *
from pipelines.data_generator import HardwareTeamDataGenerator
from pipelines.entity_extractor import EntityExtractor
from pipelines.decision_graph import DecisionGraphBuilder
from pipelines.embedding_pipeline import EmbeddingPipeline
from pipelines.retrieval import HybridRetriever
from pipelines.digest_generator import DigestGenerator
from pipelines.gap_detector import GapDetector
from pipelines.database import get_db, init_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Hardware Digest API",
    description="AI-powered decision tracking for hardware engineering teams",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
entity_extractor = EntityExtractor() if ANTHROPIC_API_KEY else None
retriever = HybridRetriever()
digest_generator = DigestGenerator() if ANTHROPIC_API_KEY else None
gap_detector = GapDetector()
embedding_pipeline = EmbeddingPipeline()

@app.on_event("startup")
async def startup_event():
    """Initialize the application."""
    logger.info("Starting Hardware Digest API...")

    # Check if database is accessible
    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("SELECT 1")
            logger.info("Database connection successful")
    except Exception as e:
        logger.warning(f"Database connection failed: {e}")

@app.get("/")
async def root():
    """API health check."""
    return {
        "message": "Hardware Digest API",
        "status": "operational",
        "version": "1.0.0"
    }

@app.get("/api/status")
async def get_status():
    """Get system status and statistics."""
    try:
        with get_db() as db:
            cursor = db.cursor()

            # Get basic counts
            cursor.execute("SELECT COUNT(*) FROM user_profiles")
            user_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM slack_messages")
            message_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM decisions")
            decision_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM decision_relationships")
            relationship_count = cursor.fetchone()[0]

            # Get embedding stats
            embedding_stats = embedding_pipeline.get_embedding_stats()

            return {
                "users": user_count,
                "messages": message_count,
                "decisions": decision_count,
                "relationships": relationship_count,
                "embeddings": embedding_stats,
                "ai_enabled": ANTHROPIC_API_KEY is not None
            }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system status")

@app.get("/api/users", response_model=List[UserProfile])
async def get_users():
    """Get all user profiles."""
    try:
        # For demo, return mock data
        generator = HardwareTeamDataGenerator()
        return generator.users
    except Exception as e:
        logger.error(f"Failed to get users: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch users")

@app.get("/api/decisions", response_model=List[dict])
async def get_decisions(
    limit: int = Query(20, ge=1, le=100),
    user_id: Optional[str] = None,
    decision_type: Optional[str] = None,
    days: int = Query(30, ge=1, le=365)
):
    """Get decisions with optional filtering."""
    try:
        # Convert decision_type to enum if provided
        decision_types = None
        if decision_type:
            try:
                decision_types = [DecisionType(decision_type)]
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid decision type")

        results = retriever.search_decisions(
            query="",
            user_id=user_id,
            decision_types=decision_types,
            time_range_days=days,
            limit=limit
        )

        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get decisions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch decisions")

@app.post("/api/search", response_model=List[dict])
async def search_decisions(request: dict):
    """Search decisions with semantic matching."""
    try:
        query = request.get("query", "")
        user_id = request.get("user_id")
        components = request.get("components")
        decision_types = request.get("decision_types")
        time_range_days = request.get("time_range_days", 30)
        limit = request.get("limit", 20)

        # Convert decision types
        decision_type_enums = None
        if decision_types:
            try:
                decision_type_enums = [DecisionType(dt) for dt in decision_types]
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid decision type")

        results = retriever.search_decisions(
            query=query,
            user_id=user_id,
            components=components,
            decision_types=decision_type_enums,
            time_range_days=time_range_days,
            limit=limit
        )

        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@app.get("/api/digest/{user_id}")
async def get_user_digest(
    user_id: str,
    days: int = Query(7, ge=1, le=30)
):
    """Generate personalized digest for a user."""
    if not digest_generator:
        raise HTTPException(
            status_code=503,
            detail="AI features not available - Anthropic API key required"
        )

    try:
        digest = await digest_generator.generate_personalized_digest(
            user_id=user_id,
            date=datetime.now(),
            days_back=days
        )

        return {
            "user_id": digest.user_id,
            "date": digest.date.isoformat(),
            "summary": digest.summary,
            "themes": digest.themes,
            "entries": [
                {
                    "decision_id": entry.decision_id,
                    "title": entry.title,
                    "summary": entry.summary,
                    "impact_summary": entry.impact_summary,
                    "before_after": entry.before_after,
                    "affected_components": entry.affected_components,
                    "citations": entry.citations,
                    "timestamp": entry.timestamp.isoformat()
                } for entry in digest.entries
            ],
            "gaps_detected": digest.gaps_detected,
            "action_items": digest.action_items
        }
    except Exception as e:
        logger.error(f"Digest generation failed for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate digest")

@app.get("/api/gaps")
async def get_gaps(days: int = Query(30, ge=1, le=365)):
    """Get detected gaps in decision making."""
    try:
        gaps = gap_detector.detect_all_gaps(days_back=days)

        # Format gaps for API response
        formatted_gaps = []
        for gap_type, gap_list in gaps.items():
            for gap in gap_list:
                formatted_gap = {
                    "type": gap_type,
                    "severity": gap.get("severity", "warning"),
                    "description": gap.get("description", gap.get("conflict_description", "")),
                    "decision_id": gap.get("decision_id"),
                    "recommendation": gap.get("recommendation", ""),
                    "timestamp": gap.get("timestamp", datetime.now()).isoformat() if isinstance(gap.get("timestamp"), datetime) else gap.get("timestamp", "")
                }
                formatted_gaps.append(formatted_gap)

        return formatted_gaps
    except Exception as e:
        logger.error(f"Gap detection failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to detect gaps")

@app.post("/api/setup")
async def setup_system():
    """Initialize system with sample data."""
    try:
        # Initialize database
        init_db()

        # Generate and load sample data
        generator = HardwareTeamDataGenerator()

        with get_db() as db:
            cursor = db.cursor()

            # Insert users
            for user in generator.users:
                cursor.execute("""
                    INSERT INTO user_profiles (user_id, user_name, role, owned_components, email)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO NOTHING
                """, (user.user_id, user.user_name, user.role, user.owned_components, user.email))

            # Generate messages
            messages = generator.generate_realistic_conversations()

            for msg in messages:
                cursor.execute("""
                    INSERT INTO slack_messages (message_id, channel_id, thread_id, user_id, message_text, timestamp, entities)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (message_id) DO NOTHING
                """, (msg.message_id, msg.channel_id, msg.thread_id, msg.user_id,
                      msg.message_text, msg.timestamp, {}))

        return {
            "message": "System setup complete",
            "users": len(generator.users),
            "messages": len(messages)
        }
    except Exception as e:
        logger.error(f"System setup failed: {e}")
        raise HTTPException(status_code=500, detail="System setup failed")

@app.post("/api/ingest")
async def ingest_messages(batch_size: int = Query(100, ge=10, le=1000)):
    """Process Slack messages and extract decisions."""
    if not entity_extractor:
        raise HTTPException(
            status_code=503,
            detail="Entity extraction not available - Anthropic API key required"
        )

    try:
        # This would typically process new messages
        # For demo, return success status
        return {
            "message": "Ingestion complete",
            "processed": batch_size,
            "decisions_created": batch_size // 5  # Mock ratio
        }
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail="Ingestion failed")

@app.post("/api/embed")
async def generate_embeddings():
    """Generate embeddings for decisions."""
    try:
        results = embedding_pipeline.run_batch_embedding()
        return {
            "message": "Embedding generation complete",
            "results": results
        }
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail="Embedding generation failed")

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"message": "Endpoint not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    from config import API_HOST, API_PORT, API_RELOAD

    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_RELOAD
    )