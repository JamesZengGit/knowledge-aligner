import { User, Decision, PersonalizedDigest, Gap } from '@/types';

export const mockUsers: User[] = [
  {
    user_id: 'alice',
    user_name: 'Alice Chen',
    role: 'Mechanical Lead',
    owned_components: ['Motor-XYZ', 'Bracket-Assembly'],
    email: 'alice@company.com'
  },
  {
    user_id: 'bob',
    user_name: 'Bob Wilson',
    role: 'Firmware Engineer',
    owned_components: ['ESP32-Firmware', 'Bootloader'],
    email: 'bob@company.com'
  },
  {
    user_id: 'dave',
    user_name: 'Dave Johnson',
    role: 'Hardware Lead',
    owned_components: ['PCB-Rev3', 'Power-Supply-v2'],
    email: 'dave@company.com'
  },
  {
    user_id: 'eve',
    user_name: 'Eve Martinez',
    role: 'PM',
    owned_components: ['Requirements', 'Schedule'],
    email: 'eve@company.com'
  }
];

export const mockDecisions: Decision[] = [
  {
    decision_id: 1,
    thread_id: 'thread_001',
    timestamp: '2026-02-01T14:30:00Z',
    author_user_id: 'eve',
    author_name: 'Eve Martinez',
    author_role: 'PM',
    decision_type: 'requirement_change',
    decision_text: 'REQ-245: Motor torque requirement changing from 15nm to 22nm based on customer load analysis. This affects Motor-XYZ and potentially Bracket-Assembly.',
    affected_components: ['Motor-XYZ', 'Bracket-Assembly'],
    referenced_reqs: ['REQ-245'],
    before_after: {
      before: '15nm',
      after: '22nm'
    },
    similarity_score: 0.95
  },
  {
    decision_id: 2,
    thread_id: 'thread_002',
    timestamp: '2026-02-02T09:15:00Z',
    author_user_id: 'alice',
    author_name: 'Alice Chen',
    author_role: 'Mechanical Lead',
    decision_type: 'design_decision',
    decision_text: 'Motor-XYZ redesign required for 22nm torque. Estimated 3-week timeline. Need to coordinate with supply chain for new motor specifications.',
    affected_components: ['Motor-XYZ'],
    referenced_reqs: ['REQ-245'],
    similarity_score: 0.87,
    relationships: [
      {
        relationship_type: 'IMPACTS',
        target_decision_id: 1,
        confidence: 0.9
      }
    ]
  },
  {
    decision_id: 3,
    thread_id: 'thread_003',
    timestamp: '2026-02-03T16:45:00Z',
    author_user_id: 'dave',
    author_name: 'Dave Johnson',
    author_role: 'Hardware Lead',
    decision_type: 'approval',
    decision_text: '✅ Approved PCB-Rev3 layout changes for improved thermal performance. Wall thickness increased from 2.5mm to 3.0mm.',
    affected_components: ['PCB-Rev3', 'Thermal-Design'],
    referenced_reqs: [],
    before_after: {
      before: '2.5mm',
      after: '3.0mm'
    },
    similarity_score: 0.92
  },
  {
    decision_id: 4,
    thread_id: 'thread_004',
    timestamp: '2026-02-04T11:20:00Z',
    author_user_id: 'bob',
    author_name: 'Bob Wilson',
    author_role: 'Firmware Engineer',
    decision_type: 'design_decision',
    decision_text: 'ESP32-Firmware memory optimization complete. Reduced flash usage from 850KB to 720KB to accommodate new WiFi stack.',
    affected_components: ['ESP32-Firmware'],
    referenced_reqs: [],
    before_after: {
      before: '850KB',
      after: '720KB'
    },
    similarity_score: 0.83
  }
];

export const mockDigest: PersonalizedDigest = {
  user_id: 'alice',
  date: '2026-02-08',
  summary: '3 critical decisions affect your components this week. REQ-245 motor torque change requires Motor-XYZ redesign. New supplier qualification needed for 22nm motor.',
  themes: [
    'Requirement Changes',
    'Mechanical Design Updates',
    'Supply Chain Impact'
  ],
  entries: [
    {
      decision_id: 'DEC-001',
      title: 'REQ-245: Motor Torque Requirement Change',
      summary: 'Motor torque requirement changing from 15nm to 22nm based on customer load analysis.',
      impact_summary: 'Motor-XYZ requires complete redesign, 3-week delay expected',
      before_after: {
        before: '15nm',
        after: '22nm'
      },
      affected_components: ['Motor-XYZ', 'Bracket-Assembly'],
      citations: ['#req-reviews thread_1234 2026-02-01T14:30'],
      timestamp: '2026-02-01T14:30:00Z'
    },
    {
      decision_id: 'DEC-002',
      title: 'Motor-XYZ Redesign Initiative',
      summary: 'Initiating Motor-XYZ redesign to accommodate new 22nm torque requirement.',
      impact_summary: 'Your owned component requires architectural changes and supply chain updates',
      affected_components: ['Motor-XYZ'],
      citations: ['#mechanical thread_5678 2026-02-02T09:15'],
      timestamp: '2026-02-02T09:15:00Z'
    }
  ],
  gaps_detected: [
    'Decision DEC-001 affects your Motor-XYZ but Bob (firmware) wasn\'t included - motor control algorithms may need updates',
    'Supply chain impact assessment missing for 22nm motor sourcing'
  ],
  action_items: [
    'Initiate Motor-XYZ redesign for 22nm torque requirement',
    'Coordinate with supply chain for new motor supplier qualification',
    'Update project timeline to account for 3-week delay'
  ]
};

export const mockGaps: Gap[] = [
  {
    type: 'missing_stakeholder',
    severity: 'critical',
    description: 'Decision DEC-001 affects Motor-XYZ but Bob Wilson (Firmware) wasn\'t included in discussion',
    decision_id: 1,
    recommendation: 'Include Bob in motor torque discussions as firmware control algorithms may need updates',
    timestamp: '2026-02-01T14:30:00Z',
    priority: 9
  },
  {
    type: 'conflict',
    severity: 'warning',
    description: 'Conflicting timeline estimates for Motor-XYZ redesign',
    decision_id: 2,
    recommendation: 'Align on realistic timeline with all stakeholders before proceeding',
    timestamp: '2026-02-02T09:15:00Z',
    priority: 6
  },
  {
    type: 'broken_dependency',
    severity: 'warning',
    description: 'PCB-Rev3 thermal changes may affect Motor-XYZ mounting requirements',
    recommendation: 'Verify motor mounting compatibility with new PCB thermal design',
    timestamp: '2026-02-03T16:45:00Z',
    priority: 5
  }
];