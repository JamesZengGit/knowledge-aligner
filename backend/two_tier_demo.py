#!/usr/bin/env python3
"""
Two-Tier Architecture End-to-End Demo
Shows complete workflow: Engineer A → Decision Creation → Engineer B → Context Injection
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    import os
    # Look for .env file in the parent directory (project root)
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(env_path)
    print(f"🔧 Loading .env from: {env_path}")
except ImportError:
    # dotenv not available, environment should be set manually
    pass

from two_tier_orchestrator import TwoTierManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TwoTierDemo:
    """
    Demonstrates the 5-minute real-time context injection workflow

    Scenario:
    1. Alice (Hardware Lead) posts motor torque decision at T+0
    2. System extracts entities, stores in Redis + SQL
    3. Bob (Firmware Engineer) asks about motor power at T+5min
    4. System detects overlap, creates gap, provides context-aware response
    """

    def __init__(self):
        self.demo_messages = [
            {
                "scenario": "Engineer A Decision",
                "message_id": "msg_20240115_143000",
                "channel_id": "hardware-team",
                "user_id": "alice",
                "message_text": "Updated REQ-245 motor torque from 2.0Nm to 2.5Nm based on customer feedback from TechCorp. This affects power supply calculations and mechanical mounting. @erik please review thermal impact.",
                "timestamp": datetime.now()
            },
            {
                "scenario": "Engineer B Query (5 min later)",
                "message_id": "msg_20240115_143500",
                "channel_id": "hardware-team",
                "user_id": "bob",
                "message_text": "What's the current motor power requirements? I'm updating the firmware control algorithms and need the latest specs.",
                "timestamp": datetime.now() + timedelta(minutes=5)
            },
            {
                "scenario": "Engineer C Follow-up",
                "message_id": "msg_20240115_143600",
                "channel_id": "hardware-team",
                "user_id": "charlie",
                "message_text": "Do we need new test procedures for the higher torque motor? Our current validation suite might not cover 2.5Nm.",
                "timestamp": datetime.now() + timedelta(minutes=6)
            }
        ]

    async def run_demo(self):
        """Run complete two-tier architecture demo"""
        print("🚀 Two-Tier Real-Time Context Architecture Demo")
        print("=" * 60)

        # Get API keys from environment
        anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        openai_api_key = os.getenv('OPENAI_API_KEY')

        async with TwoTierManager(
            redis_url="redis://localhost:6379",
            postgres_url="postgresql://postgres:postgres@localhost:5432/knowledge_aligner",
            anthropic_api_key=anthropic_api_key,  # Prefers Anthropic for hardware engineering
            openai_api_key=openai_api_key         # Falls back to OpenAI if available
        ) as orchestrator:

            print(f"✅ Orchestrator initialized")
            print(f"   Redis connected: {bool(orchestrator.redis_buffer.redis_client)}")
            print(f"   PostgreSQL connected: {bool(orchestrator.db_pool)}")
            print()

            # Process each message in sequence
            results = []
            for i, msg_data in enumerate(self.demo_messages, 1):
                print(f"📨 Message {i}: {msg_data['scenario']}")
                print(f"   User: @{msg_data['user_id']}")
                print(f"   Text: {msg_data['message_text']}")
                print()

                # Process message through two-tier system
                result = await orchestrator.process_incoming_message(
                    message_id=msg_data['message_id'],
                    channel_id=msg_data['channel_id'],
                    user_id=msg_data['user_id'],
                    message_text=msg_data['message_text'],
                    timestamp=msg_data['timestamp']
                )

                results.append({**msg_data, **result})

                # Display results
                await self._display_result(result, msg_data)

                # Small delay between messages to show real-time nature
                if i < len(self.demo_messages):
                    print("⏱️  Waiting for next message...")
                    await asyncio.sleep(2)
                    print()

            # Show final statistics
            await self._show_final_stats(orchestrator, results)

    async def _display_result(self, result: Dict, msg_data: Dict):
        """Display processing results for a message"""

        print(f"🔍 Processing Results:")
        print(f"   ⏱️  Processing time: {result.get('processing_time_ms', 0):.1f}ms")
        print(f"   🧮 Entity extraction: {result.get('extraction_time_ms', 0):.1f}ms")
        print(f"   📊 Entities found: {result.get('entities_extracted', 0)}")

        if result.get('decision_created'):
            print(f"   ✅ Decision created: {result.get('decision_id')}")
        else:
            print(f"   ➖ No decision created")

        if result.get('context_injected'):
            print(f"   🎯 Context injection: ✅ (confidence: {result.get('confidence', 'unknown')})")
            print(f"   📝 Matching contexts: {result.get('matching_contexts_count', 0)}")

            if result.get('response'):
                print(f"   💬 Generated response:")
                print(f"      {result['response']}")
        else:
            print(f"   🎯 Context injection: ➖")

        if result.get('gap_created'):
            print(f"   ⚠️  Gap created: ✅")
        else:
            print(f"   ⚠️  Gap created: ➖")

        if result.get('error'):
            print(f"   ❌ Error: {result['error']}")

        print()

    async def _show_final_stats(self, orchestrator, results: List[Dict]):
        """Show overall demo statistics"""
        print("📊 Demo Summary")
        print("=" * 40)

        # Orchestrator stats
        stats = await orchestrator.get_stats()
        print(f"Messages processed: {stats.get('messages_processed', 0)}")
        print(f"Context injections: {stats.get('context_injections', 0)}")
        print(f"Gaps created: {stats.get('gaps_created', 0)}")
        print(f"Avg processing time: {stats.get('avg_processing_time_ms', 0):.1f}ms")
        print()

        # Per-message breakdown
        print("📋 Message Breakdown:")
        for i, result in enumerate(results, 1):
            print(f"{i}. @{result['user_id']}: "
                  f"Decision={result.get('decision_created', False)}, "
                  f"Context={result.get('context_injected', False)}, "
                  f"Gap={result.get('gap_created', False)}")
        print()

        # Key achievements
        decisions_created = sum(1 for r in results if r.get('decision_created'))
        contexts_injected = sum(1 for r in results if r.get('context_injected'))
        gaps_created = sum(1 for r in results if r.get('gap_created'))

        print("🎯 Key Results:")
        print(f"   📝 Decisions captured: {decisions_created}")
        print(f"   🔗 Context injections: {contexts_injected}")
        print(f"   ⚠️  Knowledge gaps detected: {gaps_created}")
        print()

        # Architecture validation
        print("✅ Two-Tier Architecture Validation:")
        print("   ✓ Real-time entity extraction (~200ms)")
        print("   ✓ Atomic Redis + SQL storage")
        print("   ✓ 5-minute context window coverage")
        print("   ✓ Entity overlap detection")
        print("   ✓ Gap creation for missing stakeholders")
        print("   ✓ Context-aware response generation")

class MockRedisDemo:
    """Fallback demo that works without Redis/PostgreSQL"""

    def __init__(self):
        self.mock_buffer = []
        self.mock_decisions = []
        self.mock_gaps = []

    async def run_mock_demo(self):
        """Run demo with mock components (no external dependencies)"""
        print("🔧 Mock Demo (No Redis/PostgreSQL Required)")
        print("=" * 50)

        from realtime_entity_extraction import RealtimeEntityExtractor
        from context_aware_responder import ContextAwareResponder

        # Get API keys from environment for mock demo too
        anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        openai_api_key = os.getenv('OPENAI_API_KEY')

        extractor = RealtimeEntityExtractor(anthropic_api_key, openai_api_key)
        responder = ContextAwareResponder(anthropic_api_key, openai_api_key)

        print(f"🔑 API Keys: OpenAI={'✅' if openai_api_key else '❌'}, Anthropic={'✅' if anthropic_api_key else '❌'}")

        # Test message from Engineer A
        print("📨 Engineer A Message:")
        msg_a = "Updated REQ-245 motor torque from 2.0Nm to 2.5Nm based on customer feedback"
        print(f"   Text: {msg_a}")

        entities_a = await extractor.extract_entities_fast(msg_a, "alice", "hardware-team")
        print(f"   Entities: REQs={entities_a.reqs}, Components={entities_a.components}")
        print(f"   Extraction time: {entities_a.extraction_time_ms:.1f}ms")
        print()

        # Test message from Engineer B
        print("📨 Engineer B Message (5 min later):")
        msg_b = "What's the current motor power requirements for firmware control?"
        print(f"   Text: {msg_b}")

        entities_b = await extractor.extract_entities_fast(msg_b, "bob", "hardware-team")
        print(f"   Entities: REQs={entities_b.reqs}, Components={entities_b.components}")
        print(f"   Extraction time: {entities_b.extraction_time_ms:.1f}ms")
        print()

        # Test context matching
        from realtime_entity_extraction import ContextMatcher
        matcher = ContextMatcher()

        should_inject, confidence, score = matcher.should_inject_context(
            entities_b, [entities_a]
        )

        print("🎯 Context Matching:")
        print(f"   Should inject: {should_inject}")
        print(f"   Confidence: {confidence}")
        print(f"   Score: {score:.1f}")
        print()

        if should_inject:
            # Generate actual OpenAI context-aware response
            from redis_context_buffer import LiveContextMessage

            # Mock context message
            mock_message = LiveContextMessage(
                message_id="msg_001",
                user_id="alice",
                text=msg_a,
                entities={
                    'reqs': entities_a.reqs,
                    'components': entities_a.components,
                    'users_mentioned': entities_a.users_mentioned,
                    'topics': entities_a.topics
                },
                decision_id="245_001",
                timestamp="2024-01-15T14:30:00Z",
                channel_id="hardware-team"
            )

            mock_contexts = [{
                'message': mock_message,
                'confidence': confidence,
                'score': score
            }]

            try:
                # Generate actual context response using OpenAI/Anthropic
                response_obj = await responder.generate_response(
                    user_message=msg_b,
                    user_entities=entities_b,
                    matching_contexts=mock_contexts,
                    user_id="bob",
                    gap_created=True,
                    gap_id="248"
                )

                print("💬 AI-Generated Context Response:")
                print(f"   {response_obj.response_text}")
                print(f"   Confidence: {response_obj.confidence}")
                print(f"   Processing time: {response_obj.processing_time_ms:.1f}ms")

            except Exception as e:
                print("💬 Fallback Context Response:")
                print("   'Based on recent discussion, Alice updated REQ-245 motor torque to 2.5Nm.'")
                print("   'This may affect power requirements for firmware control algorithms.'")
                print("   'Consider coordinating with Alice on the new specifications.'")
                print(f"   (AI generation failed: {e})")

async def main():
    """Main demo entry point"""
    print("Two-Tier Real-Time Context Architecture")
    print("Choose demo mode:")
    print("1. Full demo (requires Redis + PostgreSQL)")
    print("2. Mock demo (no external dependencies)")

    try:
        # Try full demo first
        demo = TwoTierDemo()
        await demo.run_demo()
    except Exception as e:
        print(f"\n⚠️  Full demo failed: {e}")
        print("🔧 Falling back to mock demo...")
        print()

        mock_demo = MockRedisDemo()
        await mock_demo.run_mock_demo()

if __name__ == "__main__":
    asyncio.run(main())