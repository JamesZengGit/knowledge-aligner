"""Gap detection for missing stakeholders and conflicting decisions."""

import os
import psycopg2
import psycopg2.extras
from typing import List, Dict, Tuple, Set
from datetime import datetime, timedelta
from src.decision_graph import DecisionGraphBuilder
from src.models import Decision, RelationshipType
import logging

class GapDetector:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        self.graph_builder = DecisionGraphBuilder()

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def detect_all_gaps(self, days_back: int = 30) -> Dict[str, List[Dict]]:
        """Detect all types of gaps in recent decisions."""

        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

                # Get recent decisions
                decisions = self._get_recent_decisions(cursor, days_back)

                if not decisions:
                    return {"missing_stakeholders": [], "conflicts": [], "broken_dependencies": []}

                # Detect different types of gaps
                gaps = {
                    "missing_stakeholders": self._detect_missing_stakeholders(cursor, decisions),
                    "conflicts": self._detect_conflicts(cursor, decisions),
                    "broken_dependencies": self._detect_broken_dependencies(cursor, decisions)
                }

                return gaps

        except Exception as e:
            self.logger.error(f"Gap detection failed: {e}")
            raise

    def _get_recent_decisions(self, cursor, days_back: int) -> List[Dict]:
        """Get recent decisions for analysis."""

        query = """
        SELECT
            d.decision_id,
            d.thread_id,
            d.timestamp,
            d.author_user_id,
            d.decision_type,
            d.decision_text,
            d.affected_components,
            d.referenced_reqs,
            u.user_name,
            u.role
        FROM decisions d
        JOIN user_profiles u ON d.author_user_id = u.user_id
        WHERE d.timestamp >= %s
        ORDER BY d.timestamp DESC
        """

        cursor.execute(query, (datetime.now() - timedelta(days=days_back),))
        return [dict(row) for row in cursor.fetchall()]

    def _detect_missing_stakeholders(self, cursor, decisions: List[Dict]) -> List[Dict]:
        """Detect decisions where key stakeholders were missing from discussions."""

        missing_stakeholders = []

        # Get all user profiles and their components
        cursor.execute("SELECT user_id, user_name, role, owned_components FROM user_profiles")
        users = {row['user_id']: dict(row) for row in cursor.fetchall()}

        for decision in decisions:
            decision_id = decision['decision_id']
            thread_id = decision['thread_id']
            affected_components = decision['affected_components']

            # Find users who own affected components
            component_owners = []
            for component in affected_components:
                for user_id, user_data in users.items():
                    if component in user_data['owned_components']:
                        component_owners.append((user_id, user_data['user_name'], component))

            # Check who actually participated in the thread
            cursor.execute(
                "SELECT DISTINCT user_id FROM slack_messages WHERE thread_id = %s",
                (thread_id,)
            )
            participants = {row['user_id'] for row in cursor.fetchall()}

            # Find missing stakeholders
            missing = []
            for user_id, user_name, component in component_owners:
                if user_id not in participants and user_id != decision['author_user_id']:
                    missing.append({
                        'user_id': user_id,
                        'user_name': user_name,
                        'owned_component': component,
                        'role': users[user_id]['role']
                    })

            if missing:
                # Check severity - critical if >2 stakeholders missing or hardware lead missing
                severity = "critical" if (
                    len(missing) > 2 or
                    any(users[m['user_id']]['role'].endswith('Lead') for m in missing)
                ) else "warning"

                missing_stakeholders.append({
                    'decision_id': decision_id,
                    'decision_text': decision['decision_text'][:100] + "...",
                    'thread_id': thread_id,
                    'timestamp': decision['timestamp'],
                    'author': decision['user_name'],
                    'affected_components': affected_components,
                    'missing_stakeholders': missing,
                    'severity': severity,
                    'participants_count': len(participants),
                    'recommendation': self._generate_stakeholder_recommendation(missing, affected_components)
                })

        # Sort by severity and timestamp
        missing_stakeholders.sort(key=lambda x: (x['severity'] == 'warning', x['timestamp']), reverse=True)

        return missing_stakeholders

    def _detect_conflicts(self, cursor, decisions: List[Dict]) -> List[Dict]:
        """Detect conflicting decisions across components and requirements."""

        conflicts = []

        # Group decisions by components and requirements
        component_decisions = {}
        requirement_decisions = {}

        for decision in decisions:
            # Group by components
            for component in decision['affected_components']:
                if component not in component_decisions:
                    component_decisions[component] = []
                component_decisions[component].append(decision)

            # Group by requirements
            for req in decision['referenced_reqs']:
                if req not in requirement_decisions:
                    requirement_decisions[req] = []
                requirement_decisions[req].append(decision)

        # Detect component conflicts
        for component, comp_decisions in component_decisions.items():
            if len(comp_decisions) > 1:
                component_conflicts = self._analyze_component_conflicts(component, comp_decisions)
                conflicts.extend(component_conflicts)

        # Detect requirement conflicts
        for req, req_decisions in requirement_decisions.items():
            if len(req_decisions) > 1:
                req_conflicts = self._analyze_requirement_conflicts(req, req_decisions)
                conflicts.extend(req_conflicts)

        # Sort by severity and timestamp
        conflicts.sort(key=lambda x: (x['severity'] == 'warning', x['timestamp']), reverse=True)

        return conflicts

    def _analyze_component_conflicts(self, component: str, decisions: List[Dict]) -> List[Dict]:
        """Analyze conflicts within decisions affecting the same component."""
        conflicts = []

        # Look for contradictory decision types
        decision_types = [d['decision_type'] for d in decisions]
        timestamps = [d['timestamp'] for d in decisions]

        # Check for approval followed by rejection or vice versa
        has_approval = any('approval' in dt for dt in decision_types)
        has_rejection = any('reject' in d['decision_text'].lower() for d in decisions)

        if has_approval and has_rejection:
            conflicts.append({
                'type': 'component_conflict',
                'component': component,
                'conflict_description': f'Conflicting approval/rejection decisions for {component}',
                'decisions': [self._format_decision_summary(d) for d in decisions],
                'severity': 'critical',
                'timestamp': max(timestamps),
                'resolution_needed': True,
                'recommendation': f'Clarify current status of {component} - approved or rejected?'
            })

        # Check for contradictory before/after values
        before_after_conflicts = self._detect_before_after_conflicts(decisions)
        for conflict in before_after_conflicts:
            conflict['component'] = component
            conflicts.append(conflict)

        # Check for timeline conflicts (same change decided multiple times)
        if len(set(d['decision_text'] for d in decisions)) < len(decisions):
            recent_window = max(timestamps) - timedelta(hours=24)
            recent_decisions = [d for d in decisions if d['timestamp'] > recent_window]

            if len(recent_decisions) > 1:
                conflicts.append({
                    'type': 'duplicate_decision',
                    'component': component,
                    'conflict_description': f'Multiple recent decisions for {component} may indicate confusion',
                    'decisions': [self._format_decision_summary(d) for d in recent_decisions],
                    'severity': 'warning',
                    'timestamp': max(timestamps),
                    'resolution_needed': False,
                    'recommendation': f'Verify that latest decision for {component} is understood by all stakeholders'
                })

        return conflicts

    def _analyze_requirement_conflicts(self, requirement: str, decisions: List[Dict]) -> List[Dict]:
        """Analyze conflicts within decisions referencing the same requirement."""
        conflicts = []

        if len(decisions) <= 1:
            return conflicts

        # Sort by timestamp
        sorted_decisions = sorted(decisions, key=lambda x: x['timestamp'])

        # Look for changes that contradict previous decisions
        for i in range(1, len(sorted_decisions)):
            current = sorted_decisions[i]
            previous = sorted_decisions[i-1]

            # Simple text analysis for contradictions
            current_text = current['decision_text'].lower()
            previous_text = previous['decision_text'].lower()

            contradiction_patterns = [
                ('increase', 'decrease'),
                ('add', 'remove'),
                ('enable', 'disable'),
                ('approve', 'reject'),
                ('accept', 'decline')
            ]

            for pos_word, neg_word in contradiction_patterns:
                if ((pos_word in current_text and neg_word in previous_text) or
                    (neg_word in current_text and pos_word in previous_text)):

                    time_diff = current['timestamp'] - previous['timestamp']
                    severity = 'critical' if time_diff.days < 1 else 'warning'

                    conflicts.append({
                        'type': 'requirement_conflict',
                        'requirement': requirement,
                        'conflict_description': f'Contradictory decisions for {requirement}',
                        'decisions': [
                            self._format_decision_summary(previous),
                            self._format_decision_summary(current)
                        ],
                        'severity': severity,
                        'timestamp': current['timestamp'],
                        'resolution_needed': True,
                        'recommendation': f'Resolve contradictory requirements for {requirement}',
                        'time_between_decisions': f"{time_diff.days} days"
                    })

        return conflicts

    def _detect_before_after_conflicts(self, decisions: List[Dict]) -> List[Dict]:
        """Detect conflicts in before/after value changes."""
        conflicts = []

        # Extract before/after patterns from each decision
        changes = []
        for decision in decisions:
            text = decision['decision_text']
            # Simple regex to find "X to Y" or "X → Y" patterns
            import re
            patterns = re.findall(r'(\w+(?:\.\w+)*)\s*(?:to|→)\s*(\w+(?:\.\w+)*)', text, re.IGNORECASE)

            for before, after in patterns:
                changes.append({
                    'decision': decision,
                    'before': before.lower(),
                    'after': after.lower(),
                    'timestamp': decision['timestamp']
                })

        # Look for conflicting changes
        if len(changes) > 1:
            for i, change1 in enumerate(changes):
                for change2 in changes[i+1:]:
                    # Check for circular changes (A→B, then B→A)
                    if (change1['before'] == change2['after'] and
                        change1['after'] == change2['before']):

                        conflicts.append({
                            'type': 'circular_change',
                            'conflict_description': f'Circular changes detected: {change1["before"]} ↔ {change1["after"]}',
                            'decisions': [
                                self._format_decision_summary(change1['decision']),
                                self._format_decision_summary(change2['decision'])
                            ],
                            'severity': 'critical',
                            'timestamp': max(change1['timestamp'], change2['timestamp']),
                            'resolution_needed': True,
                            'recommendation': 'Clarify final value and reasoning for the change'
                        })

        return conflicts

    def _detect_broken_dependencies(self, cursor, decisions: List[Dict]) -> List[Dict]:
        """Detect decisions that may break component dependencies."""

        broken_deps = []

        # Get component dependencies from graph builder
        dependencies = self.graph_builder.component_dependencies

        for decision in decisions:
            for component in decision['affected_components']:
                # Check if this component has dependents
                dependents = []
                for dependent, deps in dependencies.items():
                    if component in deps:
                        dependents.append(dependent)

                if dependents:
                    # Check if dependent owners were involved
                    thread_id = decision['thread_id']

                    # Get thread participants
                    cursor.execute(
                        "SELECT DISTINCT user_id FROM slack_messages WHERE thread_id = %s",
                        (thread_id,)
                    )
                    participants = {row['user_id'] for row in cursor.fetchall()}

                    # Get owners of dependent components
                    cursor.execute(
                        "SELECT user_id, user_name, owned_components FROM user_profiles"
                    )
                    users = cursor.fetchall()

                    missing_dependent_owners = []
                    for user in users:
                        user_components = user['owned_components']
                        for dependent in dependents:
                            if dependent in user_components and user['user_id'] not in participants:
                                missing_dependent_owners.append({
                                    'user_id': user['user_id'],
                                    'user_name': user['user_name'],
                                    'dependent_component': dependent
                                })

                    if missing_dependent_owners:
                        broken_deps.append({
                            'decision_id': decision['decision_id'],
                            'decision_text': decision['decision_text'][:100] + "...",
                            'affected_component': component,
                            'dependent_components': dependents,
                            'missing_owners': missing_dependent_owners,
                            'timestamp': decision['timestamp'],
                            'severity': 'warning',
                            'recommendation': f'Inform owners of {", ".join(dependents)} about changes to {component}'
                        })

        return broken_deps

    def _format_decision_summary(self, decision: Dict) -> Dict:
        """Format decision for conflict display."""
        return {
            'decision_id': decision['decision_id'],
            'author': decision['user_name'],
            'timestamp': decision['timestamp'].isoformat(),
            'text': decision['decision_text'][:100] + "...",
            'type': decision['decision_type']
        }

    def _generate_stakeholder_recommendation(self, missing: List[Dict], components: List[str]) -> str:
        """Generate recommendation for missing stakeholder gaps."""
        if len(missing) == 1:
            return f"Contact {missing[0]['user_name']} ({missing[0]['role']}) about {missing[0]['owned_component']} impact"
        else:
            roles = ", ".join(set(m['role'] for m in missing))
            return f"Schedule review meeting with {roles} teams to discuss {', '.join(components)} changes"

    def generate_gap_report(self, gaps: Dict[str, List[Dict]]) -> str:
        """Generate formatted gap report for CLI display."""
        output = []

        output.append("=" * 80)
        output.append("GAP DETECTION REPORT")
        output.append("=" * 80)

        # Missing Stakeholders
        if gaps['missing_stakeholders']:
            output.append(f"\n👥 MISSING STAKEHOLDERS ({len(gaps['missing_stakeholders'])})")
            output.append("-" * 40)

            for gap in gaps['missing_stakeholders']:
                severity_icon = "🔴" if gap['severity'] == 'critical' else "🟡"
                output.append(f"\n{severity_icon} Decision DEC-{gap['decision_id']:03d}")
                output.append(f"   Author: {gap['author']}")
                output.append(f"   Time: {gap['timestamp'].strftime('%Y-%m-%d %H:%M')}")
                output.append(f"   Components: {', '.join(gap['affected_components'])}")
                output.append(f"   Missing: {', '.join(m['user_name'] + ' (' + m['role'] + ')' for m in gap['missing_stakeholders'])}")
                output.append(f"   💡 {gap['recommendation']}")

        # Conflicts
        if gaps['conflicts']:
            output.append(f"\n⚡ CONFLICTS DETECTED ({len(gaps['conflicts'])})")
            output.append("-" * 40)

            for conflict in gaps['conflicts']:
                severity_icon = "🔴" if conflict['severity'] == 'critical' else "🟡"
                output.append(f"\n{severity_icon} {conflict['type'].replace('_', ' ').title()}")
                output.append(f"   Description: {conflict['conflict_description']}")
                if 'component' in conflict:
                    output.append(f"   Component: {conflict['component']}")
                if 'requirement' in conflict:
                    output.append(f"   Requirement: {conflict['requirement']}")
                output.append(f"   Decisions: {len(conflict['decisions'])} conflicting decisions")
                output.append(f"   💡 {conflict['recommendation']}")

        # Broken Dependencies
        if gaps['broken_dependencies']:
            output.append(f"\n🔗 BROKEN DEPENDENCIES ({len(gaps['broken_dependencies'])})")
            output.append("-" * 40)

            for dep in gaps['broken_dependencies']:
                output.append(f"\n🟡 Decision DEC-{dep['decision_id']:03d}")
                output.append(f"   Component: {dep['affected_component']}")
                output.append(f"   Affects: {', '.join(dep['dependent_components'])}")
                output.append(f"   Missing owners: {', '.join(m['user_name'] for m in dep['missing_owners'])}")
                output.append(f"   💡 {dep['recommendation']}")

        if not any(gaps.values()):
            output.append("\n✅ No gaps detected in recent decisions!")

        output.append("\n" + "=" * 80)

        return "\n".join(output)