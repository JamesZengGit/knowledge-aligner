"""Entity extraction from Slack messages using Claude Haiku."""

import os
import re
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import anthropic
from .models import ExtractedEntities, DecisionType, SlackMessage
from dotenv import load_dotenv

load_dotenv()

class EntityExtractor:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        # Regex patterns for quick entity detection
        self.req_pattern = re.compile(r'REQ-\d+', re.IGNORECASE)
        self.component_keywords = [
            'Motor-XYZ', 'Bracket-Assembly', 'ESP32-Firmware', 'Bootloader',
            'BOM', 'Vendor-Selection', 'PCB-Rev3', 'Power-Supply-v2', 'Requirements',
            'Schedule', 'Test-Fixtures', 'QA-Process', 'Enclosure', 'Thermal-Design',
            'Driver-Code', 'I2C-Interface', 'Schematic', 'Layout', 'Assembly-Process', 'DFM'
        ]

        self.decision_indicators = [
            'approved', 'decided', 'going with', 'changed from', 'switched to',
            'updating', 'revised', 'proceeding with', 'sign-off', 'green light',
            '✅', 'completed', 'finalized', 'confirmed'
        ]

        self.before_after_pattern = re.compile(
            r'(?:from\s+|changing\s+from\s+)?(\w+(?:\.\w+)*(?:\s*\w+)*)\s*(?:→|->|to)\s*(\w+(?:\.\w+)*(?:\s*\w+)*)',
            re.IGNORECASE
        )

    async def extract_entities(self, messages: List[SlackMessage]) -> List[ExtractedEntities]:
        """Extract entities from a batch of Slack messages."""
        results = []

        # Group messages by thread for context
        threads = {}
        for msg in messages:
            thread_id = msg.thread_id or msg.message_id
            if thread_id not in threads:
                threads[thread_id] = []
            threads[thread_id].append(msg)

        for thread_id, thread_messages in threads.items():
            entities = await self._extract_from_thread(thread_messages)
            results.extend(entities)

        return results

    async def _extract_from_thread(self, messages: List[SlackMessage]) -> List[ExtractedEntities]:
        """Extract entities from a thread of messages."""
        # Quick regex-based extraction first
        quick_entities = []
        for msg in messages:
            entities = self._quick_extract(msg)
            if entities:
                quick_entities.append((msg, entities))

        # Use Claude for deeper analysis on promising messages
        detailed_entities = []
        for msg, quick_result in quick_entities:
            if self._is_decision_candidate(quick_result):
                detailed_result = await self._claude_extract(msg, messages)
                detailed_entities.append(detailed_result)

        return detailed_entities

    def _quick_extract(self, message: SlackMessage) -> Optional[ExtractedEntities]:
        """Quick regex-based entity extraction."""
        text = message.message_text.lower()

        # Extract requirements
        reqs = self.req_pattern.findall(message.message_text)

        # Extract components
        components = [comp for comp in self.component_keywords
                     if comp.lower() in text]

        # Extract decision indicators
        indicators = [ind for ind in self.decision_indicators
                     if ind in text]

        # Extract before/after changes
        before_after = []
        matches = self.before_after_pattern.findall(message.message_text)
        for before, after in matches:
            before_after.append({"before": before.strip(), "after": after.strip()})

        # Determine decision type
        decision_type = None
        if reqs and ('req' in text or 'requirement' in text):
            decision_type = DecisionType.REQUIREMENT_CHANGE
        elif any(word in text for word in ['approved', '✅', 'sign-off', 'green light']):
            decision_type = DecisionType.APPROVAL
        elif components and indicators:
            decision_type = DecisionType.DESIGN_DECISION

        if reqs or components or indicators or before_after:
            return ExtractedEntities(
                requirements=reqs,
                components=components,
                decision_indicators=indicators,
                before_after_changes=before_after,
                decision_type=decision_type
            )

        return None

    def _is_decision_candidate(self, entities: ExtractedEntities) -> bool:
        """Determine if a message is worth deeper analysis."""
        return (
            len(entities.requirements) > 0 or
            len(entities.components) > 0 or
            len(entities.decision_indicators) > 0 or
            len(entities.before_after_changes) > 0
        )

    async def _claude_extract(self, message: SlackMessage, context_messages: List[SlackMessage]) -> ExtractedEntities:
        """Use Claude for detailed entity extraction with context."""

        # Build context from thread
        context = "\n".join([
            f"[{msg.timestamp}] {msg.user_id}: {msg.message_text}"
            for msg in sorted(context_messages, key=lambda x: x.timestamp)
        ])

        prompt = f"""Extract decision-related entities from this hardware engineering team Slack message.

Context (full thread):
{context}

Target message:
[{message.timestamp}] {message.user_id}: {message.message_text}

Extract the following:

1. Requirements mentioned (format: REQ-XXX)
2. Hardware components mentioned (Motor-XYZ, PCB-Rev3, etc.)
3. Decision indicators (approved, changed, decided, etc.)
4. Before/after changes (15nm→22nm, aluminum→polymer, etc.)
5. Decision type (requirement_change, design_decision, or approval)

Focus on the target message but use thread context to understand the decision being made.

Return JSON format:
{{
    "requirements": ["REQ-XXX", ...],
    "components": ["Component-Name", ...],
    "decision_indicators": ["approved", "changed", ...],
    "before_after_changes": [{{"before": "old_value", "after": "new_value"}}, ...],
    "decision_type": "requirement_change|design_decision|approval"
}}"""

        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse JSON response
            result = json.loads(response.content[0].text)

            return ExtractedEntities(
                requirements=result.get("requirements", []),
                components=result.get("components", []),
                decision_indicators=result.get("decision_indicators", []),
                before_after_changes=result.get("before_after_changes", []),
                decision_type=DecisionType(result.get("decision_type")) if result.get("decision_type") else None
            )

        except Exception as e:
            print(f"Claude extraction failed for message {message.message_id}: {e}")
            # Fallback to quick extraction
            return self._quick_extract(message) or ExtractedEntities()

    def extract_decision_text(self, message: SlackMessage, entities: ExtractedEntities) -> str:
        """Extract clean decision text for storage."""
        text = message.message_text

        # If we have before/after changes, highlight them
        if entities.before_after_changes:
            for change in entities.before_after_changes:
                text = text.replace(
                    f"{change['before']} to {change['after']}",
                    f"**{change['before']} → {change['after']}**"
                )

        # If we have requirements, highlight them
        for req in entities.requirements:
            text = text.replace(req, f"**{req}**")

        return text