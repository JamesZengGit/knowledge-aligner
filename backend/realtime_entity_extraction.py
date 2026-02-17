"""
Real-time Entity Extraction for Two-Tier Architecture
Fast entity extraction using Claude Haiku (~200ms) for live context injection
"""

import re
import json
import time
import asyncio
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

if not ANTHROPIC_AVAILABLE and not OPENAI_AVAILABLE:
    logging.warning("Neither Anthropic nor OpenAI available, using fallback extraction")

logger = logging.getLogger(__name__)

@dataclass
class ExtractedEntities:
    """Structured entity extraction results"""
    reqs: List[str]                # REQ-XXX requirement IDs
    components: List[str]          # Hardware components
    users_mentioned: List[str]     # @username mentions
    topics: List[str]              # Engineering topics/concepts
    confidence: float              # Extraction confidence 0-1
    extraction_time_ms: float      # Performance monitoring

class RealtimeEntityExtractor:
    """
    Fast entity extraction optimized for 5-minute context windows

    Uses Claude Haiku for accuracy with regex fallback for reliability
    Target: <200ms per message for real-time chat integration
    """

    def __init__(self, anthropic_api_key: Optional[str] = None, openai_api_key: Optional[str] = None):
        self.anthropic_client = None
        self.openai_client = None

        # Initialize Anthropic client (preferred for hardware engineering)
        if ANTHROPIC_AVAILABLE and anthropic_api_key:
            self.anthropic_client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)

        # Initialize OpenAI client as alternative
        elif OPENAI_AVAILABLE and openai_api_key:
            self.openai_client = openai.AsyncOpenAI(api_key=openai_api_key)

        # Hardware engineering vocabulary for better extraction
        self.component_patterns = {
            r'\b(?:motor|actuator|servo|stepper)\b': 'motor',
            r'\b(?:pcb|circuit\s+board|board)\b': 'pcb',
            r'\b(?:power\s+supply|psu|voltage|current)\b': 'power_supply',
            r'\b(?:firmware|software|code)\b': 'firmware',
            r'\b(?:thermal|heat|temperature|cooling)\b': 'thermal',
            r'\b(?:mechanical|mounting|assembly)\b': 'mechanical',
            r'\b(?:security|encryption|auth)\b': 'security',
            r'\b(?:validation|testing|qa|test)\b': 'testing',
            r'\b(?:architecture|system|integration)\b': 'architecture',
            r'\b(?:protocol|communication|interface)\b': 'protocol'
        }

        self.topic_patterns = {
            r'\b(?:torque|force|power)\b': 'mechanical_specs',
            r'\b(?:temperature|thermal|heat)\b': 'thermal_management',
            r'\b(?:voltage|current|power)\b': 'electrical_specs',
            r'\b(?:can\s+bus|i2c|spi|uart)\b': 'communication_protocols',
            r'\b(?:stackup|layer|trace)\b': 'pcb_design',
            r'\b(?:boot|secure|encryption)\b': 'security_features'
        }

    async def extract_entities_fast(self, message_text: str, user_id: str, channel_id: str) -> ExtractedEntities:
        """
        Extract entities with <200ms target performance
        Primary: Haiku API, Fallback: Regex patterns
        """
        start_time = time.time()

        try:
            # Try Anthropic Claude Haiku first (preferred for hardware engineering)
            if self.anthropic_client:
                entities = await self._extract_with_haiku(message_text)
                if entities:
                    entities.extraction_time_ms = (time.time() - start_time) * 1000
                    return entities

            # Try OpenAI GPT as alternative
            elif self.openai_client:
                entities = await self._extract_with_openai(message_text)
                if entities:
                    entities.extraction_time_ms = (time.time() - start_time) * 1000
                    return entities

        except Exception as e:
            logger.warning(f"LLM extraction failed, using fallback: {e}")

        # Fallback to regex patterns
        entities = await self._extract_with_regex(message_text)
        entities.extraction_time_ms = (time.time() - start_time) * 1000
        return entities

    async def _extract_with_haiku(self, message_text: str) -> Optional[ExtractedEntities]:
        """
        Use Claude Haiku for accurate entity extraction
        Optimized prompt for hardware engineering context
        """
        if not self.anthropic_client:
            return None

        try:
            # Optimized prompt for hardware engineering
            prompt = f"""Extract entities from this hardware engineering message. Be precise and only extract entities that are explicitly mentioned.

Message: "{message_text}"

Return JSON with these fields:
- reqs: Array of requirement IDs (REQ-XXX format)
- components: Array of hardware components (motor, pcb, firmware, etc)
- users_mentioned: Array of @username mentions
- topics: Array of engineering topics/concepts
- confidence: Float 0-1 for extraction confidence

Example: {{"reqs": ["REQ-245"], "components": ["motor", "power_supply"], "users_mentioned": ["@alice"], "topics": ["torque_specs"], "confidence": 0.9}}

JSON:"""

            # Use Haiku for speed (~200ms)
            response = await self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,  # Keep response short for speed
                temperature=0.1,  # Low temperature for consistency
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse JSON response
            response_text = response.content[0].text.strip()
            if response_text.startswith('```json'):
                response_text = response_text.split('```json')[1].split('```')[0].strip()

            extracted_data = json.loads(response_text)

            return ExtractedEntities(
                reqs=extracted_data.get('reqs', []),
                components=extracted_data.get('components', []),
                users_mentioned=extracted_data.get('users_mentioned', []),
                topics=extracted_data.get('topics', []),
                confidence=extracted_data.get('confidence', 0.8),
                extraction_time_ms=0  # Will be set by caller
            )

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.warning(f"Failed to parse Haiku response: {e}")
            return None
        except Exception as e:
            logger.error(f"Haiku API error: {e}")
            return None

    async def _extract_with_openai(self, message_text: str) -> Optional[ExtractedEntities]:
        """
        Use OpenAI GPT for entity extraction as alternative to Claude
        Fast model with structured JSON output
        """
        if not self.openai_client:
            return None

        try:
            # Optimized prompt for hardware engineering (similar to Claude)
            prompt = f"""Extract entities from this hardware engineering message. Be precise and only extract entities that are explicitly mentioned.

Message: "{message_text}"

Return JSON with these fields:
- reqs: Array of requirement IDs (REQ-XXX format)
- components: Array of hardware components (motor, pcb, firmware, etc)
- users_mentioned: Array of @username mentions
- topics: Array of engineering topics/concepts
- confidence: Float 0-1 for extraction confidence

Example: {{"reqs": ["REQ-245"], "components": ["motor", "power_supply"], "users_mentioned": ["@alice"], "topics": ["torque_specs"], "confidence": 0.9}}

JSON:"""

            # Use GPT-3.5-turbo for speed (~200ms target)
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            # Parse JSON response
            response_text = response.choices[0].message.content.strip()
            extracted_data = json.loads(response_text)

            return ExtractedEntities(
                reqs=extracted_data.get('reqs', []),
                components=extracted_data.get('components', []),
                users_mentioned=extracted_data.get('users_mentioned', []),
                topics=extracted_data.get('topics', []),
                confidence=extracted_data.get('confidence', 0.8),
                extraction_time_ms=0  # Will be set by caller
            )

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.warning(f"Failed to parse OpenAI response: {e}")
            return None
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None

    async def _extract_with_regex(self, message_text: str) -> ExtractedEntities:
        """
        Fallback regex extraction for reliability
        Fast local processing when API unavailable
        """
        message_lower = message_text.lower()

        # Extract REQ-XXX patterns
        req_pattern = r'REQ-\d+'
        reqs = re.findall(req_pattern, message_text, re.IGNORECASE)

        # Extract @username mentions
        user_pattern = r'@(\w+)'
        users_mentioned = ['@' + match for match in re.findall(user_pattern, message_text)]

        # Extract components using patterns
        components = []
        for pattern, component in self.component_patterns.items():
            if re.search(pattern, message_lower, re.IGNORECASE):
                components.append(component)

        # Extract topics using patterns
        topics = []
        for pattern, topic in self.topic_patterns.items():
            if re.search(pattern, message_lower, re.IGNORECASE):
                topics.append(topic)

        return ExtractedEntities(
            reqs=reqs,
            components=list(set(components)),  # Remove duplicates
            users_mentioned=users_mentioned,
            topics=list(set(topics)),
            confidence=0.6,  # Lower confidence for regex
            extraction_time_ms=0  # Will be set by caller
        )

    async def batch_extract_entities(
        self,
        messages: List[Dict],
        batch_size: int = 10
    ) -> Dict[str, ExtractedEntities]:
        """
        Batch entity extraction for processing historical messages
        Used during system initialization or backfill operations
        """
        results = {}

        for i in range(0, len(messages), batch_size):
            batch = messages[i:i + batch_size]

            # Process batch in parallel
            tasks = []
            for msg in batch:
                task = self.extract_entities_fast(
                    msg.get('text', ''),
                    msg.get('user_id', ''),
                    msg.get('channel_id', '')
                )
                tasks.append((msg.get('message_id'), task))

            # Execute parallel extraction
            batch_results = await asyncio.gather(*[task for _, task in tasks])

            # Store results
            for (msg_id, _), entities in zip(tasks, batch_results):
                results[msg_id] = entities

            # Rate limiting to be nice to APIs
            await asyncio.sleep(0.1)

        logger.info(f"📝 Extracted entities for {len(results)} messages in batch")
        return results

class ContextMatcher:
    """
    Entity overlap scoring for context injection decisions
    Implements threshold-gated matching to prevent false positives
    """

    def __init__(self):
        # Synonym mapping for semantic relevance fallback
        self.synonym_map = {
            'thermal': ['heat', 'temperature', 'cooling', 'dissipation'],
            'power': ['supply', 'voltage', 'current', 'battery', 'electrical'],
            'motor': ['actuator', 'drive', 'stepper', 'servo'],
            'pcb': ['board', 'circuit', 'layout'],
            'firmware': ['software', 'code', 'programming'],
            'testing': ['validation', 'qa', 'verification']
        }

    def calculate_overlap_score(
        self,
        b_entities: ExtractedEntities,
        buffer_entities: List[ExtractedEntities]
    ) -> Tuple[str, float]:
        """
        Calculate confidence and score for context injection

        Returns: (confidence_level, numeric_score)
        confidence_level: 'high', 'medium', 'low', 'none'
        """
        if not buffer_entities:
            return 'none', 0.0

        # Aggregate all buffer entities
        all_buffer_reqs = set()
        all_buffer_components = set()
        all_buffer_topics = set()

        for entities in buffer_entities:
            all_buffer_reqs.update(entities.reqs)
            all_buffer_components.update(entities.components)
            all_buffer_topics.update(entities.topics)

        # Tier 1: REQ-ID exact match (highest confidence)
        b_reqs = set(b_entities.reqs)
        req_matches = len(b_reqs & all_buffer_reqs)
        if req_matches > 0:
            return 'high', float(req_matches * 2.0)  # Weight REQ matches highly

        # Tier 2: Component exact match (high confidence)
        b_components = set(b_entities.components)
        component_matches = len(b_components & all_buffer_components)
        if component_matches >= 2:
            return 'high', float(component_matches * 1.5)
        elif component_matches == 1:
            # Check if it's a core component (motor, pcb, firmware)
            core_components = {'motor', 'pcb', 'firmware', 'power_supply'}
            if b_components & core_components & all_buffer_components:
                return 'high', 1.5
            return 'medium', 1.0

        # Tier 3: Topic overlap (medium confidence)
        b_topics = set(b_entities.topics)
        topic_matches = len(b_topics & all_buffer_topics)
        if topic_matches >= 2:
            return 'medium', float(topic_matches * 0.8)

        # Tier 4: Synonym matching (low-medium confidence)
        synonym_score = self._calculate_synonym_overlap(
            b_components, all_buffer_components
        )
        if synonym_score >= 0.6:
            return 'medium', synonym_score

        return 'none', 0.0

    def _calculate_synonym_overlap(
        self,
        b_components: Set[str],
        buffer_components: Set[str]
    ) -> float:
        """Calculate semantic similarity using synonym mapping"""
        matches = 0
        total_comparisons = 0

        for b_comp in b_components:
            for buf_comp in buffer_components:
                total_comparisons += 1

                # Direct match
                if b_comp == buf_comp:
                    matches += 1
                    continue

                # Synonym check
                b_synonyms = self.synonym_map.get(b_comp, [])
                buf_synonyms = self.synonym_map.get(buf_comp, [])

                if (buf_comp in b_synonyms or
                    b_comp in buf_synonyms or
                    bool(set(b_synonyms) & set(buf_synonyms))):
                    matches += 0.7  # Partial credit for synonyms

        return matches / max(total_comparisons, 1)

    def should_inject_context(
        self,
        b_entities: ExtractedEntities,
        buffer_entities: List[ExtractedEntities],
        confidence_threshold: str = 'medium'
    ) -> Tuple[bool, str, float]:
        """
        Determine if context should be injected based on overlap

        Returns: (should_inject, confidence_level, score)
        """
        # Guard: No entities extracted from B's message
        if (not b_entities.reqs and
            not b_entities.components and
            not b_entities.topics):
            return False, 'none', 0.0

        # Calculate overlap
        confidence, score = self.calculate_overlap_score(b_entities, buffer_entities)

        # Apply threshold
        confidence_levels = {'high': 3, 'medium': 2, 'low': 1, 'none': 0}
        threshold_levels = {'high': 3, 'medium': 2, 'low': 1}

        required_level = threshold_levels.get(confidence_threshold, 2)
        actual_level = confidence_levels.get(confidence, 0)

        should_inject = actual_level >= required_level and score > 0

        return should_inject, confidence, score

# Testing and example usage
if __name__ == "__main__":
    import asyncio

    async def test_entity_extraction():
        """Test entity extraction functionality"""
        extractor = RealtimeEntityExtractor()

        # Test messages
        test_messages = [
            "Motor torque spec needs to increase to 2.8Nm for REQ-245",
            "@alice can you check the PCB thermal analysis?",
            "The firmware security module passes validation",
            "Need CAN bus protocol review by @bob and @erik"
        ]

        for msg in test_messages:
            entities = await extractor.extract_entities_fast(msg, "test_user", "test_channel")
            print(f"Message: {msg}")
            print(f"Entities: {entities}")
            print(f"Extraction time: {entities.extraction_time_ms:.1f}ms\n")

        # Test context matching
        matcher = ContextMatcher()

        # Simulate B's entities and buffer context
        b_entities = ExtractedEntities(
            reqs=["REQ-245"],
            components=["motor"],
            users_mentioned=[],
            topics=["torque_specs"],
            confidence=0.9,
            extraction_time_ms=150
        )

        buffer_entities = [
            ExtractedEntities(
                reqs=["REQ-245", "REQ-246"],
                components=["motor", "power_supply"],
                users_mentioned=["@alice"],
                topics=["torque_specs", "power_requirements"],
                confidence=0.8,
                extraction_time_ms=200
            )
        ]

        should_inject, confidence, score = matcher.should_inject_context(
            b_entities, buffer_entities
        )

        print(f"Context injection decision:")
        print(f"Should inject: {should_inject}")
        print(f"Confidence: {confidence}")
        print(f"Score: {score}")

    # Run test
    asyncio.run(test_entity_extraction())