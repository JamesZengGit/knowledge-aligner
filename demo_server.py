#!/usr/bin/env python3
"""
Knowledge Aligner - Full-Stack Backend with Two-Tier Architecture
Tier 1: Redis live context buffer (real-time, 2-hour window)
Tier 2: PostgreSQL persistent storage (long-term knowledge)
All existing frontend API endpoints preserved.
"""

import os
import sys
import json
import time
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv
# Load from project root .env regardless of working directory
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

import openai
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add backend directory to path for Two-Tier imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from two_tier_orchestrator import TwoTierOrchestrator
from redis_context_buffer import LiveContextMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Pydantic models (shapes unchanged — frontend compatibility) ──────────────

class ChatMessage(BaseModel):
    message: str
    user_id: str

class ChatResponse(BaseModel):
    response: str
    context_decisions: List[Dict] = []
    priority_gaps: List[Dict] = []

# ─── Static demo data ─────────────────────────────────────────────────────────

USERS_DATA = [
    {"user_id": "alice",   "user_name": "Alice Chen",       "role": "Hardware Lead",      "owned_components": ["motor", "power_supply", "mechanical"],   "email": "alice@company.com"},
    {"user_id": "bob",     "user_name": "Bob Wilson",        "role": "Firmware Engineer",  "owned_components": ["firmware", "security", "bootloader"],    "email": "bob@company.com"},
    {"user_id": "charlie", "user_name": "Charlie Davis",     "role": "Test Engineer",      "owned_components": ["validation", "testing", "qa"],           "email": "charlie@company.com"},
    {"user_id": "diana",   "user_name": "Diana Rodriguez",   "role": "Systems Architect",  "owned_components": ["architecture", "integration", "protocols"],"email": "diana@company.com"},
    {"user_id": "erik",    "user_name": "Erik Thompson",     "role": "PCB Designer",       "owned_components": ["pcb", "layout", "components"],           "email": "erik@company.com"},
    {"user_id": "fiona",   "user_name": "Fiona Kim",         "role": "Software Lead",      "owned_components": ["software", "ui", "drivers"],             "email": "fiona@company.com"},
]

DECISIONS_DATA = [
    {
        "decision_id": 241, "author_user_id": "diana", "author_name": "Diana Rodriguez",
        "author_role": "Systems Architect", "decision_type": "design_decision",
        "thread_id": "thread_241", "timestamp": "2024-01-10T08:30:00Z",
        "decision_text": "Selected CAN bus protocol over I2C for motor controller communication due to noise immunity requirements in industrial environment",
        "affected_components": ["architecture", "protocols", "motor"],
        "referenced_reqs": ["REQ-200", "REQ-201"], "similarity_score": 0.92,
        "before_after": {"before": "I2C communication", "after": "CAN bus protocol"},
    },
    {
        "decision_id": 242, "author_user_id": "erik", "author_name": "Erik Thompson",
        "author_role": "PCB Designer", "decision_type": "requirement_change",
        "thread_id": "thread_242", "timestamp": "2024-01-11T11:15:00Z",
        "decision_text": "Changed PCB stackup from 4-layer to 6-layer to improve signal integrity for high-speed differential pairs",
        "affected_components": ["pcb", "layout", "components"],
        "referenced_reqs": ["REQ-210", "REQ-211"], "similarity_score": 0.88,
        "before_after": {"before": "4-layer PCB", "after": "6-layer PCB"},
    },
    {
        "decision_id": 243, "author_user_id": "fiona", "author_name": "Fiona Kim",
        "author_role": "Software Lead", "decision_type": "design_decision",
        "thread_id": "thread_243", "timestamp": "2024-01-12T14:20:00Z",
        "decision_text": "Implemented real-time OS (FreeRTOS) instead of bare-metal for better task scheduling and reliability",
        "affected_components": ["software", "firmware", "drivers"],
        "referenced_reqs": ["REQ-220", "REQ-221"], "similarity_score": 0.91,
        "before_after": {"before": "Bare-metal implementation", "after": "FreeRTOS"},
    },
    {
        "decision_id": 244, "author_user_id": "bob", "author_name": "Bob Wilson",
        "author_role": "Firmware Engineer", "decision_type": "approval",
        "thread_id": "thread_244", "timestamp": "2024-01-13T16:45:00Z",
        "decision_text": "Approved secure boot implementation with RSA-2048 signature verification for production firmware",
        "affected_components": ["firmware", "security", "bootloader"],
        "referenced_reqs": ["REQ-230", "REQ-231"], "similarity_score": 0.94,
        "before_after": {"before": "No boot verification", "after": "RSA-2048 secure boot"},
    },
    {
        "decision_id": 245, "author_user_id": "alice", "author_name": "Alice Chen",
        "author_role": "Hardware Lead", "decision_type": "requirement_change",
        "thread_id": "thread_245", "timestamp": "2024-01-15T10:30:00Z",
        "decision_text": "Updated motor torque requirement from 2.0Nm to 2.5Nm based on customer feedback and field testing results",
        "affected_components": ["motor", "power_supply", "mechanical"],
        "referenced_reqs": ["REQ-240", "REQ-241"], "similarity_score": 0.95,
        "before_after": {"before": "Motor torque: 2.0Nm", "after": "Motor torque: 2.5Nm"},
    },
    {
        "decision_id": 246, "author_user_id": "erik", "author_name": "Erik Thompson",
        "author_role": "PCB Designer", "decision_type": "design_decision",
        "thread_id": "thread_246", "timestamp": "2024-01-16T14:15:00Z",
        "decision_text": "Switched power supply IC from linear regulator to switching regulator for improved efficiency (85% vs 60%)",
        "affected_components": ["pcb", "power_supply", "components"],
        "referenced_reqs": ["REQ-245", "REQ-250"], "similarity_score": 0.89,
        "before_after": {"before": "Linear regulator (60% efficiency)", "after": "Switching regulator (85% efficiency)"},
    },
    {
        "decision_id": 247, "author_user_id": "charlie", "author_name": "Charlie Davis",
        "author_role": "Test Engineer", "decision_type": "approval",
        "thread_id": "thread_247", "timestamp": "2024-01-17T09:45:00Z",
        "decision_text": "Approved comprehensive EMC testing protocol including radiated emissions, conducted emissions, and ESD testing",
        "affected_components": ["validation", "testing", "qa", "pcb"],
        "referenced_reqs": ["REQ-260", "REQ-261"], "similarity_score": 0.82,
        "before_after": {"before": "Basic functional testing", "after": "Full EMC compliance testing"},
    },
    {
        "decision_id": 248, "author_user_id": "diana", "author_name": "Diana Rodriguez",
        "author_role": "Systems Architect", "decision_type": "design_decision",
        "thread_id": "thread_248", "timestamp": "2024-01-18T13:20:00Z",
        "decision_text": "Implemented watchdog timer with 2-second timeout to automatically reset system in case of firmware hang",
        "affected_components": ["architecture", "firmware", "safety"],
        "referenced_reqs": ["REQ-270", "REQ-271"], "similarity_score": 0.86,
        "before_after": {"before": "No automatic recovery", "after": "Hardware watchdog with 2s timeout"},
    },
    {
        "decision_id": 249, "author_user_id": "fiona", "author_name": "Fiona Kim",
        "author_role": "Software Lead", "decision_type": "requirement_change",
        "thread_id": "thread_249", "timestamp": "2024-01-19T11:30:00Z",
        "decision_text": "Changed communication interface from UART to USB CDC for better debugging and field updates",
        "affected_components": ["software", "ui", "protocols"],
        "referenced_reqs": ["REQ-280", "REQ-281"], "similarity_score": 0.90,
        "before_after": {"before": "UART interface", "after": "USB CDC"},
    },
    {
        "decision_id": 250, "author_user_id": "alice", "author_name": "Alice Chen",
        "author_role": "Hardware Lead", "decision_type": "approval",
        "thread_id": "thread_250", "timestamp": "2024-01-20T15:45:00Z",
        "decision_text": "Approved temperature sensors placement: one on motor housing, one on power supply, and one ambient for thermal management",
        "affected_components": ["motor", "power_supply", "mechanical", "sensors"],
        "referenced_reqs": ["REQ-290", "REQ-291"], "similarity_score": 0.87,
        "before_after": {"before": "Single temperature sensor", "after": "Three-point thermal monitoring"},
    },
    {
        "decision_id": 251, "author_user_id": "bob", "author_name": "Bob Wilson",
        "author_role": "Firmware Engineer", "decision_type": "design_decision",
        "thread_id": "thread_251", "timestamp": "2024-01-22T10:15:00Z",
        "decision_text": "Implemented over-the-air (OTA) firmware update capability with encrypted delta updates",
        "affected_components": ["firmware", "security", "software"],
        "referenced_reqs": ["REQ-300", "REQ-301"], "similarity_score": 0.93,
        "before_after": {"before": "Manual firmware updates via cable", "after": "Encrypted OTA delta updates"},
    },
    {
        "decision_id": 252, "author_user_id": "charlie", "author_name": "Charlie Davis",
        "author_role": "Test Engineer", "decision_type": "requirement_change",
        "thread_id": "thread_252", "timestamp": "2024-01-23T14:30:00Z",
        "decision_text": "Extended operating temperature range from -10C to +60C to -20C to +70C for harsh environment deployment",
        "affected_components": ["validation", "testing", "components", "mechanical"],
        "referenced_reqs": ["REQ-310", "REQ-311"], "similarity_score": 0.84,
        "before_after": {"before": "Operating range: -10C to +60C", "after": "Operating range: -20C to +70C"},
    },
]

MOCK_GAPS = {
    "alice": [
        {"gap_id": "g246", "type": "missing_stakeholder", "severity": "critical", "description": "REQ-246 power supply efficiency change affects your components but you weren't consulted", "decision_id": 246, "priority": 1, "recommendation": "Contact Erik Thompson to understand power supply impact on motor requirements", "timestamp": "2024-01-16T14:15:00Z"},
        {"gap_id": "g252", "type": "conflict", "severity": "warning", "description": "REQ-252 temperature range extension conflicts with current motor specifications", "decision_id": 252, "priority": 2, "recommendation": "Review motor operating range compatibility with -20C to +70C requirement", "timestamp": "2024-01-23T14:30:00Z"},
        {"gap_id": "g245", "type": "broken_dependency", "severity": "warning", "description": "Motor torque increase (REQ-245) may require power supply capacity verification", "decision_id": 245, "priority": 3, "recommendation": "Verify power supply can handle increased motor current draw", "timestamp": "2024-01-15T10:30:00Z"},
    ],
    "bob": [
        {"gap_id": "g248", "type": "missing_stakeholder", "severity": "critical", "description": "REQ-248 watchdog timer implementation needs firmware integration planning", "decision_id": 248, "priority": 1, "recommendation": "Coordinate with Diana Rodriguez on watchdog integration with firmware architecture", "timestamp": "2024-01-18T13:20:00Z"},
        {"gap_id": "g251", "type": "conflict", "severity": "warning", "description": "OTA update capability (REQ-251) conflicts with secure boot timing requirements", "decision_id": 251, "priority": 2, "recommendation": "Review boot sequence timing with OTA delta update implementation", "timestamp": "2024-01-22T10:15:00Z"},
    ],
    "charlie": [
        {"gap_id": "g241", "type": "missing_stakeholder", "severity": "critical", "description": "REQ-241 CAN bus protocol change requires new test equipment and procedures", "decision_id": 241, "priority": 1, "recommendation": "Request CAN bus testing tools and update validation procedures", "timestamp": "2024-01-10T08:30:00Z"},
        {"gap_id": "g247", "type": "broken_dependency", "severity": "warning", "description": "EMC testing protocol approved but missing test schedule coordination", "decision_id": 247, "priority": 2, "recommendation": "Schedule EMC lab time and coordinate with PCB layout completion", "timestamp": "2024-01-17T09:45:00Z"},
    ],
    "diana": [
        {"gap_id": "g249", "type": "conflict", "severity": "warning", "description": "USB CDC interface (REQ-249) may interfere with CAN bus timing requirements", "decision_id": 249, "priority": 1, "recommendation": "Analyze USB enumeration impact on real-time CAN bus performance", "timestamp": "2024-01-19T11:30:00Z"},
        {"gap_id": "g243", "type": "missing_stakeholder", "severity": "warning", "description": "FreeRTOS implementation needs system-level resource allocation planning", "decision_id": 243, "priority": 2, "recommendation": "Define memory partitioning and task priorities with Fiona Kim", "timestamp": "2024-01-12T14:20:00Z"},
    ],
    "erik": [
        {"gap_id": "g250", "type": "missing_stakeholder", "severity": "critical", "description": "Temperature sensor placement (REQ-250) requires PCB layout modifications", "decision_id": 250, "priority": 1, "recommendation": "Coordinate sensor placement with Alice Chen for optimal thermal monitoring", "timestamp": "2024-01-20T15:45:00Z"},
        {"gap_id": "g242", "type": "conflict", "severity": "warning", "description": "6-layer PCB stackup conflicts with cost targets for production volume", "decision_id": 242, "priority": 2, "recommendation": "Analyze cost impact vs signal integrity benefits for final design review", "timestamp": "2024-01-11T11:15:00Z"},
    ],
    "fiona": [
        {"gap_id": "g244", "type": "missing_stakeholder", "severity": "critical", "description": "Secure boot implementation (REQ-244) needs software integration with bootloader", "decision_id": 244, "priority": 1, "recommendation": "Coordinate RSA verification implementation with Bob Wilson", "timestamp": "2024-01-13T16:45:00Z"},
        {"gap_id": "g249b", "type": "broken_dependency", "severity": "warning", "description": "USB CDC interface implementation depends on FreeRTOS task structure", "decision_id": 249, "priority": 2, "recommendation": "Define USB handling task priorities and memory allocation", "timestamp": "2024-01-19T11:30:00Z"},
    ],
}

# ─── Startup helpers ──────────────────────────────────────────────────────────

async def _seed_postgres(orchestrator: TwoTierOrchestrator):
    """Insert demo decisions into PostgreSQL (Tier 2) if not already present."""
    if not orchestrator.db_pool:
        return
    try:
        async with orchestrator.db_pool.acquire() as conn:
            # Seed users first
            for u in USERS_DATA:
                await conn.execute("""
                    INSERT INTO user_profiles (user_id, user_name, role, owned_components, email)
                    VALUES ($1, $2, $3, $4, $5) ON CONFLICT (user_id) DO NOTHING
                """, u["user_id"], u["user_name"], u["role"], u["owned_components"], u["email"])

            # Seed decisions
            for d in DECISIONS_DATA:
                await conn.execute("""
                    INSERT INTO decisions (
                        thread_id, timestamp, author_user_id, author_name, author_role,
                        decision_type, decision_text, affected_components,
                        referenced_reqs, similarity_score, before_after, embedding_status
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,'pending')
                    ON CONFLICT (thread_id) DO NOTHING
                """,
                    d["thread_id"],
                    datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")),
                    d["author_user_id"], d["author_name"], d["author_role"],
                    d["decision_type"], d["decision_text"],
                    d["affected_components"], d.get("referenced_reqs", []),
                    d.get("similarity_score"), json.dumps(d.get("before_after", {}))
                )

            # Build display_decision_id → PostgreSQL decision_id mapping via thread_id
            display_to_thread = {d["decision_id"]: d["thread_id"] for d in DECISIONS_DATA}
            pg_id_rows = await conn.fetch("SELECT decision_id, thread_id FROM decisions")
            thread_to_pg_id = {r["thread_id"]: r["decision_id"] for r in pg_id_rows}

            # Seed mock gaps with resolved PostgreSQL decision_ids
            for user_id, gaps in MOCK_GAPS.items():
                for g in gaps:
                    display_did = g.get("decision_id")
                    thread_id = display_to_thread.get(display_did) if display_did else None
                    pg_decision_id = thread_to_pg_id.get(thread_id) if thread_id else None
                    await conn.execute("""
                        INSERT INTO gaps (gap_id, type, severity, description, assignee_id,
                                         decision_id, recommendation)
                        VALUES ($1,$2,$3,$4,$5,$6,$7) ON CONFLICT (gap_id) DO NOTHING
                    """, g["gap_id"], g["type"], g["severity"], g["description"],
                        user_id, pg_decision_id, g.get("recommendation"))

        logger.info(f"✅ PostgreSQL seeded: {len(USERS_DATA)} users, {len(DECISIONS_DATA)} decisions, {sum(len(v) for v in MOCK_GAPS.values())} gaps")
    except Exception as e:
        logger.warning(f"⚠️  PostgreSQL seed partial failure: {e}")


async def _seed_redis(orchestrator: TwoTierOrchestrator):
    """Pre-populate Redis (Tier 1) with existing decisions as live context."""
    try:
        for d in DECISIONS_DATA:
            msg = LiveContextMessage(
                message_id=f"seed_{d['decision_id']}",
                user_id=d["author_user_id"],
                text=d["decision_text"],
                entities={
                    "reqs": d.get("referenced_reqs", []),
                    "components": d["affected_components"],
                    "users_mentioned": [],
                    "topics": [],
                },
                decision_id=str(d["decision_id"]),
                timestamp=d["timestamp"],
                channel_id="hardware-team",
            )
            await orchestrator.redis_buffer.add_message("hardware-team", msg)
        logger.info(f"✅ Redis seeded with {len(DECISIONS_DATA)} decisions")
    except Exception as e:
        logger.warning(f"⚠️  Redis seed failed: {e}")


# ─── Application lifespan ─────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    openai_key = os.getenv("OPENAI_API_KEY")

    # Initialize OpenAI client (sync) for chat fallback
    if openai_key:
        app.state.openai_client = openai.OpenAI(api_key=openai_key)
        logger.info("✅ OpenAI client initialized")
    else:
        app.state.openai_client = None
        logger.warning("⚠️  OPENAI_API_KEY not set — using template responses")

    # Initialize Two-Tier Orchestrator
    orchestrator = TwoTierOrchestrator(
        redis_url="redis://localhost:6379",
        postgres_url="postgresql://postgres:postgres@localhost:5432/knowledge_aligner",
        openai_api_key=openai_key,
    )
    try:
        await orchestrator.initialize()
        app.state.orchestrator = orchestrator
        logger.info("✅ Two-Tier Orchestrator initialized (Redis + PostgreSQL)")

        await _seed_postgres(orchestrator)
        await _seed_redis(orchestrator)
    except Exception as e:
        logger.warning(f"⚠️  Orchestrator init failed, using mock fallback: {e}")
        app.state.orchestrator = None

    yield

    if app.state.orchestrator:
        await app.state.orchestrator.shutdown()
        logger.info("🔌 Two-Tier Orchestrator shut down")


# ─── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Knowledge Aligner API",
    description="Two-Tier Real-Time Context Architecture for hardware engineering teams",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_user(user_id: str) -> Dict:
    user = next((u for u in USERS_DATA if u["user_id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return user


def _decision_row(row: dict) -> dict:
    """Convert an asyncpg row to a dict, parsing JSONB fields into objects."""
    d = dict(row)
    if isinstance(d.get("before_after"), str):
        try:
            d["before_after"] = json.loads(d["before_after"])
        except (json.JSONDecodeError, TypeError):
            pass
    return d


# ─── API Endpoints (shapes preserved for frontend compatibility) ───────────────

@app.get("/")
async def root():
    orch = app.state.orchestrator
    return {
        "message": "Knowledge Aligner API",
        "status": "operational",
        "version": "3.0.0",
        "architecture": "two-tier",
        "redis": bool(orch and orch.redis_buffer.redis_client),
        "postgres": bool(orch and orch.db_pool),
    }

@app.get("/api/status")
async def get_status():
    orch: Optional[TwoTierOrchestrator] = app.state.orchestrator
    stats = await orch.get_stats() if orch else {}
    return {
        "users": len(USERS_DATA),
        "decisions": len(DECISIONS_DATA),
        "messages": stats.get("messages_processed", 0),
        "relationships": 0,
        "embeddings": {"embedded": 0, "pending": len(DECISIONS_DATA), "failed": 0},
        "database_url": "postgresql://localhost:5432/knowledge_aligner",
        "redis_url": "redis://localhost:6379",
        "ai_enabled": bool(os.getenv("OPENAI_API_KEY")),
        "two_tier_stats": stats,
    }

@app.get("/api/users")
async def get_users():
    return USERS_DATA

@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    return _get_user(user_id)

@app.get("/api/decisions")
async def get_decisions(
    user_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get decisions — reads from PostgreSQL if available, falls back to static data."""
    orch: Optional[TwoTierOrchestrator] = app.state.orchestrator
    if orch and orch.db_pool:
        try:
            async with orch.db_pool.acquire() as conn:
                if user_id:
                    user = _get_user(user_id)
                    components = user["owned_components"]
                    rows = await conn.fetch("""
                        SELECT decision_id, thread_id, timestamp, author_user_id,
                               author_name, author_role, decision_type, decision_text,
                               affected_components, referenced_reqs, similarity_score, before_after
                        FROM decisions
                        WHERE affected_components && $1::text[]
                        ORDER BY timestamp DESC LIMIT $2 OFFSET $3
                    """, components, limit, offset)
                else:
                    rows = await conn.fetch("""
                        SELECT decision_id, thread_id, timestamp, author_user_id,
                               author_name, author_role, decision_type, decision_text,
                               affected_components, referenced_reqs, similarity_score, before_after
                        FROM decisions ORDER BY timestamp DESC LIMIT $1 OFFSET $2
                    """, limit, offset)
                return [_decision_row(r) for r in rows]
        except Exception as e:
            logger.warning(f"PostgreSQL decisions query failed, using static: {e}")

    # Fallback: static data
    data = DECISIONS_DATA
    if user_id:
        user = _get_user(user_id)
        comps = set(user["owned_components"])
        data = [d for d in data if set(d["affected_components"]) & comps]
    return data[offset: offset + limit]

@app.get("/api/decisions/{decision_id}")
async def get_decision(decision_id: int):
    orch: Optional[TwoTierOrchestrator] = app.state.orchestrator
    if orch and orch.db_pool:
        try:
            async with orch.db_pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM decisions WHERE decision_id=$1", decision_id)
                if row:
                    return _decision_row(row)
        except Exception:
            pass
    d = next((d for d in DECISIONS_DATA if d["decision_id"] == decision_id), None)
    if not d:
        raise HTTPException(status_code=404, detail="Decision not found")
    return d

@app.get("/api/gaps")
async def get_gaps(user_id: str = "alice"):
    """Get gaps — reads from PostgreSQL if available, falls back to mock data."""
    orch: Optional[TwoTierOrchestrator] = app.state.orchestrator
    if orch and orch.db_pool:
        try:
            async with orch.db_pool.acquire() as conn:
                # Get user-specific gap priorities
                rows = await conn.fetch("""
                    SELECT g.gap_id, g.type, g.severity, g.description,
                           g.decision_id, g.recommendation, g.created_at,
                           COALESCE(gp.priority, g.decision_id % 3 + 1) AS priority
                    FROM gaps g
                    LEFT JOIN gap_priority gp ON g.gap_id = gp.gap_id AND gp.user_id = $1
                    WHERE g.assignee_id = $1
                    ORDER BY COALESCE(gp.priority, g.decision_id % 3 + 1) ASC
                """, user_id)
                if rows:
                    return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"PostgreSQL gaps query failed, using mock: {e}")

    return MOCK_GAPS.get(user_id, [])

@app.post("/api/gaps/priority/{gap_id}")
async def update_gap_priority(
    gap_id: str,
    priority: int = Query(...),
    user_id: str = Query("alice"),
):
    """Update gap priority — persists to PostgreSQL gap_priority table.

    The frontend passes gap.decision_id as gap_id, so we look up the
    gaps table by decision_id to find the actual gap_id string.
    """
    orch: Optional[TwoTierOrchestrator] = app.state.orchestrator
    if orch and orch.db_pool:
        try:
            async with orch.db_pool.acquire() as conn:
                # Resolve gap_id: frontend may pass decision_id (int) or actual gap_id (str)
                real_gap_id = gap_id  # default: assume it's already a gap_id string
                if gap_id.isdigit():
                    row = await conn.fetchrow(
                        "SELECT gap_id FROM gaps WHERE decision_id=$1 AND assignee_id=$2 LIMIT 1",
                        int(gap_id), user_id
                    )
                    if row:
                        real_gap_id = row["gap_id"]

                await conn.execute("""
                    INSERT INTO gap_priority (gap_id, user_id, priority, updated_at)
                    VALUES ($1, $2, $3, NOW())
                    ON CONFLICT (gap_id, user_id) DO UPDATE SET priority=$3, updated_at=NOW()
                """, real_gap_id, user_id, priority)
        except Exception as e:
            logger.warning(f"Gap priority update failed: {e}")
    return {"success": True, "message": f"Gap {gap_id} priority updated to {priority}"}

@app.get("/api/digest/prioritized/{user_id}")
async def get_prioritized_digest(user_id: str):
    """Personalized digest — unchanged shape."""
    user = _get_user(user_id)
    gaps = await get_gaps(user_id)
    return {
        "user_id": user_id,
        "prioritized_topics": [
            {"name": c, "priority": 8, "reason": f"Primary responsibility as {user['role']}", "impact_level": "high"}
            for c in user["owned_components"][:3]
        ],
        "prioritized_gaps": gaps[:4],
        "trend_analysis": f"Recent activity shows {len(gaps)} gaps requiring attention for {user['role']} responsibilities.",
        "key_insight": f"Focus on {user['owned_components'][0]} alignment with cross-functional teams.",
    }

@app.post("/api/chat")
async def chat(message: ChatMessage):
    """
    Two-Tier context-aware chat:
    1. process_incoming_message() → entity extraction + Redis context lookup
    2. Detect gaps (user not in original decision discussion)
    3. Generate GPT-4o-mini response with injected context
    Response shape preserved: {response, context_decisions, priority_gaps}
    """
    user = _get_user(message.user_id)
    gaps = await get_gaps(message.user_id)
    orch: Optional[TwoTierOrchestrator] = app.state.orchestrator

    ai_response = None

    if orch:
        try:
            result = await orch.process_incoming_message(
                message_id=f"chat_{int(time.time())}",
                channel_id="hardware-team",
                user_id=message.user_id,
                message_text=message.message,
            )
            logger.info(
                f"Two-Tier result: inject={result.get('context_injected')}, "
                f"gap={result.get('gap_created')}, "
                f"time={result.get('processing_time_ms', 0):.0f}ms"
            )

            # Use orchestrator response if context was injected
            if result.get("context_injected") and result.get("response"):
                ai_response = result["response"]

            # Re-fetch gaps if a new one was created
            if result.get("gap_created"):
                gaps = await get_gaps(message.user_id)

        except Exception as e:
            logger.error(f"Orchestrator processing failed: {e}")

    # If orchestrator didn't produce a response, fall back to direct OpenAI call
    if not ai_response:
        if app.state.openai_client:
            system_prompt = (
                "You are a hardware engineering AI assistant for a team building an embedded "
                "control system. Help engineers stay aligned on decisions and specifications. "
                "Be concise (3-4 sentences max) and reference specific decision IDs when relevant."
            )
            context_block = "\n".join(
                f"- Decision #{g.get('decision_id')}: {g.get('description')}"
                for g in gaps[:3]
            )
            user_prompt = (
                f"User: {user['user_name']} ({user['role']})\n"
                f"Components: {', '.join(user['owned_components'])}\n\n"
                f"Priority gaps:\n{context_block}\n\n"
                f"Question: {message.message}"
            )
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None,
                lambda: app.state.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=300,
                    temperature=0.4,
                )
            )
            ai_response = resp.choices[0].message.content
        else:
            ai_response = (
                f"Hello {user['user_name']}! As {user['role']} managing "
                f"{', '.join(user['owned_components'])}, your top gap is: "
                f"{gaps[0]['description'] if gaps else 'no gaps detected'}."
            )

    context_decisions = await get_decisions(user_id=message.user_id, limit=3, offset=0)
    return ChatResponse(
        response=ai_response,
        context_decisions=context_decisions,
        priority_gaps=gaps[:3],
    )

@app.post("/api/ingest/message")
async def ingest_message(payload: dict):
    """
    Process a new message through the full Two-Tier pipeline.
    Use this to simulate real-time Slack messages being processed.
    """
    orch: Optional[TwoTierOrchestrator] = app.state.orchestrator
    if not orch:
        raise HTTPException(503, "Two-Tier Orchestrator not available")
    result = await orch.process_incoming_message(
        message_id=payload.get("message_id", f"msg_{int(time.time())}"),
        channel_id=payload.get("channel_id", "hardware-team"),
        user_id=payload["user_id"],
        message_text=payload["message"],
    )
    return result

@app.get("/api/orchestrator/stats")
async def orchestrator_stats():
    """Two-Tier Architecture performance metrics."""
    orch: Optional[TwoTierOrchestrator] = app.state.orchestrator
    if not orch:
        return {"error": "Orchestrator not running"}
    return await orch.get_stats()

@app.post("/api/search")
async def search(filters: dict):
    query = filters.get("query", "").lower()
    user_id = filters.get("user_id")
    limit = filters.get("limit", 20)
    data = DECISIONS_DATA
    if user_id:
        user = _get_user(user_id)
        comps = set(user["owned_components"])
        data = [d for d in data if set(d["affected_components"]) & comps]
    if query:
        data = [d for d in data if query in d["decision_text"].lower()]
    return {
        "results": data[:limit],
        "stats": {"total_time_ms": 12.0, "final_results": len(data[:limit]), "query_type": "two-tier-hybrid"},
    }

@app.post("/api/embed")
async def run_embedding():
    return {"message": "Embedding pipeline ready — pgvector index will be built after embeddings populate"}

@app.post("/api/ingest")
async def ingest():
    return {"message": "Use POST /api/ingest/message to process individual messages through Two-Tier pipeline"}

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Knowledge Aligner with Two-Tier Architecture")
    logger.info("   Tier 1: Redis  → redis://localhost:6379")
    logger.info("   Tier 2: PostgreSQL → localhost:5432/knowledge_aligner")
    uvicorn.run("demo_server:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
