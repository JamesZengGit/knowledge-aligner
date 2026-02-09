export interface User {
  user_id: string;
  user_name: string;
  role: string;
  owned_components: string[];
  email: string;
}

export interface Decision {
  decision_id: number;
  thread_id: string;
  timestamp: string;
  author_user_id: string;
  author_name: string;
  author_role: string;
  decision_type: 'requirement_change' | 'design_decision' | 'approval';
  decision_text: string;
  affected_components: string[];
  referenced_reqs: string[];
  similarity_score?: number;
  before_after?: {
    before: string;
    after: string;
  };
  relationships?: DecisionRelationship[];
  gaps_detected?: Gap[];
}

export interface DecisionRelationship {
  relationship_type: 'IMPACTS' | 'REFERENCES' | 'CONFLICTS_WITH' | 'DEPENDS_ON';
  target_decision_id: number;
  confidence: number;
}

export interface DigestEntry {
  decision_id: string;
  title: string;
  summary: string;
  impact_summary: string;
  before_after?: {
    before: string;
    after: string;
  };
  affected_components: string[];
  citations: string[];
  timestamp: string;
}

export interface PersonalizedDigest {
  user_id: string;
  date: string;
  summary: string;
  themes: string[];
  entries: DigestEntry[];
  gaps_detected: string[];
  action_items: string[];
}

export interface Gap {
  type: 'missing_stakeholder' | 'conflict' | 'broken_dependency';
  severity: 'critical' | 'warning';
  description: string;
  decision_id?: number;
  recommendation: string;
  timestamp: string;
  priority?: number; // 1-10, higher = more urgent
}

export interface SearchFilters {
  user_id?: string;
  components?: string[];
  decision_types?: string[];
  time_range_days?: number;
}

export interface UserPreferences {
  density: 'compact' | 'comfortable' | 'spacious';
  priorityComponents: string[];
  alertThreshold: 'critical' | 'warning' | 'all';
  role: string;
}