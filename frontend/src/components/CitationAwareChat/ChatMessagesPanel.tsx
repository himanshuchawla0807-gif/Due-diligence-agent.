import React, { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';

import { CitationAwareResponse } from './CitationAwareResponse';
import { ThinkingProcess } from './ThinkingProcess';
import { ChatMessage, Citation } from '../../types';

interface ChatMessagesPanelProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSendMessage: (message: string, withSearch: boolean) => void;
  onStop?: () => void;  // ✅ NEW: Stop current query
  onCitationClick: (citation: Citation) => void;
  onDocumentSelect?: (documentPath: string) => void;
  InputComponent: React.ComponentType<any>;
  backendStatus: 'checking' | 'online' | 'offline';
  chatTitle?: string;  // LLM-generated chat title from API
}

export function ChatMessagesPanel({
  messages,
  isLoading,
  onSendMessage,
  onStop,
  onCitationClick,
  onDocumentSelect,
  InputComponent,
  backendStatus,
  chatTitle,
}: ChatMessagesPanelProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Determine the title to display
  // Priority: LLM-generated title > "New Research" (default)
  // We don't show the raw query as title - wait for LLM to generate a proper title
  const displayTitle = chatTitle || 'New Research';

  return (
    <div className="h-full flex flex-col">
      {/* Header with Dynamic Title and Agent Info */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-gray-100 bg-white/80 backdrop-blur-sm z-10">
        {/* Left side - Green dot + Dynamic conversation title */}
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${backendStatus === 'online' ? 'bg-green-500' : backendStatus === 'offline' ? 'bg-red-500' : 'bg-yellow-500'}`}></div>
          <span className="text-sm font-medium text-gray-800 truncate max-w-[400px]">
            {displayTitle}
          </span>
        </div>
        {/* Right side - Agent name and live status */}
        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          <span className="font-medium">Due Diligence Agent</span>
          <span className="text-gray-300">•</span>
          <span className={backendStatus === 'online' ? 'text-emerald-500' : backendStatus === 'offline' ? 'text-red-500' : 'text-amber-500'}>
            {backendStatus === 'online' ? 'Live' : backendStatus === 'offline' ? 'Offline' : 'Connecting...'}
          </span>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.map((message, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {message.role === 'user' ? (
              <div className="max-w-[80%] bg-gradient-to-r from-blue-600 to-purple-600 text-white px-4 py-3 rounded-2xl shadow-lg">
                <p className="text-sm">{message.content}</p>
              </div>
            ) : (
              <div className="max-w-[85%] bg-white/90 backdrop-blur-sm border border-gray-200 px-4 py-3 rounded-2xl shadow-md">
                {message.steps && message.steps.length > 0 && (
                  <ThinkingProcess steps={message.steps} />
                )}
                <CitationAwareResponse
                  content={message.content}
                  citations={message.citations || []}
                  onCitationClick={onCitationClick}
                  onDocumentSelect={onDocumentSelect}
                />
              </div>
            )}
          </motion.div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-start"
          >
            <div className="bg-white/90 backdrop-blur-sm border border-gray-200 px-4 py-3 rounded-2xl shadow-md flex items-center gap-2">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
              </span>
              <span className="text-sm font-medium text-gray-600 animate-pulse">Thinking...</span>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-gray-200 bg-gray-50/50 backdrop-blur-sm p-4">
        <InputComponent onSubmit={onSendMessage} isLoading={isLoading} onStop={onStop} />
        <p className="text-center text-xs text-gray-600 mt-2">
          Oriplex can make mistakes. Verify important information.
        </p>
      </div>
    </div>
  );
}
