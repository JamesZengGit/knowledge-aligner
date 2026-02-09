"""Generate personalized digests in REQ-245 style using Claude Sonnet."""

import os
import json
import anthropic
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.models import PersonalizedDigest, DigestEntry
from src.retrieval import HybridRetriever
from src.decision_graph import DecisionGraphBuilder
from dotenv import load_dotenv
import logging

load_dotenv()

class DigestGenerator:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.retriever = HybridRetriever()
        self.graph_builder = DecisionGraphBuilder()

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    async def generate_personalized_digest(
        self,
        user_id: str,
        date: datetime,
        days_back: int = 7
    ) -> PersonalizedDigest:
        """Generate a personalized digest for a user covering recent decisions."""

        try:
            # Get user profile for context
            user_profile = self._get_user_profile(user_id)
            if not user_profile:
                raise ValueError(f"User {user_id} not found")

            # Retrieve relevant decisions for the user
            end_date = date
            start_date = date - timedelta(days=days_back)

            relevant_decisions = self.retriever.search_decisions(
                query="",  # No specific query, get all relevant
                user_id=user_id,
                time_range_days=days_back,
                limit=50
            )

            if not relevant_decisions:
                return PersonalizedDigest(
                    user_id=user_id,
                    date=date,
                    summary="No relevant decisions found for this period.",
                    themes=[],
                    entries=[],
                    gaps_detected=[],
                    action_items=[]
                )

            # Generate digest using Claude Sonnet
            digest_content = await self._generate_digest_with_claude(
                user_profile, relevant_decisions, start_date, end_date
            )

            # Detect gaps and conflicts
            gaps = self._detect_gaps(user_id, relevant_decisions)

            return PersonalizedDigest(
                user_id=user_id,
                date=date,
                summary=digest_content["summary"],
                themes=digest_content["themes"],
                entries=digest_content["entries"],
                gaps_detected=gaps,
                action_items=digest_content["action_items"]
            )

        except Exception as e:
            self.logger.error(f"Failed to generate digest for {user_id}: {e}")
            raise

    async def _generate_digest_with_claude(
        self,
        user_profile: Dict,
        decisions: List[Dict],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Use Claude Sonnet to generate structured digest content."""

        # Prepare context about the user
        user_context = f"""
User: {user_profile['user_name']} ({user_profile['role']})
Owned Components: {', '.join(user_profile['owned_components'])}
Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
"""

        # Prepare decisions data
        decisions_context = self._format_decisions_for_claude(decisions)

        prompt = f"""Generate a personalized hardware engineering digest in the style of EverCurrent's REQ-245 format.

{user_context}

Recent Decisions:
{decisions_context}

Generate a digest that includes:

1. SUMMARY: 2-3 sentence overview of key decisions affecting this user
2. THEMES: 3-5 major themes or topics from the decisions
3. ENTRIES: Detailed entries for each significant decision with:
   - REQ-245 style title with decision ID (use DEC-XXX format)
   - Impact summary specifically for this user's components
   - Before/after changes when applicable (15nm → 22nm style)
   - Citations to original Slack threads
   - Affected components with emphasis on user's owned components

4. ACTION_ITEMS: Specific actions this user should take based on decisions

Focus on:
- Proactive insights: How decisions impact user's work
- Decision traceability: Clear links between decisions and requirements
- Cross-functional impact: How decisions affect other teams
- Missing context: Decisions that may need user's input

Format as JSON:
{
    "summary": "Overview text",
    "themes": ["Theme 1", "Theme 2", ...],
    "entries": [
        {
            "decision_id": "DEC-001",
            "title": "REQ-245 style title",
            "summary": "Decision summary",
            "impact_summary": "Specific impact on user's components",
            "before_after": {"before": "old_value", "after": "new_value"} or null,
            "affected_components": ["Component1", "Component2"],
            "citations": ["#channel thread_id timestamp"],
            "timestamp": "ISO timestamp"
        }
    ],
    "action_items": ["Action 1", "Action 2", ...]
}"""

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse JSON response
            digest_data = json.loads(response.content[0].text)

            # Convert entries to DigestEntry objects
            entries = []
            for entry_data in digest_data.get("entries", []):
                entry = DigestEntry(
                    decision_id=entry_data.get("decision_id", "DEC-000"),
                    title=entry_data.get("title", ""),
                    summary=entry_data.get("summary", ""),
                    impact_summary=entry_data.get("impact_summary", ""),
                    before_after=entry_data.get("before_after"),
                    affected_components=entry_data.get("affected_components", []),
                    citations=entry_data.get("citations", []),
                    timestamp=datetime.fromisoformat(entry_data.get("timestamp", datetime.now().isoformat()))
                )
                entries.append(entry)

            return {
                "summary": digest_data.get("summary", ""),
                "themes": digest_data.get("themes", []),
                "entries": entries,
                "action_items": digest_data.get("action_items", [])
            }

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Claude response as JSON: {e}")
            # Fallback to basic digest
            return self._generate_fallback_digest(user_profile, decisions)

        except Exception as e:
            self.logger.error(f"Claude digest generation failed: {e}")
            return self._generate_fallback_digest(user_profile, decisions)

    def _format_decisions_for_claude(self, decisions: List[Dict]) -> str:
        """Format decisions data for Claude prompt."""
        formatted = []

        for i, decision in enumerate(decisions[:20]):  # Limit to most relevant
            # Extract before/after changes from decision text
            before_after = self._extract_before_after(decision['decision_text'])

            formatted_decision = f"""
Decision {i+1}:
- ID: {decision['decision_id']}
- Author: {decision['author_name']} ({decision['author_role']})
- Type: {decision['decision_type']}
- Timestamp: {decision['timestamp']}
- Thread: {decision['thread_id']}
- Text: {decision['decision_text']}
- Components: {', '.join(decision['affected_components'])}
- Requirements: {', '.join(decision['referenced_reqs'])}
- Similarity: {decision['similarity_score']:.2f}
"""

            if before_after:
                formatted_decision += f"- Changes: {before_after}\n"

            if decision.get('relationships'):
                rel_info = []
                for rel in decision['relationships'][:3]:  # Top 3 relationships
                    rel_info.append(f"{rel['relationship_type']} (confidence: {rel['confidence']:.2f})")
                formatted_decision += f"- Relationships: {', '.join(rel_info)}\n"

            formatted.append(formatted_decision)

        return "\n".join(formatted)

    def _extract_before_after(self, text: str) -> Optional[str]:
        """Extract before/after patterns from decision text."""
        import re

        # Look for various before/after patterns
        patterns = [
            r'(\w+(?:\.\w+)*(?:\s*\w+)*)\s*(?:→|->|to)\s*(\w+(?:\.\w+)*(?:\s*\w+)*)',
            r'from\s+(\w+(?:\.\w+)*(?:\s*\w+)*)\s+to\s+(\w+(?:\.\w+)*(?:\s*\w+)*)',
            r'changing\s+from\s+(\w+(?:\.\w+)*(?:\s*\w+)*)\s+to\s+(\w+(?:\.\w+)*(?:\s*\w+)*)',
            r'(\w+(?:\.\w+)*(?:\s*\w+)*)\s+→\s+(\w+(?:\.\w+)*(?:\s*\w+)*)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"{match.group(1)} → {match.group(2)}"

        return None

    def _generate_fallback_digest(self, user_profile: Dict, decisions: List[Dict]) -> Dict[str, Any]:
        """Generate a basic digest when Claude fails."""
        # Group decisions by type
        by_type = {}
        for decision in decisions:
            dec_type = decision['decision_type']
            if dec_type not in by_type:
                by_type[dec_type] = []
            by_type[dec_type].append(decision)

        # Generate basic themes
        themes = []
        if 'requirement_change' in by_type:
            themes.append("Requirement Changes")
        if 'design_decision' in by_type:
            themes.append("Design Decisions")
        if 'approval' in by_type:
            themes.append("Approvals")

        # Generate basic entries
        entries = []
        for i, decision in enumerate(decisions[:10]):
            before_after_text = self._extract_before_after(decision['decision_text'])
            before_after = None
            if before_after_text:
                parts = before_after_text.split(' → ')
                if len(parts) == 2:
                    before_after = {"before": parts[0], "after": parts[1]}

            entry = DigestEntry(
                decision_id=f"DEC-{decision['decision_id']:03d}",
                title=f"{decision['decision_type'].replace('_', ' ').title()}: {decision['decision_text'][:50]}...",
                summary=decision['decision_text'],
                impact_summary=f"Affects {', '.join(decision['affected_components'])}",
                before_after=before_after,
                affected_components=decision['affected_components'],
                citations=[f"#{decision['thread_id']}"],
                timestamp=decision['timestamp']
            )
            entries.append(entry)

        return {
            "summary": f"Found {len(decisions)} decisions affecting your components in the last week.",
            "themes": themes,
            "entries": entries,
            "action_items": ["Review decisions affecting your components", "Follow up on pending approvals"]
        }

    def _detect_gaps(self, user_id: str, decisions: List[Dict]) -> List[str]:
        """Detect gaps like missing stakeholders or conflicting decisions."""
        gaps = []

        # Get user's components for gap detection
        user_components = self._get_user_components(user_id)

        for decision in decisions:
            # Check if user should have been involved but wasn't
            if (set(decision['affected_components']) & set(user_components) and
                decision['author_user_id'] != user_id):

                # Check if this user was mentioned in thread
                if not self._user_mentioned_in_thread(user_id, decision['thread_id']):
                    gaps.append(
                        f"Decision DEC-{decision['decision_id']:03d} affects your components "
                        f"({', '.join(set(decision['affected_components']) & set(user_components))}) "
                        f"but you weren't included in the discussion"
                    )

        # Look for conflicting decisions
        component_decisions = {}
        for decision in decisions:
            for component in decision['affected_components']:
                if component not in component_decisions:
                    component_decisions[component] = []
                component_decisions[component].append(decision)

        for component, comp_decisions in component_decisions.items():
            if len(comp_decisions) > 1:
                # Check for potential conflicts (simple heuristic)
                if any('approved' in d['decision_text'].lower() for d in comp_decisions) and \
                   any('rejected' in d['decision_text'].lower() for d in comp_decisions):
                    gaps.append(f"Conflicting decisions detected for {component}")

        return gaps[:5]  # Limit to top 5 gaps

    def _get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile from database."""
        import psycopg2
        import psycopg2.extras

        try:
            with psycopg2.connect(os.getenv("DATABASE_URL")) as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute(
                    "SELECT user_id, user_name, role, owned_components, email FROM user_profiles WHERE user_id = %s",
                    (user_id,)
                )
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            self.logger.error(f"Failed to get user profile: {e}")
            return None

    def _get_user_components(self, user_id: str) -> List[str]:
        """Get components owned by user."""
        profile = self._get_user_profile(user_id)
        return profile['owned_components'] if profile else []

    def _user_mentioned_in_thread(self, user_id: str, thread_id: str) -> bool:
        """Check if user was mentioned or participated in thread."""
        import psycopg2

        try:
            with psycopg2.connect(os.getenv("DATABASE_URL")) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM slack_messages WHERE thread_id = %s AND user_id = %s",
                    (thread_id, user_id)
                )
                count = cursor.fetchone()[0]
                return count > 0
        except Exception:
            return False  # Conservative assumption

    def format_digest_for_display(self, digest: PersonalizedDigest) -> str:
        """Format digest for CLI display in REQ-245 style."""
        output = []

        # Header
        output.append("=" * 80)
        output.append(f"HARDWARE TEAM DIGEST - {digest.date.strftime('%Y-%m-%d')}")
        output.append(f"User: {digest.user_id}")
        output.append("=" * 80)

        # Summary
        output.append(f"\nSUMMARY")
        output.append("-" * 20)
        output.append(digest.summary)

        # Themes
        if digest.themes:
            output.append(f"\nKEY THEMES")
            output.append("-" * 20)
            for i, theme in enumerate(digest.themes, 1):
                output.append(f"{i}. {theme}")

        # Entries (REQ-245 style)
        if digest.entries:
            output.append(f"\nDECISION DETAILS")
            output.append("-" * 40)

            for entry in digest.entries:
                output.append(f"\n📋 {entry.title}")
                output.append(f"   ID: {entry.decision_id}")
                output.append(f"   Time: {entry.timestamp.strftime('%Y-%m-%d %H:%M')}")

                if entry.before_after:
                    output.append(f"   Change: {entry.before_after['before']} → {entry.before_after['after']}")

                output.append(f"   Impact: {entry.impact_summary}")
                output.append(f"   Components: {', '.join(entry.affected_components)}")

                if entry.citations:
                    output.append(f"   Citations: {', '.join(entry.citations)}")

                output.append("")

        # Action Items
        if digest.action_items:
            output.append(f"ACTION ITEMS")
            output.append("-" * 20)
            for i, action in enumerate(digest.action_items, 1):
                output.append(f"{i}. {action}")

        # Gaps Detected
        if digest.gaps_detected:
            output.append(f"\n⚠️  GAPS DETECTED")
            output.append("-" * 20)
            for i, gap in enumerate(digest.gaps_detected, 1):
                output.append(f"{i}. {gap}")

        output.append("\n" + "=" * 80)

        return "\n".join(output)