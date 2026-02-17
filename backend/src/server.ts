import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import { PrismaClient } from '../generated/prisma';

const app = express();
const prisma = new PrismaClient();
const PORT = process.env.PORT || 8001;

// Middleware
app.use(cors({
  origin: ['http://localhost:3000', 'http://127.0.0.1:3000'],
  credentials: true
}));
app.use(express.json());

// Health check
app.get('/', (req, res) => {
  res.json({
    message: 'Knowledge Aligner Prisma API',
    status: 'operational',
    version: '1.0.0-prisma',
    features: ['prisma', 'typescript', 'type-safe-database']
  });
});

// System status endpoint
app.get('/api/status', async (req, res) => {
  try {
    // Count records using Prisma
    const [userCount, decisionCount, gapCount] = await Promise.all([
      prisma.user.count(),
      prisma.decision.count(),
      prisma.gap.count()
    ]);

    res.json({
      users: userCount,
      decisions: decisionCount,
      gaps: gapCount,
      messages: 0, // Will be populated when we add Slack integration
      relationships: 0,
      embeddings: { embedded: 0, pending: 0, failed: 0 },
      database_url: 'prisma-postgresql',
      ai_enabled: !!(process.env.OPENAI_API_KEY && process.env.ANTHROPIC_API_KEY)
    });
  } catch (error) {
    console.error('Status error:', error);
    res.status(500).json({ error: 'Failed to get system status' });
  }
});

// User management endpoints
app.get('/api/users', async (req, res) => {
  try {
    const users = await prisma.user.findMany({
      select: {
        userId: true,
        userName: true,
        email: true,
        role: true,
        ownedComponents: true
      },
      orderBy: {
        userName: 'asc'
      }
    });

    // Transform to match frontend expected format
    const formattedUsers = users.map(user => ({
      user_id: user.userId,
      user_name: user.userName,
      email: user.email,
      role: user.role,
      owned_components: JSON.parse(user.ownedComponents)
    }));

    res.json(formattedUsers);
  } catch (error) {
    console.error('Users error:', error);
    res.status(500).json({ error: 'Failed to get users' });
  }
});

app.get('/api/users/:userId', async (req, res) => {
  try {
    const user = await prisma.user.findUnique({
      where: { userId: req.params.userId },
      select: {
        userId: true,
        userName: true,
        email: true,
        role: true,
        ownedComponents: true
      }
    });

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json({
      user_id: user.userId,
      user_name: user.userName,
      email: user.email,
      role: user.role,
      owned_components: JSON.parse(user.ownedComponents)
    });
  } catch (error) {
    console.error('User error:', error);
    res.status(500).json({ error: 'Failed to get user' });
  }
});

// Decision management endpoints
app.get('/api/decisions', async (req, res) => {
  try {
    const { user_id, limit = '50', offset = '0' } = req.query;

    let whereClause = {};

    if (user_id) {
      // Get user's owned components for filtering
      const user = await prisma.user.findUnique({
        where: { userId: user_id as string },
        select: { ownedComponents: true }
      });

      if (user) {
        const userComponents = JSON.parse(user.ownedComponents);
        // For SQLite, we need to use JSON search or LIKE queries
        // For now, let's get all decisions and filter in JavaScript
        whereClause = {};
      }
    }

    const decisions = await prisma.decision.findMany({
      where: whereClause,
      orderBy: { timestamp: 'desc' },
      take: parseInt(limit as string),
      skip: parseInt(offset as string),
      select: {
        id: true,
        decisionId: true,
        threadId: true,
        timestamp: true,
        authorUserId: true,
        authorName: true,
        authorRole: true,
        decisionType: true,
        decisionText: true,
        affectedComponents: true,
        referencedReqs: true,
        similarityScore: true,
        beforeState: true,
        afterState: true
      }
    });

    // Transform to match frontend expected format and filter if needed
    let filteredDecisions = decisions;
    if (user_id) {
      const user = await prisma.user.findUnique({
        where: { userId: user_id as string },
        select: { ownedComponents: true }
      });
      if (user) {
        const userComponents = JSON.parse(user.ownedComponents);
        filteredDecisions = decisions.filter(decision => {
          const components = JSON.parse(decision.affectedComponents);
          return components.some((comp: string) => userComponents.includes(comp));
        });
      }
    }

    const formattedDecisions = filteredDecisions.map(decision => ({
      decision_id: parseInt(decision.decisionId),
      thread_id: decision.threadId,
      timestamp: decision.timestamp.toISOString(),
      author_user_id: decision.authorUserId,
      author_name: decision.authorName,
      author_role: decision.authorRole,
      decision_type: decision.decisionType.toLowerCase(),
      decision_text: decision.decisionText,
      affected_components: JSON.parse(decision.affectedComponents),
      referenced_reqs: JSON.parse(decision.referencedReqs),
      similarity_score: decision.similarityScore,
      before_after: {
        before: (decision.beforeState as any)?.before || '',
        after: (decision.afterState as any)?.after || ''
      }
    }));

    res.json(formattedDecisions);
  } catch (error) {
    console.error('Decisions error:', error);
    res.status(500).json({ error: 'Failed to get decisions' });
  }
});

// Gaps endpoint
app.get('/api/gaps', async (req, res) => {
  try {
    const { user_id = 'alice' } = req.query;

    const gaps = await prisma.gap.findMany({
      where: {
        assigneeId: user_id as string
      },
      orderBy: { priority: 'asc' },
      include: {
        decision: {
          select: {
            decisionId: true,
            decisionText: true
          }
        }
      }
    });

    // Transform to match frontend expected format
    const formattedGaps = gaps.map(gap => ({
      type: gap.type.toLowerCase(),
      severity: gap.severity.toLowerCase(),
      description: gap.description,
      decision_id: gap.decision ? parseInt(gap.decision.decisionId) : undefined,
      priority: gap.priority,
      recommendation: gap.recommendation,
      timestamp: gap.createdAt.toISOString()
    }));

    res.json(formattedGaps);
  } catch (error) {
    console.error('Gaps error:', error);
    res.status(500).json({ error: 'Failed to get gaps' });
  }
});

// Gap priority update endpoint
app.post('/api/gaps/priority/:gapId', async (req, res) => {
  try {
    const gapId = parseInt(req.params.gapId);
    const { priority } = req.query;

    if (!priority || isNaN(parseInt(priority as string))) {
      return res.status(400).json({ error: 'Priority must be a valid number' });
    }

    // Find gap by decision_id (since frontend uses decision_id as gapId)
    const gap = await prisma.gap.findFirst({
      where: {
        decision: {
          decisionId: gapId.toString()
        }
      }
    });

    if (!gap) {
      return res.status(404).json({ error: 'Gap not found' });
    }

    // Update gap priority
    await prisma.gap.update({
      where: { id: gap.id },
      data: { priority: parseInt(priority as string) }
    });

    res.json({ success: true, message: 'Priority updated successfully' });
  } catch (error) {
    console.error('Priority update error:', error);
    res.status(500).json({ error: 'Failed to update priority' });
  }
});

// Start server
async function main() {
  try {
    await prisma.$connect();
    console.log('✅ Connected to database via Prisma');

    app.listen(PORT, () => {
      console.log(`🚀 Prisma server running at http://localhost:${PORT}`);
      console.log(`📊 API endpoints available:`);
      console.log(`   GET  /api/status - System status`);
      console.log(`   GET  /api/users - All users`);
      console.log(`   GET  /api/users/:id - Specific user`);
      console.log(`   GET  /api/decisions - All decisions`);
      console.log(`   GET  /api/gaps - User gaps`);
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

// Graceful shutdown
process.on('beforeExit', async () => {
  await prisma.$disconnect();
});

main().catch(console.error);