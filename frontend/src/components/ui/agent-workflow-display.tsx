import { useState, useEffect } from 'react'
import { API_BASE_URL } from '@/config'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, Clock, AlertCircle, Loader2, FileText, TrendingUp } from 'lucide-react'

interface AgentWorkflowDisplayProps {
  sessionId: string
  onComplete?: (results: any) => void
}

interface TeamStatus {
  name: string
  displayName: string
  status: 'pending' | 'active' | 'complete'
  findings?: number
  riskScore?: number
}

interface LogEntry {
  timestamp: string
  level: string
  component: string
  message: string
  metadata?: Record<string, any>
}

interface SessionStatus {
  session_id: string
  status: 'started' | 'in_progress' | 'completed' | 'error'
  firm_type: string
  market: string
  deal_name: string
  progress_percentage: number
  completed_teams: number
  total_teams: number
  current_team: string | null
  elapsed_time_seconds: number
  estimated_remaining_seconds: number
  recent_logs: LogEntry[]
  error?: string
}

export function AgentWorkflowDisplay({ sessionId, onComplete }: AgentWorkflowDisplayProps) {
  const [status, setStatus] = useState<SessionStatus | null>(null)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [results, setResults] = useState<any>(null)
  const [isPolling, setIsPolling] = useState(true)

  // Team definitions
  const teams: TeamStatus[] = [
    { name: 'financial', displayName: 'Financial Analysis', status: 'pending' },
    { name: 'legal', displayName: 'Legal Review', status: 'pending' },
    { name: 'commercial', displayName: 'Commercial Assessment', status: 'pending' },
    { name: 'technical', displayName: 'Technical Evaluation', status: 'pending' },
    { name: 'synthesis', displayName: 'Synthesis & Reporting', status: 'pending' }
  ]

  // Poll status endpoint
  useEffect(() => {
    if (!isPolling) return

    const poll = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/agents/status/${sessionId}`)
        if (response.ok) {
          const data: SessionStatus = await response.json()
          setStatus(data)
          setLogs(data.recent_logs || [])

          // Stop polling if completed or error
          if (data.status === 'completed' || data.status === 'error') {
            setIsPolling(false)
            if (data.status === 'completed') {
              fetchResults()
            }
          }
        }
      } catch (error) {
        console.error('Error polling status:', error)
      }
    }

    poll()
    const interval = setInterval(poll, 2000) // Poll every 2 seconds

    return () => clearInterval(interval)
  }, [sessionId, isPolling])

  // Fetch final results
  const fetchResults = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/agents/results/${sessionId}`)
      if (response.ok) {
        const data = await response.json()
        setResults(data)
        onComplete?.(data)
      }
    } catch (error) {
      console.error('Error fetching results:', error)
    }
  }

  // Update team statuses based on current status
  const getTeamStatuses = (): TeamStatus[] => {
    if (!status) return teams

    return teams.map((team) => {
      const teamKey = team.name
      const isComplete = status.completed_teams > teams.findIndex(t => t.name === teamKey)
      const isCurrent = status.current_team === teamKey

      return {
        ...team,
        status: isComplete ? 'complete' : isCurrent ? 'active' : 'pending'
      }
    })
  }

  // Format time
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}m ${secs}s`
  }



  if (!status) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    )
  }

  const teamStatuses = getTeamStatuses()

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6"
        >
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">
                {status.deal_name}
              </h1>
              <div className="flex gap-4 text-sm text-slate-600 dark:text-slate-400">
                <span className="flex items-center gap-1">
                  <FileText className="w-4 h-4" />
                  {status.firm_type} | {status.market}
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  Elapsed: {formatTime(status.elapsed_time_seconds)}
                </span>
                {status.status === 'in_progress' && (
                  <span className="flex items-center gap-1">
                    <TrendingUp className="w-4 h-4" />
                    Est. remaining: {formatTime(status.estimated_remaining_seconds)}
                  </span>
                )}
              </div>
            </div>

            {/* Progress Circle */}
            <div className="flex items-center gap-4">
              <div className="relative w-24 h-24">
                <svg className="w-24 h-24 transform -rotate-90">
                  <circle
                    cx="48"
                    cy="48"
                    r="40"
                    stroke="currentColor"
                    strokeWidth="8"
                    fill="none"
                    className="text-slate-200 dark:text-slate-700"
                  />
                  <circle
                    cx="48"
                    cy="48"
                    r="40"
                    stroke="currentColor"
                    strokeWidth="8"
                    fill="none"
                    strokeDasharray={`${2 * Math.PI * 40}`}
                    strokeDashoffset={`${2 * Math.PI * 40 * (1 - status.progress_percentage / 100)}`}
                    className="text-blue-500 transition-all duration-500"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-xl font-bold text-slate-900 dark:text-white">
                    {status.progress_percentage}%
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Overall Progress Bar */}
          <div className="mt-4">
            <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-blue-500 to-indigo-500"
                initial={{ width: 0 }}
                animate={{ width: `${status.progress_percentage}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
          </div>
        </motion.div>

        {/* Team Progress Cards */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {teamStatuses.map((team, index) => (
            <motion.div
              key={team.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className={`bg-white dark:bg-slate-800 rounded-xl shadow-md p-4 border-2 ${team.status === 'active'
                ? 'border-blue-500'
                : team.status === 'complete'
                  ? 'border-green-500'
                  : 'border-slate-200 dark:border-slate-700'
                }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-slate-900 dark:text-white">
                  {team.displayName}
                </span>
                {team.status === 'complete' && (
                  <CheckCircle className="w-5 h-5 text-green-500" />
                )}
                {team.status === 'active' && (
                  <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                )}
                {team.status === 'pending' && (
                  <Clock className="w-5 h-5 text-slate-400" />
                )}
              </div>
              <div className={`text-xs ${team.status === 'active'
                ? 'text-blue-600 dark:text-blue-400'
                : team.status === 'complete'
                  ? 'text-green-600 dark:text-green-400'
                  : 'text-slate-500'
                }`}>
                {team.status === 'complete' ? 'Completed' : team.status === 'active' ? 'In Progress' : 'Pending'}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Current Activity & Activity Log */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Current Activity */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-white dark:bg-slate-800 rounded-xl shadow-md p-6"
          >
            <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-blue-500" />
              Current Activity
            </h2>
            {status.current_team ? (
              <div className="space-y-2">
                <div className="text-lg font-semibold text-blue-600 dark:text-blue-400">
                  {teamStatuses.find(t => t.name === status.current_team)?.displayName}
                </div>
                <div className="text-sm text-slate-600 dark:text-slate-400">
                  Analyzing {status.current_team} aspects...
                </div>
                <div className="flex items-center gap-2 mt-4">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                  <span className="text-xs text-slate-500">Working...</span>
                </div>
              </div>
            ) : (
              <div className="text-slate-600 dark:text-slate-400">
                {status.status === 'completed' ? 'All teams completed!' : 'Initializing...'}
              </div>
            )}
          </motion.div>

          {/* Activity Log */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-white dark:bg-slate-800 rounded-xl shadow-md p-6"
          >
            <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-4">
              Activity Log
            </h2>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              <AnimatePresence>
                {logs.map((log, index) => (
                  <motion.div
                    key={`${log.timestamp}-${index}`}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 10 }}
                    className="text-sm border-l-2 border-blue-500 pl-3 py-1"
                  >
                    <div className="text-xs text-slate-500 dark:text-slate-400">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </div>
                    <div className="text-slate-700 dark:text-slate-300">
                      {log.message}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
              {logs.length === 0 && (
                <div className="text-slate-500 dark:text-slate-400 text-sm">
                  No activity logs yet...
                </div>
              )}
            </div>
          </motion.div>
        </div>

        {/* Results Panel (when complete) */}
        <AnimatePresence>
          {status.status === 'completed' && results && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6"
            >
              <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-4">
                Final Recommendation
              </h2>
              <div className="space-y-4">
                <div className="text-xl font-semibold">
                  {results.go_no_go_recommendation || 'Analysis Complete'}
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                  <div className="bg-slate-50 dark:bg-slate-700 rounded-lg p-4">
                    <div className="text-sm text-slate-600 dark:text-slate-400">Total Findings</div>
                    <div className="text-2xl font-bold text-slate-900 dark:text-white">
                      {results.key_findings?.length || 0}
                    </div>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-700 rounded-lg p-4">
                    <div className="text-sm text-slate-600 dark:text-slate-400">Teams Completed</div>
                    <div className="text-2xl font-bold text-slate-900 dark:text-white">
                      {Object.keys(results.team_results || {}).length}
                    </div>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-700 rounded-lg p-4">
                    <div className="text-sm text-slate-600 dark:text-slate-400">Duration</div>
                    <div className="text-2xl font-bold text-slate-900 dark:text-white">
                      {formatTime(status.elapsed_time_seconds)}
                    </div>
                  </div>
                </div>

                {/* Synthesized Messages Section */}
                {results.messages && results.messages.length > 0 && (
                  <div className="mt-6">
                    <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-3">
                      Agent Messages
                    </h3>
                    <div className="max-h-96 overflow-y-auto space-y-2 bg-slate-50 dark:bg-slate-700 rounded-lg p-4">
                      {results.messages.map((msg: any, index: number) => (
                        <div
                          key={index}
                          className="border-l-2 border-blue-500 pl-3 py-2"
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-semibold text-blue-600 dark:text-blue-400">
                              {msg.name || msg.role || 'agent'}
                            </span>
                            <span className="text-xs text-slate-500 dark:text-slate-400">
                              {msg.role}
                            </span>
                          </div>
                          <div className="text-sm text-slate-700 dark:text-slate-300">
                            {msg.content}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error Panel */}
        <AnimatePresence>
          {status.status === 'error' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-red-50 dark:bg-red-900/20 border-2 border-red-500 rounded-xl p-6"
            >
              <div className="flex items-center gap-2 text-red-600 dark:text-red-400 mb-2">
                <AlertCircle className="w-6 h-6" />
                <h2 className="text-xl font-bold">Error Occurred</h2>
              </div>
              <p className="text-red-700 dark:text-red-300">
                {status.error || 'An unknown error occurred during due diligence analysis.'}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

