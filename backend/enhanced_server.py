#!/usr/bin/env python3
"""
Enhanced Knowledge Aligner Server
Production-level FastAPI server with PostgreSQL + pgvector backend
Replaces simple_server.py while maintaining API compatibility
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional

import openai
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import our production modules
from database_manager import db_manager
from hybrid_retrieval import HybridRetrieval
from embedding_pipeline import EmbeddingPipeline
from entity_extraction import EntityExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pydantic models for API
class ChatMessage(BaseModel):
    message: str
    user_id: str

class ChatResponse(BaseModel):
    response: str
    context_decisions: List[Dict] = []
    priority_gaps: List[Dict] = []

class SlackMessageModel(BaseModel):
    message_id: str
    channel_id: str
    thread_id: Optional[str] = None
    user_id: str
    message_text: str
    timestamp: datetime

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup database connections"""
    try:
        logger.info("🚀 Starting Knowledge Aligner Enhanced Server...")

        # Initialize database manager
        await db_manager.init_pool()

        # Initialize OpenAI client
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if openai_api_key:
            app.state.openai_client = openai.OpenAI(api_key=openai_api_key)
            logger.info("✅ OpenAI client initialized")
        else:
            app.state.openai_client = None
            logger.warning("⚠️  OpenAI API key not found - chat features limited")

        logger.info("📊 Enhanced backend available at: http://localhost:8000")
        logger.info("🎨 Frontend should be running at: http://localhost:3000")

        yield

    finally:
        logger.info("Shutting down enhanced server...")
        await db_manager.close()

# Create FastAPI app with lifespan management
app = FastAPI(
    title="Knowledge Aligner API",
    description="Production AI-powered decision tracking system for hardware teams",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoints
@app.get("/")
async def root():
    return {
        "message": "Knowledge Aligner Enhanced API",
        "status": "operational",
        "version": "2.0.0",
        "features": ["postgresql", "pgvector", "hybrid-retrieval", "entity-extraction"]
    }

@app.get("/api/status")
async def get_status():
    """Enhanced system status with database metrics"""
    try:
        status = await db_manager.get_system_status()
        return status
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail="System status unavailable")

# User management
@app.get("/api/users")
async def get_users():
    """Get all users from database"""
    try:
        return await db_manager.get_all_users()
    except Exception as e:
        logger.error(f"Failed to get users: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve users")

@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    """Get specific user"""
    try:
        user = await db_manager.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user")

# Decision management with hybrid retrieval
@app.get("/api/decisions")
async def get_decisions(
    user_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Get decisions with optional user filtering and hybrid retrieval"""
    try:
        decisions = await db_manager.get_decisions(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        return decisions
    except Exception as e:
        logger.error(f"Failed to get decisions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve decisions")

@app.get("/api/decisions/{decision_id}")
async def get_decision(decision_id: int):
    """Get specific decision"""
    try:
        decision = await db_manager.get_decision(decision_id)
        if not decision:
            raise HTTPException(status_code=404, detail="Decision not found")
        return decision
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get decision {decision_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve decision")

# Enhanced gap detection
@app.get("/api/gaps")
async def get_gaps(user_id: str = "alice"):
    """Get personalized gaps using database backend"""
    try:
        gaps = await db_manager.get_gaps(user_id)
        return gaps
    except Exception as e:
        logger.error(f"Failed to get gaps for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve gaps")

@app.post("/api/gaps/priority/{gap_id}")
async def update_gap_priority(gap_id: int, priority: int = Query(...)):
    """Update gap priority in database"""
    try:
        success = await db_manager.update_gap_priority(gap_id, priority)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update priority")
        return {"message": f"Gap {gap_id} priority updated to {priority}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update gap priority: {e}")
        raise HTTPException(status_code=500, detail="Failed to update gap priority")

# Enhanced chat with hybrid retrieval
@app.post("/api/chat")
async def chat(message: ChatMessage):
    """Enhanced chat using database context and hybrid retrieval"""
    try:
        if not app.state.openai_client:
            raise HTTPException(status_code=503, detail="OpenAI API not available")

        # Get enhanced context using database + hybrid retrieval
        context_data = await db_manager.get_chat_context(
            user_id=message.user_id,
            message=message.message
        )

        if "error" in context_data:
            raise HTTPException(status_code=404, detail=context_data["error"])

        user = context_data["user"]
        user_decisions = context_data["recent_decisions"]
        priority_gaps = context_data["priority_gaps"]
        retrieval_stats = context_data.get("retrieval_stats")

        # Create enhanced context for OpenAI
        context = f"""
You are a hardware engineering AI assistant with access to a comprehensive decision database.

User: {user['user_name']} ({user['role']})
Components owned: {', '.join(user['owned_components'])}

Recent relevant decisions (retrieved using hybrid SQL+vector search):
{[{
    'id': d['decision_id'],
    'text': d['decision_text'][:200] + '...' if len(d['decision_text']) > 200 else d['decision_text'],
    'author': d['author_name'],
    'components': d['affected_components'],
    'similarity': d.get('similarity_score', 0.0)
} for d in user_decisions[:5]]}

Detected gaps that need attention (sorted by priority, 1=highest):
{[{
    'description': g['description'],
    'decision_id': g['decision_id'],
    'priority': g['priority'],
    'severity': g['severity'],
    'recommendation': g['recommendation']
} for g in priority_gaps[:3]]}

User question: {message.message}

{f"Search performance: Found {len(user_decisions)} relevant decisions in database using hybrid retrieval." if retrieval_stats else ""}

Instructions:
- Pay attention to gap priorities - Priority 1 is highest, higher numbers are lower priority
- When asked about top priority, refer to the gap with priority number 1 (or lowest number)
- Always reference the correct REQ number from the decision_id field
- Be conversational and actionable, not robotic
- Focus on the user's specific components and responsibilities
- Provide specific next steps when possible
- Keep responses comprehensive but under 300 words
- Use ONLY plain text - no formatting, no markdown, no symbols
- Reference the database search results when relevant
"""

        # Call OpenAI with enhanced context
        response = app.state.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful hardware engineering assistant with access to a comprehensive decision database."},
                {"role": "user", "content": context}
            ],
            max_tokens=400,
            temperature=0.7
        )

        return ChatResponse(
            response=response.choices[0].message.content,
            context_decisions=user_decisions[:3],
            priority_gaps=priority_gaps[:3]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat failed for user {message.user_id}: {e}")
        raise HTTPException(status_code=500, detail="Chat service unavailable")

# Hybrid retrieval endpoint
@app.post("/api/search")
async def hybrid_search(
    query: str,
    user_id: str = "alice",
    limit: int = Query(20, ge=1, le=100)
):
    """Direct access to hybrid retrieval system"""
    try:
        retriever = HybridRetrieval()
        await retriever.init_db_pool(db_manager.database_url)

        results, stats = await retriever.hybrid_search(
            user_id=user_id,
            query_text=query,
            limit=limit
        )

        # Convert results to JSON-serializable format
        search_results = [
            {
                'decision_id': r.decision_id,
                'decision_text': r.decision_text,
                'author_name': r.author_name,
                'author_role': r.author_role,
                'affected_components': r.affected_components,
                'referenced_reqs': r.referenced_reqs,
                'timestamp': r.timestamp.isoformat(),
                'similarity_score': r.similarity_score,
                'before_after': r.before_after
            }
            for r in results
        ]

        return {
            "results": search_results,
            "stats": {
                "total_time_ms": stats.total_time_ms,
                "sql_filter_time_ms": stats.sql_filter_time_ms,
                "semantic_search_time_ms": stats.semantic_search_time_ms,
                "candidates_found": stats.candidates_found,
                "final_results": stats.final_results,
                "query_type": stats.query_type
            }
        }

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search service unavailable")

# AI Pipeline Management
@app.post("/api/embed")
async def run_embedding_pipeline(batch_size: int = Query(100, ge=1, le=500)):
    """Run batch embedding pipeline"""
    try:
        processed = await db_manager.process_pending_embeddings(batch_size)
        return {"message": f"Processed {processed} decisions for embeddings"}
    except Exception as e:
        logger.error(f"Embedding pipeline failed: {e}")
        raise HTTPException(status_code=500, detail="Embedding pipeline failed")

@app.post("/api/ingest")
async def ingest_slack_messages(limit: int = Query(100, ge=1, le=500)):
    """Process Slack messages with entity extraction"""
    try:
        decisions_created = await db_manager.process_slack_messages(limit)
        return {"message": f"Processed Slack messages, created {decisions_created} decisions"}
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail="Message ingestion failed")

@app.post("/api/messages")
async def add_slack_message(message: SlackMessageModel):
    """Add a single Slack message for processing"""
    try:
        # Convert Pydantic model to our internal format
        from entity_extraction import SlackMessage

        slack_message = SlackMessage(
            message_id=message.message_id,
            channel_id=message.channel_id,
            thread_id=message.thread_id,
            user_id=message.user_id,
            message_text=message.message_text,
            timestamp=message.timestamp
        )

        decision_id = await db_manager.extractor.process_slack_message(slack_message)

        if decision_id:
            return {"message": f"Created decision {decision_id} from message", "decision_id": decision_id}
        else:
            return {"message": "Message processed but no decision created"}

    except Exception as e:
        logger.error(f"Failed to process message: {e}")
        raise HTTPException(status_code=500, detail="Failed to process message")

# Performance benchmarking
@app.get("/api/benchmark")
async def benchmark_system():
    """Run system performance benchmarks"""
    try:
        retriever = HybridRetrieval()
        await retriever.init_db_pool(db_manager.database_url)

        test_queries = [
            "motor torque requirements",
            "power supply capacity",
            "firmware update security",
            "PCB design changes"
        ]

        results = await retriever.benchmark_performance(test_queries, "alice")
        await retriever.close()

        return {"benchmark_results": results}

    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        raise HTTPException(status_code=500, detail="Benchmark failed")

# Legacy compatibility endpoints (for existing frontend)
@app.get("/api/digest/prioritized/{user_id}")
async def get_prioritized_digest(user_id: str):
    """Legacy compatibility for prioritized digest"""
    try:
        # Use database-backed context
        context_data = await db_manager.get_chat_context(user_id)

        if "error" in context_data:
            raise HTTPException(status_code=404, detail=context_data["error"])

        user = context_data["user"]
        priority_gaps = context_data["priority_gaps"]

        # Generate prioritized topics from user's components
        prioritized_topics = [
            {
                "name": component,
                "priority": 8,  # High priority for owned components
                "reason": f"Your primary responsibility as {user['role']}",
                "impact_level": "high"
            }
            for component in user['owned_components'][:3]
        ]

        return {
            "user_id": user_id,
            "prioritized_topics": prioritized_topics,
            "prioritized_gaps": priority_gaps[:4],
            "trend_analysis": f"Recent activity shows {len(priority_gaps)} gaps requiring attention for your {user['role']} responsibilities.",
            "key_insight": f"Focus on {user['owned_components'][0] if user['owned_components'] else 'component'} alignment with cross-functional teams to maintain project momentum."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate prioritized digest: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate digest")

if __name__ == "__main__":
    import uvicorn

    # Check for required environment variables
    required_vars = ["DATABASE_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.warning(f"Missing environment variables: {missing_vars}")
        logger.info("Using default values for development")

    # Run server
    uvicorn.run(
        "enhanced_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )