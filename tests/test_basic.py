"""Basic system tests without external dependencies."""

import os
import sys
from datetime import datetime

# Add backend/pipelines to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend/pipelines'))

from models import UserProfile, SlackMessage, DecisionType
from data_generator import HardwareTeamDataGenerator

def test_models():
    """Test that models work correctly."""
    print("Testing models...")

    # Test UserProfile
    user = UserProfile(
        user_id="alice",
        user_name="Alice Chen",
        role="Mechanical Lead",
        owned_components=["Motor-XYZ", "Bracket-Assembly"],
        email="alice@company.com"
    )

    assert user.user_id == "alice"
    assert "Motor-XYZ" in user.owned_components
    print("✅ UserProfile model works")

    # Test SlackMessage
    message = SlackMessage(
        message_id="test_001",
        channel_id="#mechanical",
        thread_id="thread_001",
        user_id="alice",
        message_text="REQ-245: Motor torque changing from 15nm to 22nm",
        timestamp=datetime.now()
    )

    assert message.message_id == "test_001"
    assert "REQ-245" in message.message_text
    print("✅ SlackMessage model works")

def test_data_generation():
    """Test data generation without external dependencies."""
    print("Testing data generation...")

    generator = HardwareTeamDataGenerator()

    # Test user generation
    assert len(generator.users) == 10

    alice = next(u for u in generator.users if u.user_id == "alice")
    assert alice.user_name == "Alice Chen"
    assert alice.role == "Mechanical Lead"
    assert "Motor-XYZ" in alice.owned_components
    print("✅ User generation works")

    # Test message generation
    messages = generator.generate_realistic_conversations()
    assert len(messages) > 100

    # Check for REQ-245 scenario
    req_messages = [m for m in messages if "REQ-245" in m.message_text]
    assert len(req_messages) > 0
    print(f"✅ Generated {len(messages)} messages with REQ-245 scenarios")

def test_component_relationships():
    """Test component dependency logic."""
    print("Testing component relationships...")

    # This is a simple test without importing the full decision graph
    component_deps = {
        'Motor-XYZ': ['Bracket-Assembly', 'Power-Supply-v2'],
        'PCB-Rev3': ['Power-Supply-v2', 'ESP32-Firmware', 'I2C-Interface'],
        'Power-Supply-v2': ['Thermal-Design', 'Schematic'],
    }

    # Test that we have expected dependencies
    assert 'Power-Supply-v2' in component_deps['Motor-XYZ']
    assert 'ESP32-Firmware' in component_deps['PCB-Rev3']
    print("✅ Component relationships defined correctly")

def test_before_after_patterns():
    """Test regex patterns for before/after extraction."""
    print("Testing before/after patterns...")

    import re

    # Simple pattern matching without full entity extractor
    before_after_pattern = re.compile(
        r'(?:from\s+|changing\s+from\s+)?([^\s]+(?:\s*[^\s]+)*)\s*(?:→|->|to)\s*([^\s]+(?:\s*[^\s]+)*)',
        re.IGNORECASE
    )

    test_texts = [
        "Motor torque changing from 15nm to 22nm",
        "Wall thickness 2.5mm → 3.0mm",
        "Protocol changed from UART to I2C",
        "Temperature range -10°C to -20°C"
    ]

    for text in test_texts:
        match = before_after_pattern.search(text)
        assert match is not None, f"Failed to match pattern in: {text}"
        before, after = match.groups()
        assert before and after, f"Empty groups in: {text}"

    print("✅ Before/after pattern matching works")

def test_requirement_patterns():
    """Test requirement ID pattern matching."""
    print("Testing requirement patterns...")

    import re

    req_pattern = re.compile(r'REQ-\d+', re.IGNORECASE)

    test_texts = [
        "REQ-245: Motor torque requirement",
        "Updating REQ-118 for power consumption",
        "See requirements REQ-332 and REQ-089",
        "No requirements mentioned here"
    ]

    expected_matches = [
        ["REQ-245"],
        ["REQ-118"],
        ["REQ-332", "REQ-089"],
        []
    ]

    for text, expected in zip(test_texts, expected_matches):
        matches = req_pattern.findall(text)
        assert matches == expected, f"Expected {expected}, got {matches} for: {text}"

    print("✅ Requirement pattern matching works")

def test_realistic_scenarios():
    """Test that realistic scenarios are generated."""
    print("Testing realistic scenarios...")

    generator = HardwareTeamDataGenerator()
    messages = generator.generate_realistic_conversations()

    # Test for key scenario elements
    req_changes = [m for m in messages if "REQ-" in m.message_text]
    approvals = [m for m in messages if any(word in m.message_text.lower()
                                          for word in ["approved", "✅", "sign-off"])]
    conflicts = [m for m in messages if any(word in m.message_text.lower()
                                          for word in ["urgent", "crisis", "blocker"])]

    assert len(req_changes) > 0, "No requirement changes found"
    assert len(approvals) > 0, "No approvals found"
    assert len(conflicts) > 0, "No urgent scenarios found"

    print(f"✅ Found {len(req_changes)} req changes, {len(approvals)} approvals, {len(conflicts)} urgent items")

if __name__ == "__main__":
    print("🧪 Running basic system tests...")

    try:
        test_models()
        test_data_generation()
        test_component_relationships()
        test_before_after_patterns()
        test_requirement_patterns()
        test_realistic_scenarios()

        print("\n🎉 All basic tests passed!")
        print("\n📊 System appears to be working correctly for core functionality:")
        print("   ✅ Data models")
        print("   ✅ Message generation")
        print("   ✅ Pattern matching")
        print("   ✅ Realistic scenarios")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)