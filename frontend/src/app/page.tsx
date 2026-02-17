'use client';

import { useState, useEffect } from 'react';
import { Header } from '@/components/ui/Header';
import { Sidebar } from '@/components/ui/Sidebar';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { DecisionsDatabase } from '@/components/decisions/DecisionsDatabase';
import { GapPriorityManager } from '@/components/gaps/GapPriorityManager';
import { mockUsers, mockDecisions, mockGaps } from '@/lib/mock-data';
import { User, Decision, Gap } from '@/types';
import api from '@/lib/api';

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export default function Home() {
  const [activeTab, setActiveTab] = useState('chat');
  const [currentAccount, setCurrentAccount] = useState('alice');

  const accounts = {
    alice: {
      user_id: 'alice',
      user_name: 'Alice Chen',
      role: 'Mechanical Lead',
      owned_components: ['Motor-XYZ', 'Bracket-Assembly']
    },
    bob: {
      user_id: 'bob',
      user_name: 'Bob Wilson',
      role: 'Firmware Engineer',
      owned_components: ['ESP32-Firmware', 'Bootloader']
    },
    dave: {
      user_id: 'dave',
      user_name: 'Dave Johnson',
      role: 'Hardware Lead',
      owned_components: ['PCB-Rev3', 'Power-Supply-v2']
    }
  };

  const currentUser = accounts[currentAccount];
  const [decisions, setDecisions] = useState<Decision[]>(mockDecisions);
  const [gaps, setGaps] = useState<Gap[]>(mockGaps.sort((a, b) => (b.priority || 0) - (a.priority || 0)));
  const [loading, setLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [decisionsData, gapsData] = await Promise.all([
        api.getDecisions(),
        fetch(`/api/gaps?user_id=${currentUser.user_id}`).then(res => res.json())
      ]);
      setDecisions(decisionsData);
      setGaps(gapsData);
    } catch (error) {
      // Fallback to mock data
      setDecisions(mockDecisions);
      setGaps(mockGaps);
    }
    setLoading(false);
  };

  const handleGapPriorityChange = async (gapId: string | number, priority: number) => {
    // Update backend with new priority
    try {
      await fetch(`/api/gaps/priority/${gapId}?priority=${priority}&user_id=${currentAccount}`, {
        method: 'POST',
      });
    } catch (error) {
      console.error('Failed to update gap priority:', error);
    }

    // Update gap priorities in state
    setGaps(prevGaps =>
      prevGaps.map(gap =>
        (gap.decision_id === gapId || (gap as any).gap_id === gapId)
          ? { ...gap, priority }
          : gap
      ).sort((a, b) => (a.priority || 0) - (b.priority || 0))
    );
  };

  const handleGapReorder = async (reorderedGaps: Gap[]) => {
    setGaps(reorderedGaps);
    // Update priorities based on new order — use gap_id when decision_id is absent
    for (let index = 0; index < reorderedGaps.length; index++) {
      const gap = reorderedGaps[index];
      const identifier = gap.decision_id ?? (gap as any).gap_id;
      if (identifier) {
        await handleGapPriorityChange(identifier, index + 1);
      }
    }
  };

  const handleChatReset = () => {
    setChatMessages([]);
  };

  // Reset conversation and reload data when account switches
  useEffect(() => {
    setChatMessages([]); // Reset chat on account change
    loadData(); // Reload data for new account's context
  }, [currentAccount]);

  const renderContent = () => {
    switch (activeTab) {
      case 'chat':
        return (
          <div className="max-w-4xl mx-auto">
            <div className="mb-6">
              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                Hardware Digest Assistant
              </h1>
              <p className="text-gray-600">
                Chat with AI to get summaries, check gaps, and understand decision impacts
              </p>
            </div>
            <ChatInterface
              user={currentUser}
              decisions={decisions}
              gaps={gaps}
              messages={chatMessages}
              onMessagesChange={setChatMessages}
              onReset={handleChatReset}
            />
          </div>
        );

      case 'decisions':
        return (
          <DecisionsDatabase
            userPreferences={{
              density: 'comfortable',
              priorityComponents: currentUser.owned_components,
              alertThreshold: 'warning',
              role: currentUser.role.toLowerCase()
            }}
            gaps={gaps}
          />
        );

      case 'gaps':
        return loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="text-gray-500 mt-2">Loading gaps...</p>
          </div>
        ) : (
          <GapPriorityManager
            gaps={gaps}
            onPriorityChange={handleGapPriorityChange}
            onReorder={handleGapReorder}
          />
        );

      default:
        return renderContent();
    }
  };

  return (
    <div className="h-screen flex flex-col">
      <Header currentUser={currentUser} accounts={accounts} currentAccount={currentAccount} onAccountChange={setCurrentAccount} />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

        <main className="flex-1 overflow-y-auto p-6">
          {renderContent()}
        </main>
      </div>
    </div>
  );
}