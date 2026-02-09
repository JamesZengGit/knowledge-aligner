'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User as UserIcon } from 'lucide-react';
import { Decision, Gap, User } from '@/types';

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  context?: {
    decisions?: Decision[];
    gaps?: Gap[];
    summary?: string;
  };
}

interface ChatInterfaceProps {
  user: User;
  decisions: Decision[];
  gaps: Gap[];
  messages?: ChatMessage[];
  onMessagesChange?: (messages: ChatMessage[]) => void;
  onReset?: () => void;
}

export function ChatInterface({
  user,
  decisions,
  gaps,
  messages: externalMessages,
  onMessagesChange,
  onReset
}: ChatInterfaceProps) {
  const [isClient, setIsClient] = useState(false);

  // Use a fixed timestamp for SSR stability
  const stableTimestamp = new Date('2026-02-09T05:00:00Z');

  const generateWelcomeMessage = async () => {
    const criticalGaps = gaps.filter(g => g.severity === 'critical').length;
    const warningGaps = gaps.filter(g => g.severity === 'warning').length;
    const userDecisions = decisions.filter(d =>
      d.affected_components.some(c => user.owned_components.includes(c))
    ).length;

    try {
      // Try to get prioritized digest from backend
      const response = await fetch(`/api/digest/prioritized/${user.user_id}`);
      if (response.ok) {
        const prioritizedData = await response.json();

        return `Good morning, ${user.user_name}! 🌅

Welcome back to your Hardware Digest. As the ${user.role}, I've prepared your personalized engineering update.

**Today's Summary:**
• ${userDecisions} decisions affecting your components (${user.owned_components.join(', ')})
• ${criticalGaps} critical gaps detected
• ${warningGaps} warning-level gaps for monitoring

**🎯 Prioritized Topics:**
${prioritizedData.prioritized_topics?.slice(0, 3).map((topic: any, i: number) =>
  `${i + 1}. **${topic.name}** (Priority: ${topic.priority}/10) - ${topic.reason}`
).join('\n') || '• REQ-245 Motor changes\n• Torque specifications\n• Supply chain coordination'}

**⚠️ Limited Priority Gaps:**
${prioritizedData.prioritized_gaps?.slice(0, 2).map((gap: any, i: number) =>
  `${i + 1}. **${gap.title}** (${gap.urgency}) - ${gap.user_impact}`
).join('\n') || '• Missing stakeholder coordination\n• Timeline alignment needed'}

**📊 Trend Analysis:**
${prioritizedData.trend_analysis || 'Decision velocity increased 40% compared to yesterday, with REQ-245 driving cascade of component changes.'}

**💡 Key Insight:**
${prioritizedData.key_insight || 'The REQ-245 torque change is creating coordination challenges - ensure all component impacts are addressed in parallel.'}

What would you like to explore first? I can dive deep into any specific decisions, gaps, or component impacts.`;
      }
    } catch (error) {
      console.error('Failed to load prioritized digest:', error);
    }

    // Fallback to static message
    const topics = decisions.flatMap(d => d.affected_components);
    const topicCounts = topics.reduce((acc, topic) => {
      acc[topic] = (acc[topic] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    const topTopics = Object.entries(topicCounts)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 3)
      .map(([topic, count]) => `${topic} (${count})`);

    // Check for missing stakeholder notifications with meeting host info
    const missedMeetings = gaps.filter(g => g.type === 'missing_stakeholder');
    const getMeetingHost = (gapDecisionId: number) => {
      const decision = decisions.find(d => d.decision_id === gapDecisionId);
      return decision ? `${decision.author_name} (${decision.author_role})` : 'Unknown';
    };

    const notificationAlert = missedMeetings.length > 0 ?
      `\n🚨 **URGENT NOTIFICATION:** You weren't included in ${missedMeetings.length} decision${missedMeetings.length > 1 ? 's' : ''} affecting your components. Meeting host${missedMeetings.length > 1 ? 's' : ''} should be notified: ${missedMeetings.map(gap => getMeetingHost(gap.decision_id)).join(', ')}.` : '';

    return `Good morning, ${user.user_name}! 🌅

Welcome back to your Hardware Digest. As the ${user.role}, I've prepared your personalized engineering update.

**Today's Summary:**
• ${userDecisions} decisions affecting your components (${user.owned_components.join(', ')})
• ${criticalGaps} critical gaps detected
• ${warningGaps} warning-level gaps for monitoring${notificationAlert}

**🎯 Prioritized Topics:**
${topTopics.slice(0, 3).map((topic, i) => `${i + 1}. ${topic} discussions`).join('\n')}

**⚠️ Limited Priority Gaps:**
${gaps.slice(0, 4).map((gap, i) => {
  const gapTypeLabel = gap.type === 'missing_stakeholder' ? 'Missing Stakeholder' :
                      gap.type === 'coordination_needed' ? 'Coordination Needed' :
                      gap.type === 'conflict' ? 'Decision Conflict' : gap.type;

  const briefDescription = gap.recommendation ? gap.recommendation.slice(0, 100) : gap.description.slice(0, 100);

  return `${i + 1}. **${gapTypeLabel}** (REQ-${gap.decision_id?.toString().padStart(3, '0') || '000'}): ${briefDescription}...`;
}).join('\n')}

${criticalGaps > 0 ?
  `\n⚠️ **Immediate attention needed:** ${criticalGaps} critical stakeholder gap${criticalGaps > 1 ? 's' : ''} require${criticalGaps > 1 ? '' : 's'} your input.` :
  '\n✅ **Good news:** All recent decisions have proper stakeholder coverage.'
}

${missedMeetings.length > 0 ?
  `\n📋 **Recommended Actions:**\n• Contact meeting hosts directly: ${missedMeetings.map(gap => getMeetingHost(gap.decision_id)).join(', ')}\n• Request retroactive inclusion in decision documentation\n• Escalate to your manager if stakeholder gaps persist\n• Review component ownership clarity with project leads` :
  ''
}

What would you like to explore first? I can dive deep into any specific decisions, gaps, or component impacts.`;
  };

  const [internalMessages, setInternalMessages] = useState<ChatMessage[]>([]);
  const [initialMessageLoaded, setInitialMessageLoaded] = useState(false);

  // Use external messages if provided, otherwise use internal state
  const messages = externalMessages || internalMessages;
  const setMessages = onMessagesChange || setInternalMessages;

  // Set client flag after hydration
  useEffect(() => {
    setIsClient(true);
  }, []);

  // Load initial welcome message and reset on user change
  useEffect(() => {
    if (isClient && (!externalMessages || externalMessages.length === 0)) {
      generateWelcomeMessage().then(welcomeContent => {
        const welcomeMessage = {
          id: `${user.user_id}-welcome-${Date.now()}`,
          type: 'assistant' as const,
          content: welcomeContent,
          timestamp: new Date(),
        };
        setMessages([welcomeMessage]);
        setInitialMessageLoaded(true);
      });
    }
  }, [isClient, decisions, gaps, user.user_id, externalMessages, setMessages]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const generateAIResponse = async (userMessage: string): Promise<string> => {
    try {
      // Call OpenAI API through backend - let it handle all the intelligence
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          user_id: user.user_id
        })
      });

      if (!response.ok) {
        throw new Error('Failed to get AI response');
      }

      const data = await response.json();
      return data.response;
    } catch (error) {
      // Simple fallback - let user know AI is unavailable
      return `I'm having trouble connecting to the AI service right now. Please try again in a moment, or check with your system administrator if the issue persists.

In the meantime, you can:
• Browse the Decisions database for REQ-245 updates
• Check the Gaps section for priority items
• Review your component status: ${user.owned_components.join(', ')}`;
    }
  };

  const generateMockResponse = (query: string, decisions: Decision[], gaps: Gap[]): string => {
    const lowerQuery = query.toLowerCase();

    if (lowerQuery.includes('top priority') || lowerQuery.includes('priority')) {
      const criticalGaps = gaps.filter(g => g.severity === 'critical').length;
      const myDecisions = decisions.filter(d =>
        d.affected_components.some(c => user.owned_components.includes(c))
      );

      return `**Your Top Priority (${user.user_name}):**

🔴 **#1 URGENT: REQ-245 Motor Torque Change**
- **Impact**: Motor-XYZ requires complete redesign (15nm → 22nm)
- **Timeline**: 3-week redesign window starting immediately
- **Critical Issue**: You're missing from firmware coordination discussions

⚡ **Immediate Actions Required:**
1. Connect with Bob Wilson (Firmware) - PID controller needs updates
2. Coordinate with Dave Johnson (Hardware) on power supply changes (5A→8A)
3. Initiate supplier qualification for new motor specifications

**Why This is #1 Priority:**
- Affects your primary component (Motor-XYZ)
- Blocking other team members' work
- ${criticalGaps} critical stakeholder gap${criticalGaps > 1 ? 's' : ''} detected
- Timeline impact cascades through entire project

**Next 72 Hours:**
- Schedule alignment meeting with Bob + Dave
- Review new motor specifications with supply chain
- Update mechanical design requirements document`;
    }

    if (lowerQuery.includes('motor') || lowerQuery.includes('req-245')) {
      return `**REQ-245 Update Summary:**

The motor torque requirement has changed from 15nm to 22nm, affecting your ${user.owned_components.join(' and ')}. Here's what you need to know:

🔴 **Immediate Actions:**
- Motor-XYZ redesign is confirmed for 3-week timeline
- Alice is coordinating with supply chain for new specifications

⚠️ **Critical Gap Detected:**
Bob (Firmware) wasn't included but should be - motor control algorithms need PID updates (Kp: 1.2→1.8, Ki: 0.5→0.7)

🔗 **Related Impact:**
- Dave is modifying PCB-Rev3 power supply (5A→8A capacity)
- This cascades through the entire motor control system

**Recommendation:** Connect with Bob immediately to align on firmware changes.`;
    }

    if (lowerQuery.includes('gap') || lowerQuery.includes('missing')) {
      const criticalGaps = gaps.filter(g => g.severity === 'critical');
      if (criticalGaps.length > 0) {
        return `**${criticalGaps.length} Critical Gaps Detected:**

${criticalGaps.map((gap, i) =>
  `${i + 1}. **${gap.type.replace('_', ' ').toUpperCase()}**
   ${gap.description}

   *Recommendation:* ${gap.recommendation}`
).join('\n\n')}

These gaps could impact your project timeline. Should I help you prioritize them?`;
      }
    }

    if (lowerQuery.includes('summary') || lowerQuery.includes('status')) {
      const myDecisions = decisions.filter(d =>
        d.affected_components.some(c => user.owned_components.includes(c))
      );

      return `**Your Component Status:**

📊 **${myDecisions.length} decisions** affecting your components in the last week
⚠️ **${gaps.filter(g => g.severity === 'critical').length} critical gaps** need attention
🔄 **${decisions.filter(d => d.decision_type === 'requirement_change').length} requirement changes** in progress

**Top Priority:** REQ-245 motor changes require immediate coordination with firmware team.

Would you like me to dive deeper into any specific area?`;
    }

    // Default intelligent response
    const recentCount = decisions.filter(d =>
      d.affected_components.some(c => user.owned_components.includes(c))
    ).length;

    return `I found ${recentCount} recent decisions related to your query. ${recentCount > 0 ?
      'The most relevant is REQ-245 affecting your Motor-XYZ component.' :
      'Nothing critical affecting your components right now.'}

What specific aspect would you like to explore?`;
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || loading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setLoading(true);

    try {
      const response = await generateAIResponse(inputMessage);

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to generate response:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-[600px] bg-white rounded-lg border shadow-sm">
      {/* Chat Header */}
      <div className="flex items-center justify-between p-4 border-b bg-[#F5F1E8]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Hardware Digest Assistant</h3>
            <p className="text-xs text-gray-600">Personalized for {user.role}</p>
          </div>
        </div>

        <button
          onClick={() => {
            if (onReset) {
              onReset();
            }
            setInitialMessageLoaded(false);
            generateWelcomeMessage().then(welcomeContent => {
              const newWelcomeMessage = {
                id: Date.now().toString(),
                type: 'assistant' as const,
                content: welcomeContent,
                timestamp: new Date(),
              };
              setMessages([newWelcomeMessage]);
              setInitialMessageLoaded(true);
            });
          }}
          className="text-sm bg-white hover:bg-gray-50 text-gray-700 px-3 py-1 rounded border"
        >
          Reset Conversation
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`flex items-start gap-2 max-w-[80%] ${
                message.type === 'user' ? 'flex-row-reverse' : ''
              }`}
            >
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                message.type === 'user' ? 'bg-blue-600' : 'bg-gray-600'
              }`}>
                {message.type === 'user' ? (
                  <UserIcon className="w-4 h-4 text-white" />
                ) : (
                  <Bot className="w-4 h-4 text-white" />
                )}
              </div>

              <div
                className={`rounded-lg p-3 ${
                  message.type === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                <div className="whitespace-pre-wrap text-sm leading-relaxed">
                  {message.content}
                </div>
                <div className={`text-xs mt-1 ${
                  message.type === 'user' ? 'text-blue-100' : 'text-gray-500'
                }`}>
                  {message.timestamp.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </div>
              </div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <div className="bg-gray-100 rounded-lg p-3">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about decisions, gaps, or your components..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={loading}
          />
          <button
            onClick={handleSendMessage}
            disabled={loading || !inputMessage.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>

        {/* Dynamic Quick Suggestions */}
        <div className="mt-2 flex flex-wrap gap-2">
          {(() => {
            const criticalGaps = gaps.filter(g => g.severity === 'critical').length;
            const userDecisions = decisions.filter(d =>
              d.affected_components.some(c => user.owned_components.includes(c))
            ).length;

            const suggestions = [];

            if (criticalGaps > 0) {
              suggestions.push({
                text: `⚠️ ${criticalGaps} critical gaps`,
                query: "Walk me through each critical gap in detail. Why am I missing from these decisions, what's the potential impact on my work, and what specific actions should I take to get involved?",
                style: "text-xs bg-red-100 hover:bg-red-200 text-red-800 rounded-full px-3 py-1 transition-colors"
              });
            }

            if (userDecisions > 0) {
              suggestions.push({
                text: `📋 ${userDecisions} affecting me`,
                query: "Please provide a detailed breakdown of the decisions affecting my components. Include the full context, stakeholders involved, timeline impacts, and my specific responsibilities as Mechanical Lead.",
                style: "text-xs bg-blue-100 hover:bg-blue-200 text-blue-800 rounded-full px-3 py-1 transition-colors"
              });
            }

            suggestions.push({
              text: "🔧 REQ-245 deep dive",
              query: "Give me a comprehensive analysis of REQ-245 motor changes, including all stakeholder impacts, timeline implications, and what I need to do as Mechanical Lead",
              style: "text-xs bg-amber-100 hover:bg-amber-200 text-amber-800 rounded-full px-3 py-1 transition-colors"
            });

            suggestions.push({
              text: "📊 Engineering trends",
              query: "Analyze the engineering trends and patterns from this week's decisions. What themes are emerging and how do they affect our project roadmap?",
              style: "text-xs bg-gray-100 hover:bg-gray-200 rounded-full px-3 py-1 transition-colors"
            });

            return suggestions.slice(0, 4).map((suggestion, index) => (
              <button
                key={index}
                onClick={() => setInputMessage(suggestion.query)}
                className={suggestion.style}
                disabled={loading}
              >
                {suggestion.text}
              </button>
            ));
          })()}
        </div>
      </div>
    </div>
  );
}