# Knowledge Aligner

An AI-powered decision tracking system for hardware engineering teams. It solves the **5-minute knowledge gap** — the window between when an engineer posts a decision and when that context reaches everyone who needs it.

## The Problem

```
Traditional: Bob gets a stale answer. The update lives in Alice's Slack thread.
Knowledge Aligner: Bob's query matches Alice's message in the live buffer.
    Response cites REQ-245, flags Bob as a missing stakeholder, creates a gap record.
```

---

## Architecture

### Two-Tier Real-Time Context

```
                  ┌─────────────────────────────────────────────┐
  Incoming        │  TIER 1 — Redis Live Buffer (0–2 hr TTL)    │
  message ──────► │  Entity extraction → context match → inject │
                  └──────────────┬──────────────────────────────┘
                                 │ decision-worthy messages
                                 ▼
                  ┌─────────────────────────────────────────────┐
                  │  TIER 2 — PostgreSQL (permanent storage)    │
                  │  decisions · gaps · gap_details · priority  │
                  └─────────────────────────────────────────────┘
```

**Tier 1 — Redis** holds the last 30 messages per channel with a 2-hour TTL. Every incoming message is entity-extracted and stored here immediately. When a query arrives, the system scores entity overlap against the buffer and injects context if the overlap meets the threshold.

**Tier 2 — PostgreSQL** stores permanent decision records, gap records with typed detail rows, and per-user priority overrides.

### Pipeline: `process_incoming_message()`

```
1. Extract entities      REQ IDs · components · topics  (~1–2 s, OpenAI)
        │
2. Decision detection    REQ present → requirement_change
        │                multiple components + keyword → technical_decision
        ├─── yes ──► INSERT into decisions (RETURNING id) → store id in Redis message
        │
3. Redis store           add to channel buffer (2 hr TTL)
        │
4. Context injection     score overlap with buffer entities
        │                threshold: medium (score ≥ 1.0)
        │
        ├─── inject ──► find matching messages
        │               create gap if user not in original discussion
        │               write gap_details (context · stakeholder · relationship)
        │               generate LLM response with injected context
        │
        └─── skip ──►  return without response (fallback to direct OpenAI call)
```

### Gap Detection and Detail Schema

When context injection fires and the querying user was not in the original discussion, a gap is created with three typed detail rows:

| `detail_type`    | `detail` (JSONB)                                                                 |
|------------------|----------------------------------------------------------------------------------|
| `context`        | `{ overlapping_components, overlapping_reqs, matching_message_count, source }`  |
| `stakeholder`    | `{ user_id, role: "notified" }`                                                  |
| `relationship`   | `{ target_gap_id, relationship_type: "related_to" }`                            |

Relationship rows are auto-populated by querying other gaps that share the same overlapping components, linking related incidents without manual input.

---

## Database Schema

```
user_profiles          decisions              gaps
─────────────          ─────────────────      ──────────────────
user_id   PK           decision_id  SERIAL PK  gap_id        PK
user_name              thread_id               type
role                   author_user_id  FK      severity
owned_components[]     author_name             description
email                  author_role             assignee_id   FK → user_profiles
                       decision_type           decision_id   FK → decisions
                       decision_text           recommendation
                       affected_components[]   created_at
                       referenced_reqs[]
                       embedding  vector(768)       gap_details
                       embedding_status          ───────────────────
                                                 detail_id    SERIAL PK
decision_details                                 gap_id       FK → gaps
─────────────────                                detail_type  (context|stakeholder|relationship|recommendation)
detail_id   SERIAL PK                            detail       JSONB
decision_id FK                                   created_at
detail_name
detail_value JSONB        gap_priority
                          ─────────────────
decision_relationships    gap_id   FK → gaps  ┐ PK
───────────────────────   user_id  FK → users ┘
relationship_id  PK       priority
source_decision_id FK     updated_at
target_decision_id FK
relationship_type
confidence
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | FastAPI (Python), uvicorn with `--reload` |
| AI — entity extraction | OpenAI `gpt-3.5-turbo` (Anthropic Claude Haiku as alternative) |
| AI — context response | OpenAI `gpt-4` (Anthropic Claude Sonnet as alternative) |
| AI — chat fallback | OpenAI `gpt-4o-mini` |
| Tier 1 | Redis 7 (Docker) |
| Tier 2 | PostgreSQL 15 + pgvector (Docker) |

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- Node.js 18+
- Python 3.10+
- OpenAI API key **or** Anthropic API key

### 1. Environment

```bash
cp .env.example .env
# Edit .env — add at least one key:
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Start infrastructure

```bash
docker-compose up -d
# Starts Redis on :6379 and PostgreSQL on :5432
# Schema and pgvector extension are applied automatically on first run
```

### 3. Start backend

```bash
# From project root
pip install fastapi uvicorn redis asyncpg openai anthropic python-dotenv
python demo_server.py
# Runs on http://localhost:8000
# On startup: seeds PostgreSQL (users, decisions, gaps) and Redis buffer
```

### 4. Start frontend

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:3000
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/users` | All demo users |
| `GET` | `/api/decisions` | Decisions from PostgreSQL (`?user_id=` to filter by component ownership) |
| `GET` | `/api/gaps` | Gaps with embedded `details[]` (`?user_id=`) |
| `GET` | `/api/gaps/{gap_id}/details` | Detail rows for one gap, relationships resolved inline |
| `POST` | `/api/gaps/priority/{gap_id}` | Update drag-and-drop priority (`?priority=&user_id=`) |
| `GET` | `/api/digest/prioritized/{user_id}` | Personalized digest with prioritized topics and gaps |
| `POST` | `/api/chat` | Two-Tier context-aware chat (`{message, user_id}`) |
| `POST` | `/api/ingest/message` | Push a raw message through the full pipeline |
| `POST` | `/api/search` | Full-text decision search |
| `GET` | `/api/orchestrator/stats` | Live pipeline metrics |
| `GET` | `/api/status` | System health and counts |

---

## Demo Accounts

| User | Role | Owned Components |
|------|------|-----------------|
| alice | Hardware Lead | motor, power_supply, mechanical |
| bob | Firmware Engineer | firmware, security, bootloader |
| charlie | Test Engineer | validation, testing, qa |
| diana | Systems Architect | architecture, integration, protocols |
| erik | PCB Designer | pcb, layout, components |
| fiona | Software Lead | software, ui, drivers |

Switch accounts using the avatar in the top-right header. Each account sees gaps, decisions, and digest personalised to its owned components.

---

## Walkthrough

### 1. Alice posts a decision

Switch to **Alice**, open **Chat**, send:

```
Updated REQ-350: motor controller voltage tolerance changed from 12V to 15V
```

The orchestrator detects `REQ-350` → marks it as a `requirement_change` → inserts a decision row in PostgreSQL → stores the message with entities in Redis.

### 2. Bob queries the same topic

Switch to **Bob**, open **Chat**, send:

```
What is the motor controller voltage spec?
```

The orchestrator extracts `motor controller` → scores overlap against the Redis buffer → finds Alice's message → injects context → generates a response that cites REQ-350 and Alice. Because Bob was not in Alice's original discussion, a gap is created automatically with three detail rows (context, stakeholder, relationship).

### 3. See the gap

Switch to **Gaps** tab. Bob's new gap appears with full detail. Drag to reorder — priority persists to PostgreSQL immediately.

### 4. Query details directly

```bash
curl http://localhost:8000/api/gaps/{gap_id}/details
```

Returns context, stakeholder, and relationship rows. Relationship rows include the resolved target gap inline.

---

## Context Matching Logic

```
Tier 1 — REQ-ID exact match       score 2.0/req    → HIGH confidence
Tier 2 — Core component match      score 1.5        → HIGH confidence
          (motor, pcb, firmware, power_supply)
Tier 3 — Any component match       score 1.0        → MEDIUM confidence
Tier 4 — Topic overlap             score 0.8/topic  → MEDIUM confidence
Tier 5 — Synonym mapping           score 0.6+       → MEDIUM confidence

Injection threshold: MEDIUM (score ≥ 1.0)
```

---

## Live Metrics

```bash
curl http://localhost:8000/api/orchestrator/stats
```

```json
{
  "messages_processed": 7,
  "context_injections": 6,
  "gaps_created": 6,
  "sql_failures": 0,
  "redis_connected": true,
  "postgres_connected": true,
  "sample_redis_stats": {
    "message_count": 22,
    "ttl_seconds": 7128
  }
}
```
