'use client';

import { useState, useEffect } from 'react';
import {
  TrendingUp,
  Users,
  FileText,
  AlertTriangle,
  Clock,
  CheckCircle
} from 'lucide-react';
import { PersonalizedDigest, Gap, UserPreferences, User, Decision } from '@/types';
import { DigestEntry } from '../digest/DigestEntry';
import { GapAlert } from '../gaps/GapAlert';
import { DecisionCard } from '../decisions/DecisionCard';
import { mockDigest, mockGaps } from '@/lib/mock-data';
import api from '@/lib/api';

interface DashboardProps {
  userId: string;
}

export function Dashboard({ userId }: DashboardProps) {
  const [digest, setDigest] = useState<PersonalizedDigest | null>(null);
  const [gaps, setGaps] = useState<Gap[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [preferences, setPreferences] = useState<UserPreferences>({
    density: 'comfortable',
    priorityComponents: [],
    alertThreshold: 'warning',
    role: 'mechanical'
  });

  useEffect(() => {
    loadDashboardData();
  }, [userId]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      await new Promise(resolve => setTimeout(resolve, 1000));

      try {
        const [statusData, gapsData, usersData, decisionsData] = await Promise.all([
          api.getStatus(),
          api.getGaps(30),
          api.getUsers(),
          api.getDecisions()
        ]);

        setStats(statusData);
        setGaps(gapsData);

        // Find current user and set preferences
        const currentUser = usersData.find((u: User) => u.user_id === userId);
        if (currentUser) {
          setUser(currentUser);
          setPreferences(prev => ({
            ...prev,
            priorityComponents: currentUser.owned_components,
            role: currentUser.role.toLowerCase()
          }));
        }

        setDecisions(decisionsData);

        try {
          const digestData = await api.getUserDigest(userId, 7);
          setDigest(digestData);
        } catch {
          setDigest(mockDigest);
        }
      } catch {
        // Fallback to mock data
        setStats({
          users: 10,
          messages: 164,
          decisions: 45,
          relationships: 23,
          embeddings: { embedded: 35, pending: 10, failed: 0 },
          ai_enabled: false
        });
        setGaps(mockGaps);
        setDigest(mockDigest);

        // Mock user data
        const mockUser = {
          user_id: userId,
          user_name: userId === 'alice' ? 'Alice Chen' : 'User',
          role: 'Mechanical Lead',
          owned_components: ['Motor-XYZ', 'Bracket-Assembly'],
          email: `${userId}@company.com`
        };
        setUser(mockUser);
        setPreferences(prev => ({
          ...prev,
          priorityComponents: mockUser.owned_components,
          role: 'mechanical'
        }));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card p-6 text-center">
        <AlertTriangle className="w-12 h-12 text-warning-600 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Failed to Load Dashboard
        </h3>
        <p className="text-gray-600 mb-4">{error}</p>
        <button
          onClick={loadDashboardData}
          className="btn btn-primary"
        >
          Retry
        </button>
      </div>
    );
  }

  // Filter decisions for personalized views
  const highPriorityDecisions = decisions.filter(d =>
    d.affected_components.some(c => preferences.priorityComponents.includes(c))
  ).slice(0, 3);

  const recentDecisions = decisions.filter(d =>
    !highPriorityDecisions.some(hp => hp.decision_id === d.decision_id)
  ).slice(0, 5);

  return (
    <div className="space-y-6">
      {/* Personalized Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">
            Welcome back, {user?.user_name || 'User'}
          </h1>
          <p className="text-gray-600">
            {user?.role} • {preferences.priorityComponents.length} components tracked
          </p>
        </div>

        {/* Quick Preferences */}
        <div className="flex items-center gap-2">
          <select
            className="text-sm border rounded px-2 py-1"
            value={preferences.density}
            onChange={(e) => setPreferences(prev => ({
              ...prev,
              density: e.target.value as 'compact' | 'comfortable' | 'spacious'
            }))}
          >
            <option value="compact">Compact</option>
            <option value="comfortable">Comfortable</option>
            <option value="spacious">Spacious</option>
          </select>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="card p-6">
            <div className="flex items-center">
              <div className="p-2 bg-primary-100 rounded-lg">
                <FileText className="w-6 h-6 text-primary-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Decisions</p>
                <p className="text-2xl font-semibold text-gray-900">{stats.decisions}</p>
              </div>
            </div>
          </div>

          <div className="card p-6">
            <div className="flex items-center">
              <div className="p-2 bg-success-100 rounded-lg">
                <Users className="w-6 h-6 text-success-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Team Members</p>
                <p className="text-2xl font-semibold text-gray-900">{stats.users}</p>
              </div>
            </div>
          </div>

          <div className="card p-6">
            <div className="flex items-center">
              <div className="p-2 bg-warning-100 rounded-lg">
                <AlertTriangle className="w-6 h-6 text-warning-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Gaps Detected</p>
                <p className="text-2xl font-semibold text-gray-900">{gaps.length}</p>
              </div>
            </div>
          </div>

          <div className="card p-6">
            <div className="flex items-center">
              <div className="p-2 bg-primary-100 rounded-lg">
                <TrendingUp className="w-6 h-6 text-primary-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Messages</p>
                <p className="text-2xl font-semibold text-gray-900">{stats.messages}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Critical Gaps Alert */}
      {gaps.filter(g => g.severity === 'critical').length > 0 && (
        <div className="card p-6">
          <div className="flex items-center mb-4">
            <AlertTriangle className="w-5 h-5 text-danger-600 mr-2" />
            <h2 className="text-lg font-semibold text-danger-800">
              Critical Issues Detected
            </h2>
          </div>
          <div className="space-y-3">
            {gaps.filter(g => g.severity === 'critical').slice(0, 3).map((gap, index) => (
              <GapAlert key={index} gap={gap} compact />
            ))}
          </div>
        </div>
      )}

      {/* Priority Sections - EverCurrent Style */}
      <div className="space-y-8">
        {/* High Priority - Your Components */}
        {highPriorityDecisions.length > 0 && (
          <div>
            <div className="flex items-center gap-3 mb-6">
              <span className="w-8 h-8 bg-red-600 text-white rounded-full flex items-center justify-center text-sm font-medium">①</span>
              <div>
                <h2 className="text-xl font-semibold text-gray-900">
                  Immediate Actions Required
                </h2>
                <p className="text-sm text-gray-600">
                  Decisions affecting your components: {preferences.priorityComponents.join(', ')}
                </p>
              </div>
            </div>

            <div className="space-y-4">
              {highPriorityDecisions.map((decision) => (
                <DecisionCard
                  key={decision.decision_id}
                  decision={decision}
                  userRole={preferences.role}
                  userComponents={preferences.priorityComponents}
                  density={preferences.density}
                />
              ))}
            </div>
          </div>
        )}

        {/* Team Context */}
        <div>
          <div className="flex items-center gap-3 mb-6">
            <span className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-medium">②</span>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">
                Team Context & Dependencies
              </h2>
              <p className="text-sm text-gray-600">
                Recent decisions across the hardware team
              </p>
            </div>
          </div>

          {recentDecisions.length > 0 ? (
            <div className="space-y-4">
              {recentDecisions.map((decision) => (
                <DecisionCard
                  key={decision.decision_id}
                  decision={decision}
                  userRole={preferences.role}
                  userComponents={preferences.priorityComponents}
                  density={preferences.density}
                />
              ))}
            </div>
          ) : (
            <div className="bg-gray-50 rounded-lg p-8 text-center">
              <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No Recent Decisions
              </h3>
              <p className="text-gray-500">
                No team decisions found in the last 7 days
              </p>
            </div>
          )}
        </div>

        {/* Action Items */}
        {digest?.action_items && digest.action_items.length > 0 && (
          <div>
            <div className="flex items-center gap-3 mb-6">
              <span className="w-8 h-8 bg-green-600 text-white rounded-full flex items-center justify-center text-sm font-medium">③</span>
              <div>
                <h2 className="text-xl font-semibold text-gray-900">
                  Action Items
                </h2>
                <p className="text-sm text-gray-600">
                  Tasks and follow-ups from recent decisions
                </p>
              </div>
            </div>

            <div className="bg-[#F5F1E8] rounded-lg p-6">
              <div className="space-y-3">
                {digest.action_items.map((item, index) => (
                  <div key={index} className="flex items-start gap-3">
                    <Clock className="w-4 h-4 text-amber-600 mt-1 flex-shrink-0" />
                    <p className="text-gray-700">{item}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}