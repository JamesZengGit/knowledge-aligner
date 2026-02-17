"""
Entity Extraction Pipeline for Knowledge Aligner
Uses Claude Haiku for fast, cost-effective entity extraction from Slack messages
Extracts: Requirements (REQ-XXX), Components, Decision indicators, Before/After changes
"""

import asyncio
import asyncpg
import anthropic
import json
import re
import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class ExtractedEntities:
    """Structured entities extracted from text"""
    requirements: List[str]          # REQ-XXX patterns
    components: List[str]            # Hardware components mentioned
    decision_indicators: List[str]   # Words suggesting decisions were made
    before_after: Dict[str, Any]     # Change patterns (X -> Y)
    decision_type: str               # requirement_change, design_decision, approval
    confidence: float                # Extraction confidence (0.0-1.0)
    mentions: List[str]              # @mentions for stakeholder tracking

@dataclass
class SlackMessage:
    """Slack message structure"""
    message_id: str
    channel_id: str
    thread_id: Optional[str]
    user_id: str
    message_text: str
    timestamp: datetime
    reactions: List[str] = None
    thread_replies: int = 0

class EntityExtractor:
    """
    Claude Haiku-powered entity extraction
    Optimized for speed and cost-effectiveness
    Target: Process 1000 messages/day at <$5 cost
    """

    def __init__(self):
        self.client = None
        self.db_pool = None

        # Pre-compiled regex patterns for fallback extraction
        self.req_pattern = re.compile(r'REQ-(\d+)', re.IGNORECASE)
        self.component_patterns = [
            re.compile(r'\b([A-Z][a-zA-Z]*-[A-Z0-9]+)\b'),  # Motor-XYZ, PCB-Rev3
            re.compile(r'\b([A-Z]{2,}[0-9]+[A-Za-z]*)\b'),  # ESP32, PCB3
            re.compile(r'\b(Bootloader|Firmware|Power[\s-]?Supply|Assembly)\b', re.IGNORECASE)
        ]
        self.decision_indicators = [
            'approved', 'decided', 'changing', 'update', 'revised', 'confirmed',
            'selected', 'rejected', 'implemented', 'modified', 'upgraded'
        ]

    async def init_claude_client(self):
        """Initialize Anthropic Claude client"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not found, using fallback extraction")
            return False

        self.client = anthropic.Anthropic(api_key=api_key)
        logger.info("Claude client initialized")
        return True

    async def init_db_pool(self, database_url: str):
        """Initialize database connection pool"""
        self.db_pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=10
        )

    async def extract_with_claude(self, message_text: str, user_context: Dict = None) -> ExtractedEntities:
        """
        Extract entities using Claude Haiku
        Optimized prompt for hardware engineering context
        """
        if not self.client:
            return await self.extract_with_fallback(message_text)

        # Build context-aware prompt
        context = ""
        if user_context:
            context = f"User: {user_context.get('name', 'Unknown')} ({user_context.get('role', 'Unknown')})\n"

        prompt = f"""{context}Extract engineering entities from this Slack message:

Message: {message_text}

Return JSON with these exact fields:
{{
  "requirements": ["REQ-245", "REQ-301"],  // REQ-XXX patterns found
  "components": ["Motor-XYZ", "PCB-Rev3"], // Hardware components mentioned
  "decision_indicators": ["approved", "changing"], // Decision-making words
  "before_after": {{"torque": {{"before": "15nm", "after": "22nm"}}}}, // Change patterns
  "decision_type": "requirement_change", // requirement_change|design_decision|approval|technical_decision
  "confidence": 0.85, // 0.0-1.0 extraction confidence
  "mentions": ["@alice", "@bob"] // @mentions found (without @)
}}

Focus on hardware engineering terms. If no clear decision is made, set decision_type to "discussion".
"""

        try:
            response = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-3-haiku-20240307",
                max_tokens=500,
                temperature=0.1,  # Low temperature for consistent extraction
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse JSON response
            content = response.content[0].text
            entities_dict = json.loads(content)

            # Validate and create ExtractedEntities
            entities = ExtractedEntities(
                requirements=entities_dict.get('requirements', []),
                components=entities_dict.get('components', []),
                decision_indicators=entities_dict.get('decision_indicators', []),
                before_after=entities_dict.get('before_after', {}),
                decision_type=entities_dict.get('decision_type', 'discussion'),
                confidence=float(entities_dict.get('confidence', 0.5)),
                mentions=entities_dict.get('mentions', [])
            )

            return entities

        except Exception as e:
            logger.error(f"Claude extraction failed: {e}")
            return await self.extract_with_fallback(message_text)

    async def extract_with_fallback(self, message_text: str) -> ExtractedEntities:
        """
        Fallback extraction using regex patterns
        Used when Claude API is unavailable
        """
        # Extract requirements
        requirements = self.req_pattern.findall(message_text)
        requirements = [f"REQ-{req}" for req in requirements]

        # Extract components
        components = []
        for pattern in self.component_patterns:
            matches = pattern.findall(message_text)
            components.extend(matches)

        # Remove duplicates while preserving order
        components = list(dict.fromkeys(components))

        # Find decision indicators
        found_indicators = []
        text_lower = message_text.lower()
        for indicator in self.decision_indicators:
            if indicator in text_lower:
                found_indicators.append(indicator)

        # Simple before/after pattern detection
        before_after = {}
        arrow_patterns = [
            r'(\w+)\s*(?:from|:)\s*([^\s]+)\s*(?:->|→|to)\s*([^\s]+)',
            r'(\w+)\s*(?:changing|changed)\s*from\s*([^\s]+)\s*to\s*([^\s]+)'
        ]

        for pattern in arrow_patterns:
            matches = re.findall(pattern, message_text, re.IGNORECASE)
            for match in matches:
                key, before, after = match
                before_after[key.lower()] = {"before": before, "after": after}

        # Determine decision type
        decision_type = "discussion"
        if found_indicators:
            if any(word in text_lower for word in ['req-', 'requirement']):
                decision_type = "requirement_change"
            elif any(word in text_lower for word in ['design', 'implement', 'build']):
                decision_type = "design_decision"
            elif any(word in text_lower for word in ['approved', 'accept', 'reject']):
                decision_type = "approval"
            else:
                decision_type = "technical_decision"

        # Extract mentions (simple @ pattern)
        mentions = re.findall(r'@(\w+)', message_text)

        # Calculate confidence based on entities found
        confidence = 0.3  # Base confidence for fallback
        if requirements:
            confidence += 0.3
        if components:
            confidence += 0.2
        if found_indicators:
            confidence += 0.2

        return ExtractedEntities(
            requirements=requirements,
            components=components,
            decision_indicators=found_indicators,
            before_after=before_after,
            decision_type=decision_type,
            confidence=min(confidence, 1.0),
            mentions=mentions
        )

    async def process_slack_message(self, message: SlackMessage) -> Optional[int]:
        """
        Process a Slack message and create decision record if appropriate
        Returns decision_id if decision was created, None otherwise
        """
        # Get user context for better extraction
        user_context = await self.get_user_context(message.user_id)

        # Extract entities
        entities = await self.extract_with_claude(message.message_text, user_context)

        # Store raw message with entities
        await self.store_slack_message(message, entities)

        # Only create decision if confidence is high enough and indicators present
        if entities.confidence < 0.6 or not entities.decision_indicators:
            logger.debug(f"Skipping decision creation for message {message.message_id} (confidence: {entities.confidence})")
            return None

        # Create decision record
        decision_id = await self.create_decision_record(message, entities, user_context)

        if decision_id:
            logger.info(f"Created decision {decision_id} from message {message.message_id}")

        return decision_id

    async def store_slack_message(self, message: SlackMessage, entities: ExtractedEntities):
        """Store raw Slack message with extracted entities"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO slack_messages
                (message_id, channel_id, thread_id, user_id, message_text, timestamp, entities, processed)
                VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE)
                ON CONFLICT (message_id) DO UPDATE SET
                    entities = $7,
                    processed = TRUE
            """,
            message.message_id,
            message.channel_id,
            message.thread_id,
            message.user_id,
            message.message_text,
            message.timestamp,
            json.dumps(asdict(entities))
            )

    async def create_decision_record(self,
                                   message: SlackMessage,
                                   entities: ExtractedEntities,
                                   user_context: Dict) -> Optional[int]:
        """Create decision record from extracted entities"""
        async with self.db_pool.acquire() as conn:
            try:
                # Insert decision
                decision_id = await conn.fetchval("""
                    INSERT INTO decisions
                    (thread_id, timestamp, author_user_id, author_name, author_role,
                     decision_type, decision_text, affected_components, referenced_reqs,
                     similarity_score, before_after)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    RETURNING decision_id
                """,
                message.thread_id or message.message_id,
                message.timestamp,
                message.user_id,
                user_context.get('user_name', 'Unknown'),
                user_context.get('role', 'Unknown'),
                entities.decision_type,
                message.message_text,
                entities.components,
                entities.requirements,
                entities.confidence,
                json.dumps(entities.before_after) if entities.before_after else None
                )

                # Add extraction metadata to decision_details
                await conn.execute("""
                    INSERT INTO decision_details (decision_id, detail_name, detail_value)
                    VALUES ($1, 'extraction_metadata', $2)
                """, decision_id, json.dumps({
                    'method': 'claude_haiku' if self.client else 'fallback',
                    'confidence': entities.confidence,
                    'mentions': entities.mentions,
                    'decision_indicators': entities.decision_indicators,
                    'source_message_id': message.message_id
                }))

                return decision_id

            except Exception as e:
                logger.error(f"Failed to create decision record: {e}")
                return None

    async def get_user_context(self, user_id: str) -> Dict:
        """Get user context from database"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT user_name, role, owned_components, email
                FROM user_profiles
                WHERE user_id = $1
            """, user_id)

            if row:
                return dict(row)
            else:
                return {'user_name': user_id, 'role': 'Unknown', 'owned_components': []}

    async def batch_process_messages(self, limit: int = 100) -> int:
        """
        Process unprocessed Slack messages in batch
        Returns number of decisions created
        """
        async with self.db_pool.acquire() as conn:
            # Get unprocessed messages
            rows = await conn.fetch("""
                SELECT message_id, channel_id, thread_id, user_id, message_text, timestamp
                FROM slack_messages
                WHERE processed = FALSE
                ORDER BY timestamp ASC
                LIMIT $1
            """, limit)

        decisions_created = 0

        for row in rows:
            message = SlackMessage(
                message_id=row['message_id'],
                channel_id=row['channel_id'],
                thread_id=row['thread_id'],
                user_id=row['user_id'],
                message_text=row['message_text'],
                timestamp=row['timestamp']
            )

            decision_id = await self.process_slack_message(message)
            if decision_id:
                decisions_created += 1

        logger.info(f"Processed {len(rows)} messages, created {decisions_created} decisions")
        return decisions_created

    async def get_extraction_stats(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        async with self.db_pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_messages,
                    COUNT(*) FILTER (WHERE processed = TRUE) as processed,
                    COUNT(*) FILTER (WHERE processed = FALSE) as pending,
                    AVG(CAST(entities->>'confidence' AS FLOAT)) as avg_confidence
                FROM slack_messages
                WHERE entities IS NOT NULL
            """)

            decision_stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_decisions,
                    COUNT(*) FILTER (WHERE embedding_status = 'embedded') as embedded,
                    COUNT(*) FILTER (WHERE embedding_status = 'pending') as pending_embedding
                FROM decisions
            """)

            return {
                'messages': dict(stats) if stats else {},
                'decisions': dict(decision_stats) if decision_stats else {}
            }

    async def close(self):
        """Clean up resources"""
        if self.db_pool:
            await self.db_pool.close()

# CLI for testing and batch processing
async def main():
    import argparse

    parser = argparse.ArgumentParser(description='Entity Extraction Pipeline')
    parser.add_argument('--message', type=str, help='Test single message extraction')
    parser.add_argument('--batch', action='store_true', help='Process unprocessed messages')
    parser.add_argument('--stats', action='store_true', help='Show extraction statistics')
    parser.add_argument('--limit', type=int, default=100, help='Batch processing limit')

    args = parser.parse_args()

    # Initialize extractor
    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/knowledge_aligner')
    extractor = EntityExtractor()

    try:
        await extractor.init_claude_client()
        await extractor.init_db_pool(database_url)

        if args.message:
            # Test single message
            entities = await extractor.extract_with_claude(args.message)
            print("Extracted entities:")
            print(json.dumps(asdict(entities), indent=2))

        elif args.batch:
            # Process batch of messages
            decisions_created = await extractor.batch_process_messages(args.limit)
            print(f"Created {decisions_created} decisions from batch processing")

        elif args.stats:
            # Show statistics
            stats = await extractor.get_extraction_stats()
            print("Extraction Statistics:")
            print(json.dumps(stats, indent=2, default=str))

        else:
            print("Use --message 'text', --batch, or --stats")

    finally:
        await extractor.close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())