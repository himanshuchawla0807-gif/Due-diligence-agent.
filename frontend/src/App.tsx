import { useState, useRef, useEffect } from 'react'
import { AIInputWithSearch } from '@/components/ui/ai-input-with-search'
import { FileUploadZone } from '@/components/ui/file-upload-zone'
import { AgentWorkflowDisplay } from '@/components/ui/agent-workflow-display'
import { SplitScreenLayout } from '@/components/CitationAwareChat/SplitScreenLayout'
import { useDocumentTree } from '@/hooks/useDocumentTree'
import { useCitationNavigation } from '@/hooks/useCitationNavigation'
import { MessageSquare } from 'lucide-react'
import type { Citation, ChatMessage } from '@/types'
import './App.css'

// Session service URL for session persistence
import { API_BASE_URL, SESSION_SERVICE_URL } from '@/config'
const SERVICE_KEY = import.meta.env.VITE_SERVICE_KEY || ''

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking')
  const [showChat, setShowChat] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const sessionNotifiedRef = useRef(false) // ✅ Track if parent has been notified (like Research Agent's hasStarted)
  const [agentSessionId] = useState<string | null>(null)
  const [showAgentWorkflow] = useState(false)
  const [viewMode, setViewMode] = useState<'chat' | 'agent'>('chat')
  const [chatTitle, setChatTitle] = useState<string | null>(null)  // LLM-generated chat title
  const [isRestoringSession, setIsRestoringSession] = useState(false)
  const abortControllerRef = useRef<AbortController | null>(null)  // ✅ For fetch cancellation

  // Get industry, user, and session from URL params (passed from Universal Frontend)
  const getUrlParams = () => {
    const params = new URLSearchParams(window.location.search);
    return {
      industry: params.get('industry') as 'VC' | 'PE' | 'FO' | 'MA' | 'CA' | 'OTHER' | null,
      customIndustry: params.get('customIndustry'),
      userId: params.get('user'),  // Firebase user ID for session persistence
      sessionId: params.get('session')  // Existing session to restore
    };
  };
  const urlParams = getUrlParams();

  const [selectedIndustry, setSelectedIndustry] = useState<'VC' | 'PE' | 'FO' | 'MA' | 'CA' | 'OTHER' | null>(urlParams.industry)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Citation-aware RAG hooks
  const { documentTree } = useDocumentTree(sessionId, urlParams.userId)
  const { activeCitation, handleCitationClick, closeViewer } = useCitationNavigation()

  // Restore session from URL ONLY (not from LocalStorage)
  // This allows users to start fresh sessions by navigating to the default page
  useEffect(() => {
    const restoreSession = async () => {
      // Only restore if explicitly passed via URL param
      // Do NOT auto-restore from LocalStorage - this allows fresh sessions
      const targetSessionId = urlParams.sessionId;

      if (!targetSessionId) {
        console.log('[SESSION] No session in URL - ready for new session');
        return;
      }

      // Always set session ID and show chat view
      setSessionId(targetSessionId);
      setShowChat(true);

      // If we don't have user ID, we can still try to show the session
      if (!urlParams.userId) {
        console.log(`⚠️ [SESSION] No user ID, showing session: ${targetSessionId}`);
        return;
      }

      setIsRestoringSession(true);
      try {
        const response = await fetch(`${SESSION_SERVICE_URL}/sessions/${urlParams.userId}/${targetSessionId}`, {
          headers: { 'x-service-key': SERVICE_KEY } // ✅ Auth
        });
        if (response.ok) {
          const data = await response.json();

          // Set chat title
          if (data.session?.title) {
            setChatTitle(data.session.title);
          }

          // Restore messages
          if (data.messages && data.messages.length > 0) {
            const restoredMessages: ChatMessage[] = data.messages.map((msg: any, idx: number) => ({
              id: msg.id || `restored-${idx}`,
              role: msg.role,
              content: msg.content,
              citations: msg.citations || [],
              steps: msg.steps || []
            }));
            setMessages(restoredMessages);
          }

          console.log(`✅ [SESSION] Restored session with ${data.messages?.length || 0} messages: ${targetSessionId}`);
        } else {
          console.log(`⚠️ [SESSION] Could not restore from Firestore, using session ID: ${targetSessionId}`);
        }
      } catch (error) {
        console.log('Could not restore session from Firestore:', error);
      } finally {
        setIsRestoringSession(false);
      }
    };

    restoreSession();
  }, [urlParams.sessionId, urlParams.userId]);

  // ✅ NEW: Save session to LocalStorage
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem('last_dd_session_id', sessionId);
    }
  }, [sessionId]);

  // Handle document selection from sidebar
  const handleDocumentSelect = (documentPath: string) => {
    // Create a citation-like object to open the document viewer
    const documentCitation: Citation = {
      id: 'sidebar-doc',
      page: 1,
      bbox: [0, 0, 1, 1],
      file_name: documentPath.split('/').pop() || documentPath,
      relative_path: documentPath,
      text_snippet: ''
    }
    handleCitationClick(documentCitation)
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Update URL when sessionId changes
  useEffect(() => {
    if (sessionId && !urlParams.sessionId) {
      // Update this iframe's URL (parent notified via handleUploadComplete)
      const newUrl = new URL(window.location.href);
      newUrl.searchParams.set('session', sessionId);
      window.history.replaceState({}, '', newUrl.toString());
      console.log('📢 [SESSION] Updated iframe URL with session:', sessionId);
    }
  }, [sessionId, urlParams.sessionId]);

  // Check backend health on mount
  useEffect(() => {
    checkBackendHealth()
  }, [])

  const checkBackendHealth = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`)
      if (response.ok) {
        setBackendStatus('online')
      } else {
        setBackendStatus('offline')
      }
    } catch (error) {
      setBackendStatus('offline')
    }
  }

  const handleSubmit = async (value: string, withSearch: boolean) => {
    // Add user message
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: value,
      timestamp: Date.now(),

      withSearch,
      industry: selectedIndustry
    }
    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)

    // ✅ Create abort controller for this request
    abortControllerRef.current = new AbortController()

    try {
      // Send to backend with session_id and user_id for Firestore persistence
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: value,
          withSearch: withSearch,
          session_id: sessionId,
          user_id: urlParams.userId,  // Firebase user ID for 14-day session persistence
          industry: selectedIndustry
        }),
        signal: abortControllerRef.current.signal  // ✅ Allow cancellation
      })

      if (!response.ok) {
        throw new Error('Failed to get response from backend')
      }

      const data = await response.json()

      // Add assistant message with citations
      const assistantMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: data.response,
        timestamp: Date.now(),
        citations: data.citations || [],
        steps: data.steps || []
      }
      setMessages(prev => [...prev, assistantMessage])

      // Store LLM-generated chat title if present
      if (data.chat_title) {
        setChatTitle(data.chat_title)
        console.log('🏷️ Chat title from API:', data.chat_title)

        // ✅ NEW: Notify parent of title update for live sidebar refresh
        if (window.parent !== window) {
          window.parent.postMessage({
            type: 'titleUpdated',
            sessionId: sessionId,
            title: data.chat_title
          }, '*');
          console.log('📢 [SESSION] Notified parent of title update:', data.chat_title);
        }
      }
    } catch (error) {
      // ✅ Ignore abort errors (expected when user clicks Stop)
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('🛑 [CHAT] Request aborted by user')
        return
      }

      console.error('Error:', error)
      // Add error message
      const errorMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `Sorry, there was an error processing your request. Please make sure the backend is running on ${API_BASE_URL}.`,
        timestamp: Date.now()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
      abortControllerRef.current = null  // ✅ Clear ref
    }
  }

  // ✅ Stop handler for abort button - aborts frontend fetch AND notifies backend
  const handleStop = async () => {
    console.log('🛑 [CHAT] Stopping query...')

    // 1. Abort the frontend fetch request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    setIsLoading(false)

    // 2. Tell backend to cancel any running operations for this session
    if (sessionId) {
      try {
        await fetch(`${API_BASE_URL}/api/cancel/${sessionId}`, {
          method: 'POST',
        })
        console.log('🛑 [CHAT] Backend cancel request sent')
      } catch (error) {
        console.log('🛑 [CHAT] Backend cancel failed (may already be complete):', error)
      }
    }
  }

  // ✅ NEW: Handle session created (for postMessage/URL update only - NOT showing chat yet)
  const handleSessionCreated = (newSessionId: string) => {
    // Notify parent IMMEDIATELY for URL update
    if (!sessionNotifiedRef.current && window.parent !== window) {
      sessionNotifiedRef.current = true;
      window.parent.postMessage({
        type: 'sessionCreated',
        sessionId: newSessionId,
        title: 'New Due Diligence',
        agentType: 'due_diligence'
      }, '*');
      console.log('📢 [SESSION] Notified parent of new session:', newSessionId);
    }
    // ⚠️ DON'T set sessionId here - wait until files are processed
    // Setting it here triggers useDocumentTree fetch before documents exist
  }

  // Handle file upload completion (called AFTER files are processed)
  const handleUploadComplete = async (_files: File[], newSessionId: string, industry: 'VC' | 'PE' | 'FO' | 'MA' | 'CA' | 'OTHER' | null) => {
    console.log('✅ [UPLOAD COMPLETE] Files processed, setting session...');

    // ✅ Set sessionId FIRST - this triggers useDocumentTree hook to fetch
    setSessionId(newSessionId);
    setSelectedIndustry(industry);

    // ✅ Wait a moment for the hook to start fetching, then show chat
    // The useDocumentTree hook auto-fetches when sessionId changes
    setTimeout(() => {
      setShowChat(true);
      console.log('Upload complete. Session ID:', newSessionId, 'Industry:', industry);
    }, 500);  // Give useDocumentTree time to fetch before showing chat
  }


  // Show loading screen while restoring session
  if (isRestoringSession) {
    return (
      <div className="h-screen flex flex-col items-center justify-center bg-white">
        <style>{`
          .circle-loader {
            --path: #d1d5db;
            --dot: #3B82F6;
            --duration: 3s;
            width: 44px;
            height: 44px;
            position: relative;
          }
          .circle-loader:before {
            content: "";
            width: 6px;
            height: 6px;
            border-radius: 50%;
            position: absolute;
            display: block;
            background: var(--dot);
            top: 3px;
            left: 19px;
            transform-origin: 3px 19px;
            transform: rotate(-90deg);
            animation: dotCircle var(--duration) cubic-bezier(0.785, 0.135, 0.15, 0.86) infinite;
          }
          .circle-loader svg {
            display: block;
            width: 100%;
            height: 100%;
          }
          .circle-loader svg circle {
            fill: none;
            stroke: var(--path);
            stroke-width: 10px;
            stroke-linejoin: round;
            stroke-linecap: round;
            stroke-dasharray: 150 50 150 50;
            stroke-dashoffset: 75;
            animation: pathCircle var(--duration) cubic-bezier(0.785, 0.135, 0.15, 0.86) infinite;
          }
          @keyframes pathCircle {
            25% { stroke-dashoffset: 125; }
            50% { stroke-dashoffset: 175; }
            75% { stroke-dashoffset: 225; }
            100% { stroke-dashoffset: 275; }
          }
          @keyframes dotCircle {
            0% { transform: rotate(-90deg); }
            25% { transform: rotate(-180deg); }
            50% { transform: rotate(-270deg); }
            75% { transform: rotate(-360deg); }
            100% { transform: rotate(-450deg); }
          }
        `}</style>
        <div className="flex flex-col items-center gap-5">
          <div className="circle-loader">
            <svg viewBox="0 0 80 80">
              <circle r={32} cy={40} cx={40} />
            </svg>
          </div>
          <p className="text-sm text-gray-400 font-medium tracking-wide">Just a moment...</p>
        </div>
      </div>
    )
  }

  // Show upload screen if no files uploaded yet
  console.log('🏠 [APP] showChat:', showChat, 'sessionId:', sessionId, 'urlParams.sessionId:', urlParams.sessionId);
  if (!showChat) {
    return (
      <FileUploadZone
        onUploadComplete={handleUploadComplete}
        onSessionCreated={handleSessionCreated}
        initialIndustry={urlParams.industry}
        customIndustry={urlParams.customIndustry || undefined}
        userId={urlParams.userId} // ✅ Pass user ID for trusted upload
        serviceKey={SERVICE_KEY}  // ✅ Pass service key for auth
      />
    )
  }

  const handleAgentCompletion = (results: any) => {
    console.log('Agent workflow completed', results)

    // Format summary message
    const recommendation = results.go_no_go_recommendation || 'Analysis Complete'
    const findings = results.key_findings || []

    let summaryContent = `## Analysis Complete\n\n**Recommendation:** ${recommendation}\n\n**Key Findings:**\n`
    findings.slice(0, 5).forEach((finding: string) => {
      summaryContent += `- ${finding}\n`
    })

    summaryContent += `\n\nI have completed the due diligence analysis. You can now ask me specific questions about the findings or any of the documents.`

    // Add summary message
    // Add summary message
    const summaryMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'assistant',
      content: summaryContent,
      timestamp: Date.now()
    }
    setMessages(prev => [...prev, summaryMessage])

    // Switch to chat view
    setViewMode('chat')
  }

  // Show agent workflow if active
  if (showAgentWorkflow && agentSessionId && viewMode === 'agent') {
    return (
      <>
        {/* View Toggle */}
        <div className="fixed top-4 left-4 z-10">
          <button
            onClick={() => setViewMode('chat')}
            className="flex items-center gap-2 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm px-4 py-2 rounded-full border border-slate-200 dark:border-slate-700 hover:bg-white dark:hover:bg-slate-800 transition-colors"
          >
            <MessageSquare className="w-4 h-4" />
            <span className="text-sm text-slate-700 dark:text-slate-300">Switch to Chat</span>
          </button>
        </div>
        <AgentWorkflowDisplay
          sessionId={agentSessionId}
          onComplete={handleAgentCompletion}
        />
      </>
    )
  }

  return (
    <div className="min-h-screen bg-[#F5F5F7] text-[#1D1D1F]">
      {/* Citation-aware Split Screen Layout */}
      <main className="h-screen flex flex-col p-4 pt-4 overflow-hidden">
        {/* Persistent Action Bar - Always show when session is established */}
        {sessionId && (
          <div className="fixed top-4 left-4 z-10 flex gap-2">
            {/* View Toggle - Only show if agent workflow is active */}
            {showAgentWorkflow && (
              <button
                onClick={() => setViewMode(viewMode === 'chat' ? 'agent' : 'chat')}
                className="flex items-center gap-2 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm px-4 py-2 rounded-full border border-slate-200 dark:border-slate-700 hover:bg-white dark:hover:bg-slate-800 transition-colors"
              >
                {viewMode === 'chat' ? (
                  <>
                    <MessageSquare className="w-4 h-4" />
                    <span className="text-sm text-slate-700 dark:text-slate-300">View Agent Analysis</span>
                  </>
                ) : (
                  <>
                    <MessageSquare className="w-4 h-4" />
                    <span className="text-sm text-slate-700 dark:text-slate-300">Back to Chat</span>
                  </>
                )}
              </button>
            )}
          </div>
        )}

        {/* Split Screen Layout with Citation-Aware Chat and Document Viewer */}
        <div className="flex-1 min-h-0 bg-white rounded-3xl shadow-xl border border-gray-200 overflow-hidden">
          <SplitScreenLayout
            messages={messages}
            documentTree={documentTree}
            onCitationClick={handleCitationClick}
            onDocumentSelect={handleDocumentSelect}
            onSendMessage={handleSubmit}
            onStop={handleStop}
            isLoading={isLoading}
            InputComponent={(props) => <AIInputWithSearch {...props} />}
            sessionId={sessionId}
            activeCitation={activeCitation}
            onCloseViewer={closeViewer}
            backendStatus={backendStatus}
            chatTitle={chatTitle}
          />
        </div>
      </main>
    </div >
  )
}

export default App
