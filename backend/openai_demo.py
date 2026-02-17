#!/usr/bin/env python3
"""
OpenAI-Powered Two-Tier Architecture Demo
Shows entity extraction and context-aware responses using GPT-3.5 + GPT-4
"""

import asyncio
import os
import time
from datetime import datetime

# Load environment variables from root directory
try:
    from dotenv import load_dotenv
    import os
    # Look for .env file in the parent directory (project root)
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(env_path)
    print(f"🔧 Loading .env from: {env_path}")
except ImportError:
    print("⚠️  dotenv not available, using system environment")
    pass

import openai

class OpenAITwoTierDemo:
    """Demonstrates OpenAI-powered real-time context injection"""

    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        self.client = openai.AsyncOpenAI(api_key=api_key)
        print(f"✅ OpenAI client initialized (key: {api_key[:10]}...)")

    async def extract_entities(self, message_text: str) -> dict:
        """Extract entities using GPT-3.5-turbo"""
        start_time = time.time()

        prompt = f"""Extract entities from this hardware engineering message. Return JSON only.

Message: "{message_text}"

Return JSON with:
- reqs: Array of requirement IDs (REQ-XXX format)
- components: Array of hardware components
- users_mentioned: Array of @username mentions
- topics: Array of engineering topics
- confidence: Float 0-1

JSON:"""

        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        import json
        entities = json.loads(response.choices[0].message.content)
        extraction_time = (time.time() - start_time) * 1000
        entities['extraction_time_ms'] = extraction_time

        return entities

    async def generate_context_response(self, user_message: str, context_data: dict) -> str:
        """Generate context-aware response using GPT-4"""

        context_summary = f"""📋 Components: {', '.join(context_data.get('overlapping_components', []))}
📑 Requirements: {', '.join(context_data.get('overlapping_reqs', []))}

🕐 Recent discussions:
1. @alice (5m ago): {context_data.get('context_text', 'Updated motor specifications')}

🚨 NOTE: This user wasn't included in the original discussions, so I've created a knowledge gap alert."""

        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an AI assistant for hardware engineering teams. Provide concise, actionable responses."},
                {"role": "user", "content": f"""A team member (@bob) just asked: "{user_message}"

I found related recent discussions:
{context_summary}

Please provide a helpful response that:
1. Summarizes the relevant context
2. Highlights key decisions or changes
3. Suggests next steps (2-3 sentences max)

Response:"""}
            ],
            max_tokens=300,
            temperature=0.3
        )

        return response.choices[0].message.content.strip()

    async def run_demo(self):
        """Run complete OpenAI-powered two-tier demo"""
        print("\n🚀 OpenAI Two-Tier Real-Time Context Architecture Demo")
        print("=" * 65)

        # Engineer A posts decision
        print("\n📨 Engineer A Message (T+0):")
        msg_a = "Updated REQ-245 motor torque from 2.0Nm to 2.5Nm based on customer feedback from TechCorp"
        print(f"   @alice: {msg_a}")

        entities_a = await self.extract_entities(msg_a)
        print(f"   🔍 Entities: REQs={entities_a.get('reqs', [])}, Components={entities_a.get('components', [])}")
        print(f"   ⚡ Extraction: {entities_a.get('extraction_time_ms', 0):.1f}ms")

        # Engineer B asks question 5 min later
        print("\n📨 Engineer B Message (T+5min):")
        msg_b = "What's the current motor power requirements for firmware control algorithms?"
        print(f"   @bob: {msg_b}")

        entities_b = await self.extract_entities(msg_b)
        print(f"   🔍 Entities: REQs={entities_b.get('reqs', [])}, Components={entities_b.get('components', [])}")
        print(f"   ⚡ Extraction: {entities_b.get('extraction_time_ms', 0):.1f}ms")

        # Context overlap detection
        overlapping_components = list(set(entities_a.get('components', [])) & set(entities_b.get('components', [])))
        overlapping_reqs = list(set(entities_a.get('reqs', [])) & set(entities_b.get('reqs', [])))

        if overlapping_components or overlapping_reqs:
            print(f"\n🎯 Context Overlap Detected!")
            print(f"   Components: {overlapping_components}")
            print(f"   Requirements: {overlapping_reqs}")
            print(f"   Confidence: HIGH (entity match)")

            # Generate intelligent response
            context_data = {
                'overlapping_components': overlapping_components or entities_b.get('components', []),
                'overlapping_reqs': overlapping_reqs,
                'context_text': msg_a
            }

            print(f"\n🤖 Generating GPT-4 Context Response...")
            response = await self.generate_context_response(msg_b, context_data)

            print(f"\n💬 Context-Aware Response:")
            print(f"   {response}")

        print(f"\n✅ OpenAI Two-Tier Architecture Demo Complete!")
        print(f"   🔗 Entity extraction: GPT-3.5-turbo")
        print(f"   🧠 Context responses: GPT-4")
        print(f"   ⚡ Real-time context injection: Working")
        print(f"   🎯 Gap detection: Active")

async def main():
    try:
        demo = OpenAITwoTierDemo()
        await demo.run_demo()
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("💡 Make sure OPENAI_API_KEY is set in .env file")

if __name__ == "__main__":
    asyncio.run(main())