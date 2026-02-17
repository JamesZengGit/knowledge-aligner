# Knowledge Aligner: Two-Tier Real-Time Context Architecture

An AI-powered decision tracking system with **5-minute real-time context injection** that eliminates the knowledge gap between hardware engineering team decisions and stakeholder awareness.

## 🏗️ Two-Tier Architecture Overview

**TIER 1**: Redis Live Buffer (0-2 hours) - Real-time entity extraction and context injection
**TIER 2**: PostgreSQL + pgvector (2+ hours) - Historical knowledge with vector embeddings

### The 5-Minute Problem
```
T+0: Alice posts "Updated REQ-245 motor torque 2.0→2.5Nm"
T+5: Bob asks "What's current motor power requirements?"
❌ Traditional systems miss this context (batch processing every 4 hours)
✅ Our system detects entity overlap and provides intelligent context
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.10+
- Redis Server (optional - auto-fallback to mock)
- PostgreSQL (optional - auto-fallback to SQLite)
- **API Key Options** (optional - template fallback):
  - `ANTHROPIC_API_KEY` (preferred for hardware engineering)
  - `OPENAI_API_KEY` (alternative - uses GPT-4 + GPT-3.5-turbo)

### Setup
```bash
# Clone repository
git clone https://github.com/JamesZengGit/knowledge-aligner.git
cd knowledge-aligner

# Install frontend dependencies
cd frontend && npm install

# Install backend dependencies
cd ../backend && pip install fastapi uvicorn redis asyncpg anthropic openai

# Set up environment (optional for LLM features)
cp .env.example .env
# Add your API key to .env:
# OPENAI_API_KEY=your_key_here
# OR
# ANTHROPIC_API_KEY=your_key_here

# Test Two-Tier Architecture
python two_tier_demo.py

# Test OpenAI-Powered Demo (requires OPENAI_API_KEY in .env)
python backend/openai_demo.py
```

### Run Application
```bash
# Start backend (terminal 1)
cd backend && python simple_server.py

# Start frontend (terminal 2)
cd frontend && npm run dev

# Test architecture demo (terminal 3)
cd backend && python two_tier_demo.py
```

### Access
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Demo: `python two_tier_demo.py` (works with/without external dependencies)

## Features

### Decision Tracking
- Indexed decisions with before/after comparisons
- Complete impact analysis showing affected components and stakeholders
- Full traceability with citations back to original discussions

### Gap Detection
- Missing stakeholder alerts when key people aren't included in decisions
- Role-based personalized notifications with meeting host contact info
- Entity relationship tracking for proper accountability

### Role-Based Personalization
- Account switching between different engineering roles
- Component-specific gaps and priorities for each team member
- Personalized chat interface with AI-powered insights

### Smart Prioritization
- Drag-and-drop gap priority management
- Dynamic priority calculation based on component overlap
- Chat integration that recognizes reordered priorities

## Technology Stack

### Frontend
- Next.js 14 with TypeScript
- Tailwind CSS for styling
- React components for UI

### Backend
- FastAPI with Python
- OpenAI GPT-4o-mini for chat responses
- In-memory data for demo purposes

### Key Capabilities
- Real-time account switching
- Dynamic gap priority management
- Entity-linked notifications
- Chat persistence across tab navigation

## Demo Accounts

The application includes three demo accounts showing different engineering perspectives:

### Alice Chen (Mechanical Lead)
- **Components**: Motor-XYZ, Bracket-Assembly
- **Gaps**: Missing from motor torque requirement decisions
- **Priorities**: Hardware design and mechanical integration focus

### Bob Wilson (Firmware Engineer)
- **Components**: ESP32-Firmware, Bootloader
- **Gaps**: Missing from security and motor control meetings
- **Priorities**: Firmware updates and embedded system coordination

### Dave Johnson (Hardware Lead)
- **Components**: PCB-Rev3, Power-Supply-v2
- **Gaps**: Missing from power requirement discussions
- **Priorities**: Power systems and PCB design decisions

### Role Switching
Click the user avatar in the header to switch between accounts and see how the system adapts to different engineering roles with personalized gaps, priorities, and notifications.

## Demo Scenarios

### Motor Torque Requirement Change
- Requirement change from 15nm to 22nm affects multiple components
- Gap detection identifies missing firmware engineer in decision
- Cross-team coordination needed for Motor-XYZ, ESP32-Firmware, and power systems

### Security Update Implementation
- Bootloader security requirements affect firmware components
- Missing stakeholder alerts notify affected team members
- Meeting host contact information provided for proper inclusion

### Power System Design Review
- PCB and power supply changes require hardware lead input
- Entity linking tracks relationships between components and owners
- Personalized notifications ensure proper engineering review

## 🧠 Two-Tier Orchestrator Logic

The orchestrator is the **central nervous system** of the Two-Tier Architecture, coordinating between Redis live buffer, PostgreSQL persistent storage, and LLM-powered context injection.

### Core Workflow: `process_incoming_message()`

```
🔄 REAL-TIME CONTEXT INJECTION WORKFLOW
T+0: Engineer A Decision → T+5: Engineer B Query
Alice: "Updated REQ-245 motor torque 2.0→2.5Nm" → Bob: "What's current motor power requirements?"
           ↓                                              ↓
    Entity Extraction (~200ms)                    Entity Extraction (~200ms)
           ↓                                              ↓
    Entities: REQ-245, motor                       Entities: motor, power_supply
    Decision: Created                              Context: HIGH overlap (1.5)
           ↓                                              ↓
    TIER 1: Redis Store (2hr TTL) ←────────────→ Context Injection Algorithm
           ↓                                              ↓
    TIER 2: SQL Store (Permanent)                 LLM Response + Gap Alert
```

### 1. **Decision Detection Logic**

```python
def _is_decision_worthy(self, entities, message_text) -> bool:
    # HIGH PRIORITY: REQ mentions are strong indicators
    if entities.reqs:
        return True  # "Updated REQ-245 motor torque..." → DECISION

    # MEDIUM PRIORITY: Multiple components + decision keywords
    decision_keywords = ['decision', 'approved', 'updated', 'changed', 'spec']
    if len(entities.components) >= 2 and has_decision_keyword:
        return True  # "Approved new PCB thermal design" → DECISION

    # LOW PRIORITY: High confidence extraction + engineering topics
    if entities.confidence > 0.8 and len(entities.topics) >= 2:
        return True

    return False  # "How's everyone doing?" → NOT A DECISION
```

### 2. **Context Injection Intelligence**

```python
async def _check_context_injection(self, channel_id, b_entities, user_id):
    # Get last 30 messages from Redis (2-hour window)
    context_messages = await self.redis_buffer.get_recent_context(
        channel_id, max_messages=30, max_age_minutes=120
    )

    # Calculate overlap between B's entities and buffer entities
    should_inject, confidence, score = self.context_matcher.should_inject_context(
        b_entities, buffer_entities, confidence_threshold='medium'
    )

    if should_inject:
        # Create gap if B wasn't mentioned in original discussion
        gap_id = await self._create_gap_if_needed(b_entities, matching_contexts, user_id)

        # Generate intelligent response using Claude Sonnet
        response = await self.context_responder.generate_response(...)
```

### 3. **Gap Detection Algorithm**

Detects **missing stakeholders** when context overlap occurs:

```python
async def _create_gap_if_needed(self, b_entities, matching_contexts, user_id):
    # Check if user was mentioned in ANY matching context message
    user_was_mentioned = any(
        f"@{user_id}" in ctx['message'].entities.get('users_mentioned', [])
        for ctx in matching_contexts
    )

    if user_was_mentioned:
        return None  # User was already included - no gap needed

    # Gap detected: B should have been included in original discussion
    # Example: Alice discusses REQ-245 motor changes, Bob asks about motors later
    # → Gap: Bob should have been @mentioned in Alice's decision
```

### 4. **Performance Metrics**

```
⚡ REAL-TIME PERFORMANCE TARGETS
Entity Extraction:        < 200ms  (Claude Haiku + regex fallback)
Redis Context Lookup:     ~   5ms  (ZRANGE with timestamp scoring)
Overlap Scoring:          ~   2ms  (Set intersection + pattern matching)
LLM Response Generation:   < 3sec  (Claude Sonnet with structured prompt)
───────────────────────────────────
TOTAL RESPONSE TIME:       < 3.5s  ✅ (Target: 5s for real-time UX)
```

### 5. **Dead Zone Elimination Strategy**

```
TIMELINE: Eliminating the 4-Hour Dead Zone
Hour 0    1    2    3    4    5    6    7    8
├─────┼────┼────┼────┼────┼────┼────┼────┼────┤
│ TIER 1 Redis Buffer (2hr TTL)      │    │    │
│ ████████████████████████████████    │    │    │
│     │    │ TIER 2 Batch Process    │    │    │
│     │    │ ░░░░░░░░░░░░░░░░░░░░░░░░ │    │    │

✅ Redis TTL: 2 hours
✅ Batch cadence: Every 1.5 hours
✅ Overlap window: 30 minutes safety margin
```

The orchestrator successfully bridges the **5-minute real-time window** problem by coordinating fast Redis lookups with permanent SQL storage, while providing intelligent context injection and gap detection for engineering teams.