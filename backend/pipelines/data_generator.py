"""Generate realistic simulated Slack dataset for hardware teams."""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict
from .models import UserProfile, SlackMessage

class HardwareTeamDataGenerator:
    def __init__(self):
        self.users = [
            UserProfile(user_id="alice", user_name="Alice Chen", role="Mechanical Lead",
                       owned_components=["Motor-XYZ", "Bracket-Assembly"], email="alice@company.com"),
            UserProfile(user_id="bob", user_name="Bob Wilson", role="Firmware Engineer",
                       owned_components=["ESP32-Firmware", "Bootloader"], email="bob@company.com"),
            UserProfile(user_id="carol", user_name="Carol Davis", role="Supply Chain",
                       owned_components=["BOM", "Vendor-Selection"], email="carol@company.com"),
            UserProfile(user_id="dave", user_name="Dave Johnson", role="Hardware Lead",
                       owned_components=["PCB-Rev3", "Power-Supply-v2"], email="dave@company.com"),
            UserProfile(user_id="eve", user_name="Eve Martinez", role="PM",
                       owned_components=["Requirements", "Schedule"], email="eve@company.com"),
            UserProfile(user_id="frank", user_name="Frank Thompson", role="Test Engineer",
                       owned_components=["Test-Fixtures", "QA-Process"], email="frank@company.com"),
            UserProfile(user_id="grace", user_name="Grace Lee", role="Mechanical",
                       owned_components=["Enclosure", "Thermal-Design"], email="grace@company.com"),
            UserProfile(user_id="henry", user_name="Henry Brown", role="Firmware",
                       owned_components=["Driver-Code", "I2C-Interface"], email="henry@company.com"),
            UserProfile(user_id="iris", user_name="Iris Kim", role="Electrical",
                       owned_components=["Schematic", "Layout"], email="iris@company.com"),
            UserProfile(user_id="jack", user_name="Jack Singh", role="Manufacturing",
                       owned_components=["Assembly-Process", "DFM"], email="jack@company.com"),
        ]

        self.channels = ["#mechanical", "#firmware", "#supply-chain", "#general", "#req-reviews"]

        self.requirement_patterns = [
            "REQ-245: Motor torque increases from 15nm to 22nm due to load analysis",
            "REQ-118: Power consumption budget reduced from 5W to 3.5W",
            "REQ-332: Operating temperature range extended from -10°C to -20°C",
            "REQ-089: Communication protocol changed from UART to I2C",
            "REQ-156: Enclosure material switched from aluminum to polymer",
            "REQ-201: Battery life requirement increased from 8hrs to 12hrs",
        ]

        self.decision_templates = [
            {
                "type": "requirement_change",
                "templates": [
                    "After reviewing the thermal analysis, {req} - this affects {component}",
                    "Customer feedback requires {req}, updating {component} accordingly",
                    "Safety certification needs {req}, {component} design must be revised",
                ]
            },
            {
                "type": "design_decision",
                "templates": [
                    "We're going with {supplier} for {component} based on cost and lead time",
                    "Changed {component} from {old_value} to {new_value} for better performance",
                    "Approved {component} design after thermal simulation passed",
                ]
            },
            {
                "type": "approval",
                "templates": [
                    "✅ Approved {component} for production after DFM review",
                    "Sign-off complete for {component}, proceeding to manufacturing",
                    "Green light on {component} - all stakeholders aligned",
                ]
            }
        ]

    def generate_realistic_conversations(self) -> List[SlackMessage]:
        """Generate 30 days of realistic hardware team conversations."""
        messages = []
        base_time = datetime.now() - timedelta(days=30)

        # Generate scenarios that reflect real hardware team challenges
        scenarios = [
            self._generate_requirement_change_scenario(base_time),
            self._generate_supplier_crisis_scenario(base_time + timedelta(days=5)),
            self._generate_design_review_scenario(base_time + timedelta(days=10)),
            self._generate_manufacturing_issue_scenario(base_time + timedelta(days=15)),
            self._generate_scope_creep_scenario(base_time + timedelta(days=20)),
            self._generate_thermal_analysis_scenario(base_time + timedelta(days=25)),
        ]

        for scenario in scenarios:
            messages.extend(scenario)

        # Add daily standup-style updates
        for day in range(30):
            messages.extend(self._generate_daily_updates(base_time + timedelta(days=day)))

        return sorted(messages, key=lambda x: x.timestamp)

    def _generate_requirement_change_scenario(self, start_time: datetime) -> List[SlackMessage]:
        """Generate REQ-245 style requirement change with cascading impacts."""
        thread_id = f"req_change_{int(start_time.timestamp())}"
        messages = []

        # Initial requirement change announcement
        messages.append(SlackMessage(
            message_id=f"{thread_id}_001",
            channel_id="#req-reviews",
            thread_id=thread_id,
            user_id="eve",
            message_text="REQ-245: Motor torque requirement changing from 15nm to 22nm based on customer load analysis. This is a breaking change that affects Motor-XYZ and potentially Bracket-Assembly.",
            timestamp=start_time,
            entities={"requirements": ["REQ-245"], "components": ["Motor-XYZ", "Bracket-Assembly"]}
        ))

        # Mechanical lead responds (Alice owns Motor-XYZ)
        messages.append(SlackMessage(
            message_id=f"{thread_id}_002",
            channel_id="#req-reviews",
            thread_id=thread_id,
            user_id="alice",
            message_text="This means we need to redesign Motor-XYZ completely. The current 15nm motor won't handle 22nm. Looking at 3 week delay minimum.",
            timestamp=start_time + timedelta(minutes=15),
        ))

        # Supply chain impact (Carol)
        messages.append(SlackMessage(
            message_id=f"{thread_id}_003",
            channel_id="#req-reviews",
            thread_id=thread_id,
            user_id="carol",
            message_text="22nm motor means different supplier. Our current vendor maxes out at 18nm. I'll need to requalify new parts - adds cost and time.",
            timestamp=start_time + timedelta(minutes=45),
        ))

        # Missing stakeholder scenario - Bob (firmware) not included but should be
        # This creates a gap that the system should detect

        return messages

    def _generate_supplier_crisis_scenario(self, start_time: datetime) -> List[SlackMessage]:
        """Generate supplier crisis requiring quick decisions."""
        thread_id = f"supplier_crisis_{int(start_time.timestamp())}"
        messages = []

        messages.append(SlackMessage(
            message_id=f"{thread_id}_001",
            channel_id="#supply-chain",
            thread_id=thread_id,
            user_id="carol",
            message_text="🚨 URGENT: Primary capacitor supplier just went EOL on our 470uF part. Need replacement decision TODAY for PCB-Rev3.",
            timestamp=start_time,
            entities={"components": ["PCB-Rev3"], "urgency": "high"}
        ))

        messages.append(SlackMessage(
            message_id=f"{thread_id}_002",
            channel_id="#supply-chain",
            thread_id=thread_id,
            user_id="iris",
            message_text="Can we use 2x 220uF in parallel? Same footprint, slightly higher ESR but within spec.",
            timestamp=start_time + timedelta(minutes=10),
        ))

        messages.append(SlackMessage(
            message_id=f"{thread_id}_003",
            channel_id="#supply-chain",
            thread_id=thread_id,
            user_id="dave",
            message_text="✅ Approved parallel 220uF solution. Update BOM and proceed. No layout changes needed.",
            timestamp=start_time + timedelta(minutes=30),
        ))

        return messages

    def _generate_design_review_scenario(self, start_time: datetime) -> List[SlackMessage]:
        """Generate design review with multiple stakeholder input."""
        thread_id = f"design_review_{int(start_time.timestamp())}"
        messages = []

        # Design review announcement
        messages.append(SlackMessage(
            message_id=f"{thread_id}_001",
            channel_id="#mechanical",
            thread_id=thread_id,
            user_id="alice",
            message_text="Design review for Enclosure v2.1 tomorrow 2PM. Key changes: wall thickness 2.5mm→3.0mm, added vent holes for thermal.",
            timestamp=start_time,
            entities={"components": ["Enclosure"], "changes": [{"before": "2.5mm", "after": "3.0mm"}]}
        ))

        # Thermal engineer input
        messages.append(SlackMessage(
            message_id=f"{thread_id}_002",
            channel_id="#mechanical",
            thread_id=thread_id,
            user_id="grace",
            message_text="3.0mm walls good for thermal. Vent hole placement looks optimal - 15°C reduction in thermal sim.",
            timestamp=start_time + timedelta(hours=2),
        ))

        # Manufacturing concern
        messages.append(SlackMessage(
            message_id=f"{thread_id}_003",
            channel_id="#mechanical",
            thread_id=thread_id,
            user_id="jack",
            message_text="Thicker walls mean longer cycle time in molding. ~8% cost increase. Can we optimize?",
            timestamp=start_time + timedelta(hours=4),
        ))

        return messages

    def _generate_manufacturing_issue_scenario(self, start_time: datetime) -> List[SlackMessage]:
        """Generate manufacturing issue requiring engineering input."""
        thread_id = f"mfg_issue_{int(start_time.timestamp())}"
        messages = []

        messages.append(SlackMessage(
            message_id=f"{thread_id}_001",
            channel_id="#general",
            thread_id=thread_id,
            user_id="jack",
            message_text="Assembly line reports 15% failure rate on I2C-Interface connection. Intermittent communication errors.",
            timestamp=start_time,
            entities={"components": ["I2C-Interface"], "failure_rate": "15%"}
        ))

        messages.append(SlackMessage(
            message_id=f"{thread_id}_002",
            channel_id="#general",
            thread_id=thread_id,
            user_id="henry",
            message_text="Could be pull-up resistor tolerance issue. I2C needs tight 4.7kΩ ±5%. Are we getting ±10% parts?",
            timestamp=start_time + timedelta(minutes=20),
        ))

        messages.append(SlackMessage(
            message_id=f"{thread_id}_003",
            channel_id="#general",
            thread_id=thread_id,
            user_id="carol",
            message_text="Checking BOM... yes we spec'd ±10% to save cost. Switching to ±5% adds $0.03 per unit.",
            timestamp=start_time + timedelta(minutes=35),
        ))

        return messages

    def _generate_scope_creep_scenario(self, start_time: datetime) -> List[SlackMessage]:
        """Generate scope creep scenario - requirements expanding during development."""
        thread_id = f"scope_creep_{int(start_time.timestamp())}"
        messages = []

        messages.append(SlackMessage(
            message_id=f"{thread_id}_001",
            channel_id="#firmware",
            thread_id=thread_id,
            user_id="eve",
            message_text="Customer now wants WiFi connectivity added to ESP32-Firmware. 'Nice to have' became 'must have'.",
            timestamp=start_time,
            entities={"components": ["ESP32-Firmware"], "scope_change": True}
        ))

        messages.append(SlackMessage(
            message_id=f"{thread_id}_002",
            channel_id="#firmware",
            thread_id=thread_id,
            user_id="bob",
            message_text="WiFi adds 2 weeks dev time + more flash memory. Current ESP32 won't fit the code.",
            timestamp=start_time + timedelta(minutes=25),
        ))

        # Conflicting decision - Dave says proceed, but Bob flagged concerns
        messages.append(SlackMessage(
            message_id=f"{thread_id}_003",
            channel_id="#firmware",
            thread_id=thread_id,
            user_id="dave",
            message_text="Customer is paying extra. Add WiFi, we'll figure out the memory issue later.",
            timestamp=start_time + timedelta(hours=1),
        ))

        return messages

    def _generate_thermal_analysis_scenario(self, start_time: datetime) -> List[SlackMessage]:
        """Generate thermal analysis requiring cross-functional coordination."""
        thread_id = f"thermal_{int(start_time.timestamp())}"
        messages = []

        messages.append(SlackMessage(
            message_id=f"{thread_id}_001",
            channel_id="#mechanical",
            thread_id=thread_id,
            user_id="grace",
            message_text="Thermal analysis complete for Power-Supply-v2. Junction temp hits 85°C under max load - need cooling solution.",
            timestamp=start_time,
            entities={"components": ["Power-Supply-v2"], "temperature": "85°C"}
        ))

        messages.append(SlackMessage(
            message_id=f"{thread_id}_002",
            channel_id="#mechanical",
            thread_id=thread_id,
            user_id="iris",
            message_text="Can we add thermal pads to PCB-Rev3? Or do we need active cooling?",
            timestamp=start_time + timedelta(minutes=30),
        ))

        messages.append(SlackMessage(
            message_id=f"{thread_id}_003",
            channel_id="#mechanical",
            thread_id=thread_id,
            user_id="alice",
            message_text="Active cooling adds cost. Let's try larger heat sink first - Thermal-Design can accommodate 15mm height.",
            timestamp=start_time + timedelta(hours=1),
        ))

        return messages

    def _generate_daily_updates(self, date: datetime) -> List[SlackMessage]:
        """Generate daily status updates and smaller decisions."""
        messages = []
        user_pool = random.sample(self.users, random.randint(3, 6))

        for i, user in enumerate(user_pool):
            msg_time = date + timedelta(hours=9, minutes=i*5)  # Staggered morning updates

            updates = [
                f"Status update: {random.choice(user.owned_components)} testing complete, all checks passed ✅",
                f"Blocker: waiting on {random.choice(['approval', 'parts', 'test results'])} for {random.choice(user.owned_components)}",
                f"Quick update: {random.choice(user.owned_components)} design iteration done, ready for review",
                f"FYI: {random.choice(user.owned_components)} schedule moved up by 2 days due to vendor delivery",
            ]

            messages.append(SlackMessage(
                message_id=f"daily_{date.strftime('%Y%m%d')}_{user.user_id}_{i:03d}",
                channel_id=random.choice(self.channels),
                user_id=user.user_id,
                message_text=random.choice(updates),
                timestamp=msg_time,
            ))

        return messages