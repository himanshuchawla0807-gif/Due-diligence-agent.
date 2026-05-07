import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { DocumentTreeViewer } from './DocumentTreeViewer';
import { ChatMessagesPanel } from './ChatMessagesPanel';
import { DocumentViewerPanel } from './DocumentViewerPanel';
import type { ChatMessage, DocumentTree, Citation } from '../../types';

interface SplitScreenLayoutProps {
  messages: ChatMessage[];
  documentTree: DocumentTree | null;
  onCitationClick: (citation: Citation) => void;
  onDocumentSelect?: (documentPath: string) => void;
  onSendMessage: (message: string, withSearch: boolean) => void;
  onStop?: () => void;  // ✅ NEW: Stop current query
  isLoading: boolean;
  InputComponent: React.ComponentType<any>;
  sessionId: string | null;
  activeCitation: Citation | null;
  onCloseViewer: () => void;
  backendStatus: 'checking' | 'online' | 'offline';
  chatTitle?: string | null;  // LLM-generated chat title
}

export function SplitScreenLayout({
  messages,
  documentTree,
  onCitationClick,
  onDocumentSelect,
  onSendMessage,
  onStop,
  isLoading,
  InputComponent,
  sessionId,
  activeCitation,
  onCloseViewer,
  backendStatus,
  chatTitle,
}: SplitScreenLayoutProps) {
  const [isSplit, setIsSplit] = useState(false);
  const [activeDocument, setActiveDocument] = useState<string | undefined>();
  const isViewerOpen = activeCitation !== null;

  // Notify parent window (ORIPLEX) when document viewer opens/closes
  // This allows the parent to show a backdrop overlay that covers the sidebar
  useEffect(() => {
    // Only send message if we're in an iframe
    if (window.parent !== window) {
      try {
        window.parent.postMessage(
          { type: isViewerOpen ? 'MODAL_OPEN' : 'MODAL_CLOSE' },
          '*' // In production, use specific origin
        );
      } catch (e) {
        console.warn('Could not send modal state to parent:', e);
      }
    }
  }, [isViewerOpen]);

  // Handle document selection - update active document and trigger viewer
  const handleDocumentClick = (documentPath: string) => {
    setActiveDocument(documentPath);
    onDocumentSelect?.(documentPath);
  };

  // Sync active document with active citation
  useEffect(() => {
    if (activeCitation) {
      const path = activeCitation.relative_path || activeCitation.file_name;
      if (path) {
        setActiveDocument(path);
        // Also ensure the tree expands to show this file (handled by DocumentTreeViewer usually if activeDocument is set)
      }
    }
  }, [activeCitation]);

  // Trigger split-screen animation after first message
  useEffect(() => {
    if (messages.length > 0 && !isSplit) {
      // Delay to allow for smooth animation
      setTimeout(() => setIsSplit(true), 100);
    }
  }, [messages.length, isSplit]);

  // If no messages yet, show centered input
  if (messages.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-3xl px-6"
        >
          <div className="mb-8 text-center">
            <h2 className="text-3xl font-bold text-gray-900 mb-2">
              Ask me anything about your documents
            </h2>
            <p className="text-gray-600">
              Get precise answers with citations linked to source documents
            </p>
          </div>
          <InputComponent onSubmit={onSendMessage} isLoading={isLoading} onStop={onStop} />
        </motion.div>
      </div>
    );
  }

  // Split-screen layout
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key="split-screen"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15 }}  // ✅ Faster
        className="h-full w-full bg-white"
      >
        <PanelGroup direction="horizontal" className="h-full w-full">
          {/* Document Tree Panel */}
          <Panel defaultSize={20} minSize={15} maxSize={40} order={1}>
            <div
              className="h-full bg-white border-r border-gray-200 overflow-hidden"
            >
              <DocumentTreeViewer
                documentTree={documentTree}
                activeDocument={activeDocument}
                onDocumentSelect={handleDocumentClick}
              />
            </div>
          </Panel>

          <PanelResizeHandle className="w-1 bg-transparent hover:bg-blue-500 transition-colors duration-150 cursor-col-resize z-50 -ml-0.5 relative group">
            <div className="absolute inset-y-0 left-1/2 w-0.5 bg-blue-500 opacity-0 group-hover:opacity-100 transition-opacity" />
          </PanelResizeHandle>

          {/* Chat Panel */}
          <Panel defaultSize={isViewerOpen ? 40 : 80} minSize={30} order={2}>
            <motion.div
              initial={{ width: '100%' }}
              animate={{ width: '100%' }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
              className="h-full bg-white overflow-hidden flex flex-col"
            >
              <ChatMessagesPanel
                messages={messages}
                isLoading={isLoading}
                onSendMessage={onSendMessage}
                onStop={onStop}
                onCitationClick={onCitationClick}
                onDocumentSelect={onDocumentSelect}
                InputComponent={InputComponent}
                backendStatus={backendStatus}
                chatTitle={chatTitle || undefined}
              />
            </motion.div>
          </Panel>

          {/* Document Viewer Panel (slides in when open) */}
          {isViewerOpen && activeCitation && sessionId && (
            <>
              <PanelResizeHandle className="w-1 bg-transparent hover:bg-blue-500 transition-colors duration-150 cursor-col-resize z-50 -ml-0.5 relative group">
                <div className="absolute inset-y-0 left-1/2 w-0.5 bg-blue-500 opacity-0 group-hover:opacity-100 transition-opacity" />
              </PanelResizeHandle>

              <Panel defaultSize={40} minSize={20} order={3}>
                <motion.div
                  initial={{ width: 0, opacity: 0, x: 100 }}
                  animate={{ width: '100%', opacity: 1, x: 0 }}
                  exit={{ width: 0, opacity: 0, x: 100 }}
                  transition={{ duration: 0.4, ease: 'easeOut' }}
                  className="h-full bg-white border-l border-gray-200 overflow-hidden"
                >
                  <DocumentViewerPanel
                    sessionId={sessionId}
                    fileName={activeCitation.relative_path || activeCitation.file_name}
                    citation={activeCitation}
                    onClose={onCloseViewer}
                  />
                </motion.div>
              </Panel>
            </>
          )}
        </PanelGroup>
      </motion.div>
    </AnimatePresence>
  );
}
