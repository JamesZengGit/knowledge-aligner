import 'dotenv/config';
import { PrismaClient } from '../generated/prisma';

const prisma = new PrismaClient();

async function main() {
  console.log('🌱 Seeding Knowledge Aligner database...');

  // Create users
  console.log('👥 Creating users...');
  const users = [
    {
      userId: 'alice',
      userName: 'Alice Chen',
      email: 'alice.chen@company.com',
      role: 'Hardware Lead',
      ownedComponents: JSON.stringify(['motor', 'power_supply', 'mechanical'])
    },
    {
      userId: 'bob',
      userName: 'Bob Wilson',
      email: 'bob.wilson@company.com',
      role: 'Firmware Engineer',
      ownedComponents: JSON.stringify(['firmware', 'security', 'bootloader'])
    },
    {
      userId: 'charlie',
      userName: 'Charlie Davis',
      email: 'charlie.davis@company.com',
      role: 'Test Engineer',
      ownedComponents: JSON.stringify(['validation', 'testing', 'qa'])
    },
    {
      userId: 'diana',
      userName: 'Diana Rodriguez',
      email: 'diana.rodriguez@company.com',
      role: 'Systems Architect',
      ownedComponents: JSON.stringify(['architecture', 'integration', 'protocols'])
    },
    {
      userId: 'erik',
      userName: 'Erik Thompson',
      email: 'erik.thompson@company.com',
      role: 'PCB Designer',
      ownedComponents: JSON.stringify(['pcb', 'layout', 'components'])
    },
    {
      userId: 'fiona',
      userName: 'Fiona Kim',
      email: 'fiona.kim@company.com',
      role: 'Software Lead',
      ownedComponents: JSON.stringify(['software', 'ui', 'drivers'])
    }
  ];

  for (const user of users) {
    await prisma.user.upsert({
      where: { userId: user.userId },
      update: user,
      create: user
    });
  }

  // Create decisions
  console.log('📋 Creating decisions...');
  const decisions = [
    {
      decisionId: '241',
      threadId: 'thread_241',
      timestamp: new Date('2024-01-10T08:30:00Z'),
      authorUserId: 'diana',
      authorName: 'Diana Rodriguez',
      authorRole: 'Systems Architect',
      decisionType: 'DESIGN_DECISION' as const,
      decisionText: 'Selected CAN bus protocol over I2C for motor controller communication due to noise immunity requirements in industrial environment',
      affectedComponents: JSON.stringify(['architecture', 'protocols', 'motor']),
      referencedReqs: JSON.stringify(['REQ-200', 'REQ-201']),
      similarityScore: 0.92,
      beforeState: { before: 'I2C communication (simple, low cost)' },
      afterState: { after: 'CAN bus protocol (robust, industrial-grade)' }
    },
    {
      decisionId: '242',
      threadId: 'thread_242',
      timestamp: new Date('2024-01-11T11:15:00Z'),
      authorUserId: 'erik',
      authorName: 'Erik Thompson',
      authorRole: 'PCB Designer',
      decisionType: 'REQUIREMENT_CHANGE' as const,
      decisionText: 'Changed PCB stackup from 4-layer to 6-layer to improve signal integrity for high-speed differential pairs',
      affectedComponents: JSON.stringify(['pcb', 'layout', 'components']),
      referencedReqs: JSON.stringify(['REQ-210', 'REQ-211']),
      similarityScore: 0.88,
      beforeState: { before: '4-layer PCB (cost optimized)' },
      afterState: { after: '6-layer PCB (signal integrity optimized)' }
    },
    {
      decisionId: '243',
      threadId: 'thread_243',
      timestamp: new Date('2024-01-12T14:20:00Z'),
      authorUserId: 'fiona',
      authorName: 'Fiona Kim',
      authorRole: 'Software Lead',
      decisionType: 'DESIGN_DECISION' as const,
      decisionText: 'Implemented real-time OS (FreeRTOS) instead of bare-metal for better task scheduling and reliability',
      affectedComponents: JSON.stringify(['software', 'firmware', 'drivers']),
      referencedReqs: JSON.stringify(['REQ-220', 'REQ-221']),
      similarityScore: 0.91,
      beforeState: { before: 'Bare-metal implementation' },
      afterState: { after: 'FreeRTOS with priority-based scheduling' }
    },
    {
      decisionId: '244',
      threadId: 'thread_244',
      timestamp: new Date('2024-01-13T16:45:00Z'),
      authorUserId: 'bob',
      authorName: 'Bob Wilson',
      authorRole: 'Firmware Engineer',
      decisionType: 'APPROVAL' as const,
      decisionText: 'Approved secure boot implementation with RSA-2048 signature verification for production firmware',
      affectedComponents: JSON.stringify(['firmware', 'security', 'bootloader']),
      referencedReqs: JSON.stringify(['REQ-230', 'REQ-231']),
      similarityScore: 0.94,
      beforeState: { before: 'No boot verification' },
      afterState: { after: 'RSA-2048 secure boot with signature verification' }
    },
    {
      decisionId: '245',
      threadId: 'thread_245',
      timestamp: new Date('2024-01-15T10:30:00Z'),
      authorUserId: 'alice',
      authorName: 'Alice Chen',
      authorRole: 'Hardware Lead',
      decisionType: 'REQUIREMENT_CHANGE' as const,
      decisionText: 'Updated motor torque requirement from 2.0Nm to 2.5Nm based on customer feedback and field testing results',
      affectedComponents: JSON.stringify(['motor', 'power_supply', 'mechanical']),
      referencedReqs: JSON.stringify(['REQ-240', 'REQ-241']),
      similarityScore: 0.95,
      beforeState: { before: 'Motor torque: 2.0Nm (original spec)' },
      afterState: { after: 'Motor torque: 2.5Nm (customer-validated requirement)' }
    }
  ];

  for (const decision of decisions) {
    await prisma.decision.upsert({
      where: { decisionId: decision.decisionId },
      update: decision,
      create: decision
    });
  }

  // Create gaps
  console.log('⚠️  Creating gaps...');
  const gaps = [
    {
      type: 'MISSING_STAKEHOLDER' as const,
      severity: 'CRITICAL' as const,
      description: 'REQ-246 power supply efficiency change affects your components but you weren\'t consulted',
      assigneeId: 'alice',
      priority: 1,
      recommendation: 'Contact Erik Thompson to understand power supply impact on motor requirements'
    },
    {
      type: 'CONFLICT' as const,
      severity: 'WARNING' as const,
      description: 'REQ-252 temperature range extension conflicts with current motor specifications',
      assigneeId: 'alice',
      priority: 2,
      recommendation: 'Review motor operating range compatibility with -20°C to +70°C requirement'
    },
    {
      type: 'MISSING_STAKEHOLDER' as const,
      severity: 'CRITICAL' as const,
      description: 'REQ-248 watchdog timer implementation needs firmware integration planning',
      assigneeId: 'bob',
      priority: 1,
      recommendation: 'Coordinate with Diana Rodriguez on watchdog integration with firmware architecture'
    },
    {
      type: 'MISSING_STAKEHOLDER' as const,
      severity: 'CRITICAL' as const,
      description: 'REQ-241 CAN bus protocol change requires new test equipment and procedures',
      assigneeId: 'charlie',
      priority: 1,
      recommendation: 'Request CAN bus testing tools and update validation procedures'
    }
  ];

  for (const gap of gaps) {
    await prisma.gap.create({
      data: gap
    });
  }

  console.log('✅ Seeding completed!');
}

main()
  .catch((e) => {
    console.error('❌ Seeding failed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });