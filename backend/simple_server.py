"""Simple backend server for testing without full dependencies."""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import openai
# LangChain imports removed - using embedded logic approach

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Removed LangChain models - using embedded logic approach

app = FastAPI(title="Hardware Digest API - Demo Mode")

# Pydantic models for chat
class ChatMessage(BaseModel):
    message: str
    user_id: str

class ChatResponse(BaseModel):
    response: str
    context_decisions: list = []
    priority_gaps: list = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global gap state (in production this would be in database)
current_gap_priorities = {}

# Entity relationship system for linking persons, events, and decisions
class EntitySystem:
    def __init__(self):
        self.entities = {
            "persons": {},
            "events": {},
            "components": {},
            "requirements": {}
        }
        self.relationships = []

    def add_person(self, user_id, name, role, components, contact_info=None):
        self.entities["persons"][user_id] = {
            "id": user_id,
            "name": name,
            "role": role,
            "owned_components": components,
            "contact_info": contact_info or {},
            "type": "person"
        }

    def add_event(self, event_id, event_type, host_id, participants, components_affected, timestamp):
        self.entities["events"][event_id] = {
            "id": event_id,
            "type": "event",
            "event_type": event_type,
            "host_id": host_id,
            "participants": participants,
            "components_affected": components_affected,
            "timestamp": timestamp
        }

    def get_missing_stakeholders(self, event_id):
        """Find who should have been invited but wasn't"""
        event = self.entities["events"].get(event_id)
        if not event:
            return []

        missing = []
        for component in event["components_affected"]:
            # Find component owners not in participants
            owners = [p for p in self.entities["persons"].values()
                     if component in p["owned_components"] and p["id"] not in event["participants"]]
            missing.extend(owners)

        return missing

    def get_notification_targets(self, missing_person_id, event_id):
        """Get who should be notified when someone is missing"""
        event = self.entities["events"].get(event_id)
        if not event:
            return []

        return {
            "missing_person": self.entities["persons"].get(missing_person_id),
            "meeting_host": self.entities["persons"].get(event["host_id"]),
            "event": event
        }

# Mock data for demo
mock_users = [
    {
        "user_id": "alice",
        "user_name": "Alice Chen",
        "role": "Mechanical Lead",
        "owned_components": ["Motor-XYZ", "Bracket-Assembly"],
        "email": "alice@company.com"
    },
    {
        "user_id": "bob",
        "user_name": "Bob Wilson",
        "role": "Firmware Engineer",
        "owned_components": ["ESP32-Firmware", "Bootloader"],
        "email": "bob@company.com"
    },
    {
        "user_id": "dave",
        "user_name": "Dave Johnson",
        "role": "Hardware Lead",
        "owned_components": ["PCB-Rev3", "Power-Supply-v2"],
        "email": "dave@company.com"
    }
]

mock_decisions = [
    {
        "decision_id": 1,
        "thread_id": "thread_001",
        "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
        "author_user_id": "eve",
        "author_name": "Eve Martinez",
        "author_role": "PM",
        "decision_type": "requirement_change",
        "decision_text": "REQ-245: Motor torque requirement changing from 15nm to 22nm based on customer load analysis. This affects Motor-XYZ and potentially Bracket-Assembly.",
        "affected_components": ["Motor-XYZ", "Bracket-Assembly"],
        "referenced_reqs": ["REQ-245"],
        "similarity_score": 0.95,
        "before_after": {
            "before": "15nm",
            "after": "22nm"
        },
        "gaps_detected": [
            {
                "type": "missing_stakeholder",
                "severity": "critical",
                "description": "Bob Wilson (Firmware) should be included - motor control algorithms may need updates",
                "decision_id": 1,
                "recommendation": "Include Bob in motor torque discussions",
                "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
                "priority": 9
            }
        ]
    },
    {
        "decision_id": 2,
        "thread_id": "thread_002",
        "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
        "author_user_id": "alice",
        "author_name": "Alice Chen",
        "author_role": "Mechanical Lead",
        "decision_type": "design_decision",
        "decision_text": "Motor-XYZ redesign required for 22nm torque. Estimated 3-week timeline. Need to coordinate with supply chain for new motor specifications.",
        "affected_components": ["Motor-XYZ"],
        "referenced_reqs": ["REQ-245"],
        "similarity_score": 0.87,
        "before_after": {
            "before": "3-week estimate",
            "after": "confirmed 3-week timeline"
        }
    },
    {
        "decision_id": 3,
        "thread_id": "thread_003",
        "timestamp": (datetime.now() - timedelta(hours=4)).isoformat(),
        "author_user_id": "dave",
        "author_name": "Dave Johnson",
        "author_role": "Hardware Lead",
        "decision_type": "design_decision",
        "decision_text": "PCB-Rev3 power supply modification needed for increased current draw from new motor specs. Changing from 5A to 8A capacity.",
        "affected_components": ["PCB-Rev3", "Power-Supply-v2"],
        "referenced_reqs": ["REQ-245"],
        "similarity_score": 0.78,
        "before_after": {
            "before": "5A capacity",
            "after": "8A capacity"
        }
    },
    {
        "decision_id": 4,
        "thread_id": "thread_004",
        "timestamp": (datetime.now() - timedelta(hours=6)).isoformat(),
        "author_user_id": "bob",
        "author_name": "Bob Wilson",
        "author_role": "Firmware Engineer",
        "decision_type": "design_decision",
        "decision_text": "ESP32-Firmware motor control algorithm update to handle increased torque requirements. PID controller gains need adjustment.",
        "affected_components": ["ESP32-Firmware", "Motor-XYZ"],
        "referenced_reqs": ["REQ-245"],
        "similarity_score": 0.84,
        "before_after": {
            "before": "PID gains: Kp=1.2, Ki=0.5",
            "after": "PID gains: Kp=1.8, Ki=0.7"
        }
    },
    {
        "decision_id": 5,
        "thread_id": "thread_005",
        "timestamp": (datetime.now() - timedelta(hours=3)).isoformat(),
        "author_user_id": "alice",
        "author_name": "Alice Chen",
        "author_role": "Mechanical Lead",
        "decision_type": "requirement_change",
        "decision_text": "Power requirements for Motor-XYZ increased due to 22nm torque. PCB-Rev3 power traces may need revision for higher current draw.",
        "affected_components": ["PCB-Rev3", "Power-Supply-v2", "Motor-XYZ"],
        "referenced_reqs": ["REQ-245"],
        "similarity_score": 0.91,
        "before_after": {
            "before": "12V 2A power supply",
            "after": "12V 3.2A power supply"
        }
    },
    {
        "decision_id": 6,
        "thread_id": "thread_006",
        "timestamp": (datetime.now() - timedelta(hours=5)).isoformat(),
        "author_user_id": "eve",
        "author_name": "Eve Martinez",
        "author_role": "PM",
        "decision_type": "technical_decision",
        "decision_text": "Bootloader security update required for new ESP32 firmware. Must implement secure boot to prevent unauthorized firmware updates.",
        "affected_components": ["Bootloader", "ESP32-Firmware"],
        "referenced_reqs": ["REQ-301"],
        "similarity_score": 0.89,
        "before_after": {
            "before": "Basic bootloader",
            "after": "Secure boot enabled"
        }
    }
]

# Initialize entity system after mock data is defined
entity_system = EntitySystem()

# Add all persons to entity system
for user in mock_users:
    entity_system.add_person(
        user["user_id"],
        user["user_name"],
        user["role"],
        user["owned_components"],
        {"email": user["email"]}
    )

# Add decision events with participants and affected components
decision_events = [
    ("event_001", "decision_meeting", "eve", ["eve"], ["Motor-XYZ", "Bracket-Assembly"]),  # Bob missing
    ("event_002", "design_review", "alice", ["alice"], ["Motor-XYZ"]),  # Bob missing
    ("event_004", "firmware_update", "bob", ["bob"], ["ESP32-Firmware", "Motor-XYZ"]),  # Alice missing
    ("event_005", "power_review", "alice", ["alice"], ["PCB-Rev3", "Power-Supply-v2", "Motor-XYZ"]),  # Dave missing
    ("event_006", "security_meeting", "eve", ["eve"], ["Bootloader", "ESP32-Firmware"]),  # Bob missing
]

for event_id, event_type, host_id, participants, components in decision_events:
    entity_system.add_event(event_id, event_type, host_id, participants, components, datetime.now().isoformat())

@app.get("/")
async def root():
    return {"message": "Hardware Digest API - Demo Mode", "status": "operational"}

@app.get("/api/status")
async def get_status():
    return {
        "users": len(mock_users),
        "messages": 164,
        "decisions": len(mock_decisions),
        "relationships": 12,
        "embeddings": {"embedded": 35, "pending": 10, "failed": 0},
        "ai_enabled": False
    }

@app.get("/api/users")
async def get_users():
    return mock_users

@app.get("/api/decisions")
async def get_decisions():
    return mock_decisions

@app.get("/api/digest/{user_id}")
async def get_digest(user_id: str):
    return {
        "user_id": user_id,
        "date": datetime.now().isoformat(),
        "summary": "3 critical decisions affect your components this week. REQ-245 motor torque change requires Motor-XYZ redesign. New supplier qualification needed for 22nm motor.",
        "themes": ["Requirement Changes", "Mechanical Design Updates", "Supply Chain Impact"],
        "entries": [
            {
                "decision_id": "REQ-001",
                "title": "REQ-245: Motor Torque Requirement Change",
                "summary": "Motor torque requirement changing from 15nm to 22nm based on customer load analysis.",
                "impact_summary": "Motor-XYZ requires complete redesign, 3-week delay expected",
                "before_after": {"before": "15nm", "after": "22nm"},
                "affected_components": ["Motor-XYZ", "Bracket-Assembly"],
                "citations": ["#req-reviews thread_1234 2026-02-01T14:30"],
                "timestamp": (datetime.now() - timedelta(hours=2)).isoformat()
            }
        ],
        "gaps_detected": [
            "Decision REQ-001 affects your Motor-XYZ but Bob (firmware) wasn't included - motor control algorithms may need updates"
        ],
        "action_items": [
            "Initiate Motor-XYZ redesign for 22nm torque requirement",
            "Coordinate with supply chain for new motor supplier qualification"
        ]
    }

@app.get("/api/digest/prioritized/{user_id}")
async def get_prioritized_digest(user_id: str):
    """Generate prioritized digest using LangChain structured output."""
    try:
        # Get user context
        user = next((u for u in mock_users if u["user_id"] == user_id), None)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get user's relevant decisions
        user_decisions = [
            d for d in mock_decisions
            if any(comp in user["owned_components"] for comp in d["affected_components"])
        ]

        # Get gaps for user
        user_gaps = [
            gap for gap in [
                {
                    "gap_id": d["decision_id"],
                    "title": f"Missing in Decision {d['decision_id']}",
                    "urgency": "critical" if d["decision_id"] == 1 else "medium",
                    "user_impact": f"Your {', '.join([c for c in d['affected_components'] if c in user['owned_components']])} affected",
                    "action_needed": "Join decision discussion"
                }
                for d in mock_decisions
                if any(comp in user["owned_components"] for comp in d["affected_components"])
                and d["author_user_id"] != user_id
            ]
        ][:2]  # Limit to 2 gaps

        # Use embedded priority logic instead of LLM for reliability
        # Prioritize gaps by severity and user component relevance
        prioritized_gaps = []
        for gap in user_gaps:
            priority_score = 5  # base priority
            if gap["urgency"] == "critical":
                priority_score = 9
            elif gap["urgency"] == "high":
                priority_score = 7
            elif gap["urgency"] == "medium":
                priority_score = 5

            # Boost priority if affects user's primary components
            if any(comp in gap["user_impact"] for comp in user["owned_components"]):
                priority_score = min(10, priority_score + 2)

            gap["priority"] = priority_score
            prioritized_gaps.append(gap)

        # Sort by priority and limit to top 2
        prioritized_gaps = sorted(prioritized_gaps, key=lambda x: x["priority"], reverse=True)[:2]

        # Prioritize topics based on decision frequency and user component involvement
        component_impact = {}
        for d in user_decisions:
            for comp in d["affected_components"]:
                if comp in user["owned_components"]:
                    component_impact[comp] = component_impact.get(comp, 0) + 3  # High weight for owned
                else:
                    component_impact[comp] = component_impact.get(comp, 0) + 1

        # Add REQ-245 and related topics with calculated priorities
        prioritized_topics = []
        for comp, count in sorted(component_impact.items(), key=lambda x: x[1], reverse=True)[:3]:
            priority = min(10, count * 2)  # Scale to 1-10
            impact_level = "high" if priority >= 8 else "medium" if priority >= 5 else "low"
            reason = f"Affects your component with {count} recent decision{'s' if count > 1 else ''}"
            if comp in user["owned_components"]:
                reason = f"Critical component under your ownership with {count} active decision{'s' if count > 1 else ''}"

            prioritized_topics.append({
                "name": comp,
                "priority": priority,
                "reason": reason,
                "impact_level": impact_level
            })

        # Generate trend analysis based on decision patterns
        recent_decisions_count = len(user_decisions)
        if recent_decisions_count >= 3:
            trend_analysis = f"Decision velocity increased 40% with {recent_decisions_count} decisions affecting your components. REQ-245 driving cascade of changes across mechanical, firmware, and hardware domains."
        elif recent_decisions_count >= 1:
            trend_analysis = f"Moderate activity with {recent_decisions_count} decision{'s' if recent_decisions_count > 1 else ''} affecting your area. Focus on coordination to prevent gaps."
        else:
            trend_analysis = "Low decision activity in your domain. Good time to catch up on pending items."

        # Generate key insight based on highest priority gaps and topics
        highest_priority_topic = prioritized_topics[0]["name"] if prioritized_topics else "your components"
        highest_priority_gap = prioritized_gaps[0] if prioritized_gaps else None

        if highest_priority_gap and highest_priority_gap["priority"] >= 8:
            key_insight = f"The {highest_priority_topic} changes are creating coordination challenges - {highest_priority_gap['action_needed'].lower()} to prevent project delays."
        else:
            key_insight = f"Focus on {highest_priority_topic} alignment with cross-functional teams to maintain project momentum."

        return {
            "prioritized_topics": prioritized_topics,
            "prioritized_gaps": prioritized_gaps,
            "trend_analysis": trend_analysis,
            "key_insight": key_insight
        }

    except Exception as e:
        # Fallback structured response
        return {
            "prioritized_topics": [
                {
                    "name": "Motor-XYZ",
                    "priority": 10,
                    "reason": "Critical torque requirement change affects your primary component",
                    "impact_level": "high"
                },
                {
                    "name": "REQ-245 Compliance",
                    "priority": 9,
                    "reason": "New requirement drives multiple design changes",
                    "impact_level": "high"
                },
                {
                    "name": "Supply Chain Coordination",
                    "priority": 7,
                    "reason": "New motor specs require supplier qualification",
                    "impact_level": "medium"
                }
            ],
            "prioritized_gaps": [
                {
                    "gap_id": 1,
                    "title": "Missing from firmware discussions",
                    "urgency": "critical",
                    "user_impact": "Motor control algorithms may need updates for your Motor-XYZ",
                    "action_needed": "Connect with Bob Wilson about firmware implications"
                },
                {
                    "gap_id": 4,
                    "title": "Timeline coordination gap",
                    "urgency": "high",
                    "user_impact": "Your 3-week redesign timeline may conflict with other components",
                    "action_needed": "Align timeline estimates with Dave (hardware) and supply chain"
                }
            ],
            "trend_analysis": "Decision velocity increased 40% compared to yesterday, with REQ-245 driving cascade of component changes across mechanical, firmware, and hardware domains.",
            "key_insight": "The REQ-245 torque change is creating a coordination challenge - while you're planning Motor-XYZ redesign, ensure firmware control algorithms and power supply capacity are addressed in parallel to avoid integration delays."
        }

@app.get("/api/gaps")
async def get_gaps(user_id: str = "alice"):
    # Return role-specific gaps with entity linking
    user = next((u for u in mock_users if u["user_id"] == user_id), mock_users[0])

    user_specific_gaps = []

    # Entity mapping for proper personalization
    decision_hosts = {
        1: {"name": "Eve Martinez", "role": "PM"},
        2: {"name": "Alice Chen", "role": "Mechanical Lead"},
        4: {"name": "Bob Wilson", "role": "Firmware Engineer"},
        5: {"name": "Alice Chen", "role": "Mechanical Lead"},
        6: {"name": "Eve Martinez", "role": "PM"}
    }

    for decision in mock_decisions:
        # Only show gaps for decisions affecting user's components
        if any(comp in user["owned_components"] for comp in decision["affected_components"]):
            affected_user_components = [c for c in decision["affected_components"] if c in user["owned_components"]]

            # Calculate priority dynamically
            component_overlap = len(affected_user_components)
            is_author = decision["author_user_id"] == user_id

            if decision["decision_id"] in current_gap_priorities:
                priority = current_gap_priorities[decision["decision_id"]]
            else:
                if is_author:
                    priority = 3 + component_overlap
                else:
                    priority = 1 if component_overlap >= 2 else 2 if component_overlap == 1 else 5

            meeting_host = decision_hosts.get(decision["decision_id"], {"name": "Unknown", "role": "Unknown"})

            if decision["author_user_id"] != user_id:
                # User should have been included but wasn't - personalized for THEM
                gap = {
                    "type": "missing_stakeholder",
                    "severity": "critical" if priority <= 2 else "warning",
                    "description": f"Decision REQ-{decision['decision_id']:03d} affects your {', '.join(affected_user_components)} but you weren't included",
                    "decision_id": decision["decision_id"],
                    "recommendation": f"Contact meeting host {meeting_host['name']} ({meeting_host['role']}) to request inclusion in REQ-{decision['decision_id']:03d}",
                    "timestamp": decision["timestamp"],
                    "priority": priority,
                    "entities": {
                        "missing_person": {"id": user_id, "name": user["user_name"], "role": user["role"]},
                        "meeting_host": meeting_host,
                        "affected_components": affected_user_components
                    }
                }
                user_specific_gaps.append(gap)

    return user_specific_gaps

@app.post("/api/chat")
async def chat(message: ChatMessage):
    try:
        # Get user context
        user = next((u for u in mock_users if u["user_id"] == message.user_id), None)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get user's relevant decisions (affecting their components)
        user_decisions = [
            d for d in mock_decisions
            if any(comp in user["owned_components"] for comp in d["affected_components"])
        ]

        # Get priority gaps for this user using current gap priorities
        priority_gaps = []
        for d in mock_decisions:
            if any(comp in user["owned_components"] for comp in d["affected_components"]):
                # Use current gap priority if available, otherwise calculate dynamic default
                if d["decision_id"] in current_gap_priorities:
                    priority = current_gap_priorities[d["decision_id"]]
                else:
                    # Calculate priority based on component overlap and authorship
                    component_overlap = len([c for c in d["affected_components"] if c in user["owned_components"]])
                    is_author = d["author_user_id"] == user["user_id"]

                    if is_author:
                        # If user authored the decision, coordination priority
                        priority = 3 + component_overlap  # 4-6 range typically
                    else:
                        # If user should have been included, missing stakeholder priority
                        if component_overlap >= 2:  # Multiple components affected
                            priority = 1  # Highest priority
                        elif component_overlap == 1:
                            priority = 2  # High priority
                        else:
                            priority = 5  # Lower priority

                # Different gap descriptions based on whether user authored the decision
                if d["author_user_id"] == message.user_id:
                    description = f"Decision {d['decision_id']} requires coordination with other stakeholders affecting your {', '.join([c for c in d['affected_components'] if c in user['owned_components']])}"
                    gap_type = "coordination_needed"
                else:
                    description = f"You should be included in decision {d['decision_id']} affecting your {', '.join([c for c in d['affected_components'] if c in user['owned_components']])}"
                    gap_type = "missing_stakeholder"

                gap = {
                    "type": gap_type,
                    "severity": "critical" if priority >= 8 else "warning",
                    "description": description,
                    "decision_id": d["decision_id"],
                    "priority": priority
                }
                priority_gaps.append(gap)

        # Sort by priority (lowest number = highest priority)
        priority_gaps = sorted(priority_gaps, key=lambda x: x["priority"])

        # Create context for OpenAI - let the LLM handle prioritization naturally
        context = f"""
You are a hardware engineering AI assistant. User: {user['user_name']} ({user['role']})
Components owned: {', '.join(user['owned_components'])}

Recent decisions affecting user:
{json.dumps([{'id': d['decision_id'], 'text': d['decision_text'], 'components': d['affected_components'], 'timestamp': d['timestamp']} for d in user_decisions], indent=2)}

Detected gaps that need attention (sorted by priority):
{json.dumps([{'description': g['description'], 'decision_id': g['decision_id'], 'priority': g['priority'], 'severity': g['severity']} for g in priority_gaps], indent=2)}

User question: {message.message}

Instructions:
- Pay attention to gap priorities - the LOWEST priority number indicates the most urgent gap (Priority 1 = highest priority)
- When asked about top priority, refer to the gap with the lowest priority number (closest to 1)
- Always reference the correct REQ number from the decision_id field (e.g. REQ-001 for decision_id 1, REQ-004 for decision_id 4)
- Be conversational and actionable, not robotic
- Focus on the user's specific components and responsibilities
- Provide specific next steps when possible
- Keep responses comprehensive but under 300 words
- Use ONLY plain text - no formatting, no markdown, no symbols
- Write simple sentences that read clearly as plain text messages
- Use line breaks for organization but no special characters or markup
"""

        # Call OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful hardware engineering assistant that understands priority levels and provides actionable advice."},
                {"role": "user", "content": context}
            ],
            max_tokens=400,
            temperature=0.7
        )

        return ChatResponse(
            response=response.choices[0].message.content,
            context_decisions=user_decisions[:3],  # Limit to top 3 relevant decisions
            priority_gaps=priority_gaps[:2]  # Limit to top 2 gaps
        )

    except Exception as e:
        # Fallback response if OpenAI fails
        return ChatResponse(
            response=f"Here's what I found for your components ({', '.join(user['owned_components']) if user else 'unknown'}): REQ-245 is affecting Motor-XYZ with torque changes from 15nm to 22nm. You have 1 critical gap where you should be included in firmware discussions.",
            context_decisions=user_decisions[:3] if 'user_decisions' in locals() else [],
            priority_gaps=priority_gaps[:2] if 'priority_gaps' in locals() else []
        )

@app.post("/api/gaps/priority")
async def update_gap_priority():
    """Update gap priorities based on frontend changes."""
    global current_gap_priorities
    try:
        # For demo, we'll simulate getting priority updates from frontend
        # In a real app, this would receive the updated priorities via request body

        # This endpoint will be called by the frontend when gaps are reordered
        return {"message": "Gap priorities updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/gaps/priority/{gap_id}")
async def update_single_gap_priority(gap_id: int, priority: int = Query(...)):
    """Update priority for a single gap."""
    global current_gap_priorities
    current_gap_priorities[gap_id] = priority
    print(f"Updated gap {gap_id} to priority {priority}. Current priorities: {current_gap_priorities}")
    return {"message": f"Gap {gap_id} priority updated to {priority}"}

@app.post("/api/setup")
async def setup():
    return {"message": "Demo setup complete", "users": 10, "messages": 164}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print("🚀 Starting Hardware Digest API in Demo Mode...")
    print(f"📊 Backend will be available at: http://localhost:{port}")
    print("🎨 Frontend should be running at: http://localhost:3000")
    uvicorn.run(app, host="0.0.0.0", port=port)