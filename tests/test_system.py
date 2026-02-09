"""Basic system tests for the Slack digest system."""

import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from data_generator import HardwareTeamDataGenerator
from entity_extractor import EntityExtractor
from models import SlackMessage, DecisionType

class TestDataGeneration:
    def test_user_generation(self):
        """Test that user profiles are generated correctly."""
        generator = HardwareTeamDataGenerator()
        assert len(generator.users) == 10

        # Check Alice's profile
        alice = next(u for u in generator.users if u.user_id == "alice")
        assert alice.user_name == "Alice Chen"
        assert alice.role == "Mechanical Lead"
        assert "Motor-XYZ" in alice.owned_components
        assert "Bracket-Assembly" in alice.owned_components

    def test_message_generation(self):
        """Test that realistic messages are generated."""
        generator = HardwareTeamDataGenerator()
        messages = generator.generate_realistic_conversations()

        assert len(messages) > 100  # Should have plenty of messages

        # Check that messages are sorted by timestamp
        timestamps = [msg.timestamp for msg in messages]
        assert timestamps == sorted(timestamps)

        # Check that we have different channels
        channels = set(msg.channel_id for msg in messages)
        assert len(channels) >= 3  # Multiple channels

    def test_req_scenario_generation(self):
        """Test REQ-245 style scenario generation."""
        generator = HardwareTeamDataGenerator()
        start_time = datetime.now()
        scenario = generator._generate_requirement_change_scenario(start_time)

        assert len(scenario) >= 3  # Multiple messages in thread

        # Check for REQ-245 pattern
        req_message = scenario[0]
        assert "REQ-245" in req_message.message_text
        assert "15nm" in req_message.message_text
        assert "22nm" in req_message.message_text

class TestEntityExtraction:
    def extractor(self):
        return EntityExtractor()

    def sample_messages(self):
        return [
            SlackMessage(
                message_id="test_001",
                channel_id="#req-reviews",
                thread_id="thread_001",
                user_id="eve",
                message_text="REQ-245: Motor torque requirement changing from 15nm to 22nm based on customer load analysis. This affects Motor-XYZ and potentially Bracket-Assembly.",
                timestamp=datetime.now()
            ),
            SlackMessage(
                message_id="test_002",
                channel_id="#mechanical",
                thread_id="thread_002",
                user_id="alice",
                message_text="✅ Approved Enclosure v2.1 design after thermal simulation passed. Wall thickness changed from 2.5mm to 3.0mm.",
                timestamp=datetime.now()
            )
        ]

    def test_quick_extraction(self):
        """Test quick regex-based entity extraction."""
        extractor = self.extractor()
        sample_messages = self.sample_messages()

        # Test requirement change message
        entities1 = extractor._quick_extract(sample_messages[0])
        assert entities1 is not None
        assert "REQ-245" in entities1.requirements
        assert "Motor-XYZ" in entities1.components
        assert entities1.decision_type == DecisionType.REQUIREMENT_CHANGE
        assert len(entities1.before_after_changes) > 0

        # Test approval message
        entities2 = extractor._quick_extract(sample_messages[1])
        assert entities2 is not None
        assert "Enclosure" in entities2.components
        assert entities2.decision_type == DecisionType.APPROVAL

    def test_before_after_extraction(self):
        """Test before/after change extraction."""
        extractor = self.extractor()
        sample_messages = self.sample_messages()

        # Test "from X to Y" pattern
        entities1 = extractor._quick_extract(sample_messages[0])
        changes = entities1.before_after_changes
        assert len(changes) > 0
        assert changes[0]["before"] == "15nm"
        assert changes[0]["after"] == "22nm"

        # Test "X to Y" pattern
        entities2 = extractor._quick_extract(sample_messages[1])
        changes = entities2.before_after_changes
        assert len(changes) > 0
        assert changes[0]["before"] == "2.5mm"
        assert changes[0]["after"] == "3.0mm"

class TestSystemIntegration:
    def test_end_to_end_flow(self):
        """Test basic end-to-end data flow."""
        # Generate data
        generator = HardwareTeamDataGenerator()
        messages = generator.generate_realistic_conversations()[:10]  # Small sample

        # Extract entities
        extractor = EntityExtractor()

        # Quick test without Claude API
        decisions = []
        for msg in messages:
            entities = extractor._quick_extract(msg)
            if entities and entities.decision_type:
                decision_text = extractor.extract_decision_text(msg, entities)
                decisions.append({
                    'message': msg,
                    'entities': entities,
                    'decision_text': decision_text
                })

        # Should find at least a few decisions
        assert len(decisions) >= 2

        # Check decision quality
        for decision in decisions:
            assert decision['entities'].decision_type is not None
            assert len(decision['decision_text']) > 10
            assert (len(decision['entities'].components) > 0 or
                   len(decision['entities'].requirements) > 0)

def test_component_dependencies():
    """Test component dependency mapping."""
    from decision_graph import DecisionGraphBuilder

    builder = DecisionGraphBuilder()

    # Test known dependencies
    assert "Power-Supply-v2" in builder.component_dependencies["Motor-XYZ"]
    assert "ESP32-Firmware" in builder.component_dependencies["PCB-Rev3"]

    # Test dependent finding
    dependents = builder._get_dependent_components(["Power-Supply-v2"])
    assert "Motor-XYZ" in dependents
    assert "PCB-Rev3" in dependents

if __name__ == "__main__":
    # Run basic tests without pytest
    print("🧪 Running basic system tests...")

    # Test data generation
    print("Testing data generation...")
    test_gen = TestDataGeneration()
    test_gen.test_user_generation()
    test_gen.test_message_generation()
    test_gen.test_req_scenario_generation()
    print("✅ Data generation tests passed")

    # Test entity extraction
    print("Testing entity extraction...")
    test_extract = TestEntityExtraction()
    extractor = EntityExtractor()
    sample_messages = [
        SlackMessage(
            message_id="test_001",
            channel_id="#req-reviews",
            thread_id="thread_001",
            user_id="eve",
            message_text="REQ-245: Motor torque requirement changing from 15nm to 22nm based on customer load analysis. This affects Motor-XYZ and potentially Bracket-Assembly.",
            timestamp=datetime.now()
        )
    ]

    entities = extractor._quick_extract(sample_messages[0])
    assert entities is not None
    assert "REQ-245" in entities.requirements
    print("✅ Entity extraction tests passed")

    # Test component dependencies
    print("Testing component dependencies...")
    test_component_dependencies()
    print("✅ Component dependency tests passed")

    # Test system integration
    print("Testing system integration...")
    test_integration = TestSystemIntegration()
    test_integration.test_end_to_end_flow()
    print("✅ System integration tests passed")

    print("🎉 All basic tests passed!")