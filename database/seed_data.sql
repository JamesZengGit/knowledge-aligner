-- Seed data for Knowledge Aligner
-- Insert demo users and decisions to demonstrate the system

-- Insert user profiles
INSERT INTO user_profiles (user_id, user_name, role, owned_components, email) VALUES
('alice', 'Alice Chen', 'Mechanical Lead', ARRAY['Motor-XYZ', 'Bracket-Assembly'], 'alice@company.com'),
('bob', 'Bob Wilson', 'Firmware Engineer', ARRAY['ESP32-Firmware', 'Bootloader'], 'bob@company.com'),
('dave', 'Dave Johnson', 'Hardware Lead', ARRAY['PCB-Rev3', 'Power-Supply-v2'], 'dave@company.com'),
('eve', 'Eve Martinez', 'PM', ARRAY['Requirements', 'Schedule'], 'eve@company.com'),
('carol', 'Carol Smith', 'Supply Chain', ARRAY['BOM', 'Vendor-Selection'], 'carol@company.com');

-- Insert decisions with realistic engineering scenarios
INSERT INTO decisions (
    thread_id, timestamp, author_user_id, author_name, author_role,
    decision_type, decision_text, affected_components, referenced_reqs,
    similarity_score, before_after
) VALUES
-- REQ-245 Motor Torque Change (Original EverCurrent example)
('thread_001', NOW() - INTERVAL '2 hours', 'eve', 'Eve Martinez', 'PM',
 'requirement_change',
 'REQ-245: Motor torque requirement changing from 15nm to 22nm based on customer load analysis. This affects Motor-XYZ and potentially Bracket-Assembly mounting. We need to evaluate impact on power consumption and thermal management.',
 ARRAY['Motor-XYZ', 'Bracket-Assembly'],
 ARRAY['REQ-245'],
 0.95,
 '{"before": "15nm", "after": "22nm"}'::jsonb),

-- Alice's design response to motor change
('thread_002', NOW() - INTERVAL '1 hour', 'alice', 'Alice Chen', 'Mechanical Lead',
 'design_decision',
 'Motor-XYZ redesign required for 22nm torque. Estimated 3-week timeline. Need to coordinate with supply chain for new motor specifications. Bracket-Assembly may need reinforcement.',
 ARRAY['Motor-XYZ', 'Bracket-Assembly'],
 ARRAY['REQ-245'],
 0.87,
 '{"before": "3-week estimate", "after": "confirmed 3-week timeline"}'::jsonb),

-- Dave's power supply analysis
('thread_003', NOW() - INTERVAL '4 hours', 'dave', 'Dave Johnson', 'Hardware Lead',
 'design_decision',
 'Power analysis for increased motor torque: Power-Supply-v2 current capacity at 5A, new motor will draw 6.2A peak. Need to upgrade to 8A capacity or parallel configuration.',
 ARRAY['Power-Supply-v2', 'Motor-XYZ'],
 ARRAY['REQ-245'],
 0.89,
 '{"before": "5A capacity", "after": "8A capacity required"}'::jsonb),

-- Bob's firmware update (missing from motor discussions)
('thread_004', NOW() - INTERVAL '6 hours', 'bob', 'Bob Wilson', 'Firmware Engineer',
 'design_decision',
 'ESP32-Firmware motor control algorithm update to handle increased torque requirements. PID controller gains need adjustment: Kp=1.2->1.8, Ki=0.5->0.7. Testing required.',
 ARRAY['ESP32-Firmware', 'Motor-XYZ'],
 ARRAY['REQ-245'],
 0.84,
 '{"before": "PID gains: Kp=1.2, Ki=0.5", "after": "PID gains: Kp=1.8, Ki=0.7"}'::jsonb),

-- Power system impact (Dave should have been consulted)
('thread_005', NOW() - INTERVAL '3 hours', 'alice', 'Alice Chen', 'Mechanical Lead',
 'requirement_change',
 'Power requirements for Motor-XYZ increased due to 22nm torque. PCB-Rev3 power traces may need revision for higher current draw. Thermal analysis shows 15% increase in heat generation.',
 ARRAY['PCB-Rev3', 'Power-Supply-v2', 'Motor-XYZ'],
 ARRAY['REQ-245'],
 0.91,
 '{"before": "12V 2A power supply", "after": "12V 3.2A power supply"}'::jsonb),

-- Security requirement (Bob missing from initial discussion)
('thread_006', NOW() - INTERVAL '5 hours', 'eve', 'Eve Martinez', 'PM',
 'technical_decision',
 'Bootloader security update required for new ESP32 firmware. Must implement secure boot to prevent unauthorized firmware updates. This is critical for customer security compliance.',
 ARRAY['Bootloader', 'ESP32-Firmware'],
 ARRAY['REQ-301'],
 0.89,
 '{"before": "Basic bootloader", "after": "Secure boot enabled"}'::jsonb),

-- Supply chain impact
('thread_007', NOW() - INTERVAL '8 hours', 'carol', 'Carol Smith', 'Supply Chain',
 'design_decision',
 'New motor specifications for 22nm torque require different supplier. Lead time 6 weeks vs current 2 weeks. Cost increase 15%. Need approval for supplier change.',
 ARRAY['Motor-XYZ', 'BOM', 'Vendor-Selection'],
 ARRAY['REQ-245'],
 0.86,
 '{"before": "2 week lead time", "after": "6 week lead time"}'::jsonb),

-- Testing requirements
('thread_008', NOW() - INTERVAL '1 day', 'eve', 'Eve Martinez', 'PM',
 'requirement_change',
 'Updated testing requirements for motor torque validation. Need torque test fixture that can handle 22nm with ±2% accuracy. Previous fixture only rated for 18nm.',
 ARRAY['Motor-XYZ', 'Test-Fixtures'],
 ARRAY['REQ-245', 'REQ-246'],
 0.83,
 '{"before": "18nm test capacity", "after": "22nm test capacity"}'::jsonb);

-- Insert decision details (parent-detail pattern examples)
INSERT INTO decision_details (decision_id, detail_name, detail_value) VALUES
-- Extended context for REQ-245
(1, 'full_thread_text', '{"messages": [{"user": "eve", "text": "Customer feedback shows our current 15nm isn\t sufficient for their application"}, {"user": "alice", "text": "We can redesign Motor-XYZ but need 3 weeks"}, {"user": "dave", "text": "Power supply implications need analysis"}]}'::jsonb),
(1, 'impact_analysis', '{"affected_teams": ["mechanical", "firmware", "hardware"], "estimated_effort": "3-4 weeks", "cost_impact": "$15000", "risk_level": "medium"}'::jsonb),
(1, 'user_priority', '{"priority": 1, "updated_by": "alice", "updated_at": "2024-02-09T10:00:00Z"}'::jsonb),

-- Motor redesign details
(2, 'implementation_plan', '{"phases": ["CAD redesign", "prototype", "validation"], "dependencies": ["supplier selection", "test fixture"], "resources": ["2 mechanical engineers", "1 test engineer"]}'::jsonb),
(2, 'user_priority', '{"priority": 2, "updated_by": "alice", "updated_at": "2024-02-09T10:15:00Z"}'::jsonb),

-- Firmware update technical details
(4, 'code_changes', '{"files": ["motor_control.c", "pid_controller.h"], "testing_required": true, "regression_tests": ["torque_validation", "power_consumption", "thermal"]}'::jsonb),
(4, 'user_priority', '{"priority": 1, "updated_by": "bob", "updated_at": "2024-02-09T09:30:00Z"}'::jsonb);

-- Insert decision relationships
INSERT INTO decision_relationships (source_decision_id, target_decision_id, relationship_type, confidence) VALUES
(1, 2, 'IMPACTS', 0.95),  -- REQ-245 impacts motor redesign
(1, 3, 'IMPACTS', 0.85),  -- REQ-245 impacts power supply
(1, 4, 'IMPACTS', 0.80),  -- REQ-245 impacts firmware
(1, 5, 'IMPACTS', 0.90),  -- REQ-245 impacts PCB design
(2, 4, 'DEPENDS_ON', 0.75), -- Motor redesign depends on firmware update
(3, 5, 'REFERENCES', 0.85), -- Power analysis references PCB impact
(4, 6, 'REFERENCES', 0.60), -- Firmware update references security
(1, 7, 'IMPACTS', 0.70);   -- REQ-245 impacts supply chain

-- Insert some sample Slack messages
INSERT INTO slack_messages (message_id, channel_id, thread_id, user_id, message_text, timestamp, entities, processed) VALUES
('msg_001', 'C001', 'thread_001', 'eve', 'REQ-245: Motor torque requirement changing from 15nm to 22nm based on customer load analysis.', NOW() - INTERVAL '2 hours',
 '{"requirements": ["REQ-245"], "components": ["Motor-XYZ"], "decision_indicators": ["changing"], "before_after": {"before": "15nm", "after": "22nm"}}'::jsonb, true),
('msg_002', 'C001', 'thread_001', 'alice', 'We can handle the Motor-XYZ redesign but need 3 weeks minimum. Bracket-Assembly mounting may need reinforcement.', NOW() - INTERVAL '2 hours',
 '{"components": ["Motor-XYZ", "Bracket-Assembly"], "decision_indicators": ["can handle"], "timeline": "3 weeks"}'::jsonb, true),
('msg_003', 'C002', 'thread_004', 'bob', 'Updated ESP32-Firmware PID gains for new torque: Kp=1.2->1.8, Ki=0.5->0.7', NOW() - INTERVAL '6 hours',
 '{"components": ["ESP32-Firmware"], "decision_indicators": ["Updated"], "before_after": {"Kp": {"before": "1.2", "after": "1.8"}, "Ki": {"before": "0.5", "after": "0.7"}}}'::jsonb, true);

-- Refresh materialized view
SELECT refresh_daily_summary();

-- Verify data insertion
SELECT 'Inserted ' || COUNT(*) || ' user profiles' FROM user_profiles;
SELECT 'Inserted ' || COUNT(*) || ' decisions' FROM decisions;
SELECT 'Inserted ' || COUNT(*) || ' decision details' FROM decision_details;
SELECT 'Inserted ' || COUNT(*) || ' relationships' FROM decision_relationships;
SELECT 'Inserted ' || COUNT(*) || ' slack messages' FROM slack_messages;