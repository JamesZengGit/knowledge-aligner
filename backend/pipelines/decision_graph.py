"""Build decision graphs to track relationships and impacts."""

from typing import List, Dict, Set, Tuple
import re
from datetime import datetime, timedelta
from src.models import Decision, DecisionRelationship, RelationshipType

class DecisionGraphBuilder:
    def __init__(self):
        self.component_dependencies = {
            # Hardware dependencies
            'Motor-XYZ': ['Bracket-Assembly', 'Power-Supply-v2'],
            'PCB-Rev3': ['Power-Supply-v2', 'ESP32-Firmware', 'I2C-Interface'],
            'Power-Supply-v2': ['Thermal-Design', 'Schematic'],
            'ESP32-Firmware': ['Bootloader', 'Driver-Code'],
            'Enclosure': ['Thermal-Design', 'Assembly-Process'],

            # Process dependencies
            'BOM': ['Vendor-Selection', 'DFM'],
            'Requirements': ['Schedule'],
            'Test-Fixtures': ['QA-Process'],
        }

        self.user_expertise = {
            'alice': ['Motor-XYZ', 'Bracket-Assembly', 'mechanical'],
            'bob': ['ESP32-Firmware', 'Bootloader', 'firmware'],
            'carol': ['BOM', 'Vendor-Selection', 'supply-chain'],
            'dave': ['PCB-Rev3', 'Power-Supply-v2', 'hardware'],
            'eve': ['Requirements', 'Schedule', 'project-management'],
            'frank': ['Test-Fixtures', 'QA-Process', 'testing'],
            'grace': ['Enclosure', 'Thermal-Design', 'thermal'],
            'henry': ['Driver-Code', 'I2C-Interface', 'firmware'],
            'iris': ['Schematic', 'Layout', 'electrical'],
            'jack': ['Assembly-Process', 'DFM', 'manufacturing'],
        }

    def build_relationships(self, decisions: List[Decision]) -> List[DecisionRelationship]:
        """Build relationships between decisions based on content analysis."""
        relationships = []

        # Sort decisions by timestamp for temporal analysis
        sorted_decisions = sorted(decisions, key=lambda x: x.timestamp)

        for i, decision in enumerate(sorted_decisions):
            # Look for relationships with previous decisions
            for j, other_decision in enumerate(sorted_decisions[:i]):
                rel = self._analyze_relationship(decision, other_decision)
                if rel:
                    relationships.append(rel)

        return relationships

    def _analyze_relationship(self, decision1: Decision, decision2: Decision) -> DecisionRelationship:
        """Analyze relationship between two decisions."""
        # Component overlap indicates potential impact
        shared_components = set(decision1.affected_components) & set(decision2.affected_components)

        if shared_components:
            confidence = len(shared_components) / max(len(decision1.affected_components), len(decision2.affected_components))

            # Determine relationship type
            rel_type = self._determine_relationship_type(decision1, decision2, shared_components)

            if rel_type:
                return DecisionRelationship(
                    source_decision_id=decision1.decision_id,
                    target_decision_id=decision2.decision_id,
                    relationship_type=rel_type,
                    confidence=confidence
                )

        # Check for requirement references
        shared_reqs = set(decision1.referenced_reqs) & set(decision2.referenced_reqs)
        if shared_reqs:
            return DecisionRelationship(
                source_decision_id=decision1.decision_id,
                target_decision_id=decision2.decision_id,
                relationship_type=RelationshipType.REFERENCES,
                confidence=0.8
            )

        # Check for dependency chain
        if self._has_dependency_relationship(decision1, decision2):
            return DecisionRelationship(
                source_decision_id=decision1.decision_id,
                target_decision_id=decision2.decision_id,
                relationship_type=RelationshipType.DEPENDS_ON,
                confidence=0.7
            )

        return None

    def _determine_relationship_type(self, decision1: Decision, decision2: Decision, shared_components: Set[str]) -> RelationshipType:
        """Determine the specific relationship type between decisions."""

        # Check for explicit conflicts
        if self._has_conflict(decision1, decision2):
            return RelationshipType.CONFLICTS_WITH

        # Check for impacts based on timestamp and content
        if decision1.timestamp > decision2.timestamp:
            # Later decision potentially impacts earlier one
            if any(comp in self._get_dependent_components(decision2.affected_components)
                   for comp in decision1.affected_components):
                return RelationshipType.IMPACTS

        # Check for references
        if any(req in decision1.decision_text for req in decision2.referenced_reqs):
            return RelationshipType.REFERENCES

        # Default to impact relationship for shared components
        return RelationshipType.IMPACTS

    def _has_conflict(self, decision1: Decision, decision2: Decision) -> bool:
        """Check if two decisions conflict with each other."""

        # Look for contradictory before/after changes
        text1_lower = decision1.decision_text.lower()
        text2_lower = decision2.decision_text.lower()

        # Simple conflict detection - opposite decisions on same component
        conflict_patterns = [
            ('approved', 'rejected'),
            ('increased', 'decreased'),
            ('added', 'removed'),
            ('enabled', 'disabled'),
        ]

        shared_components = set(decision1.affected_components) & set(decision2.affected_components)
        if shared_components:
            for pos_word, neg_word in conflict_patterns:
                if (pos_word in text1_lower and neg_word in text2_lower) or \
                   (neg_word in text1_lower and pos_word in text2_lower):
                    return True

        return False

    def _has_dependency_relationship(self, decision1: Decision, decision2: Decision) -> bool:
        """Check if decision1 depends on decision2."""

        # Check component dependencies
        for comp1 in decision1.affected_components:
            for comp2 in decision2.affected_components:
                if comp2 in self.component_dependencies.get(comp1, []):
                    return True

        return False

    def _get_dependent_components(self, components: List[str]) -> List[str]:
        """Get all components that depend on the given components."""
        dependents = []
        for comp in components:
            for dependent, dependencies in self.component_dependencies.items():
                if comp in dependencies:
                    dependents.append(dependent)
        return dependents

    def detect_missing_stakeholders(self, decision: Decision, all_users: Dict[str, List[str]]) -> List[str]:
        """Detect users who should have been involved in a decision but weren't."""
        missing = []

        # Get users who own affected components
        for component in decision.affected_components:
            for user_id, user_components in all_users.items():
                if component in user_components and user_id != decision.author_user_id:
                    missing.append(user_id)

        # Get users with relevant expertise
        decision_keywords = decision.decision_text.lower().split()
        for user_id, expertise in self.user_expertise.items():
            if user_id != decision.author_user_id:
                if any(keyword in decision_keywords for keyword in expertise):
                    missing.append(user_id)

        return list(set(missing))  # Remove duplicates

    def analyze_impact_scope(self, decision: Decision) -> Dict[str, List[str]]:
        """Analyze the full scope of impact for a decision."""
        impacts = {
            'direct_components': decision.affected_components.copy(),
            'dependent_components': [],
            'affected_teams': [],
            'required_approvals': []
        }

        # Find dependent components
        for comp in decision.affected_components:
            impacts['dependent_components'].extend(
                self._get_dependent_components([comp])
            )

        # Determine affected teams based on components
        all_affected = impacts['direct_components'] + impacts['dependent_components']
        for user_id, user_components in self.user_expertise.items():
            if any(comp in user_components for comp in all_affected):
                impacts['affected_teams'].append(user_id)

        # Determine required approvals based on decision type and scope
        if decision.decision_type.value == 'requirement_change':
            impacts['required_approvals'].extend(['eve'])  # PM always needed

        if len(impacts['direct_components']) > 2:
            impacts['required_approvals'].extend(['dave'])  # Hardware lead for complex changes

        return impacts