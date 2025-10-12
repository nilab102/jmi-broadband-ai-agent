'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Database, X, Copy, Trash2, Search, CheckCircle, AlertCircle, Clock, Play } from 'lucide-react'
import { config } from '@/lib/config'

interface ToolResult {
  id: string
  timestamp: Date
  type: string
  toolName: string
  action: string
  parameters: Record<string, any>
  result: any
  success: boolean
  executionTime?: number
  raw: string
}

interface ToolsResultsDisplayProps {
  isConnected: boolean
  onConnect?: () => void
  onDisconnect?: () => void
}

export function ToolsResultsDisplay({ isConnected, onConnect, onDisconnect }: ToolsResultsDisplayProps) {
  const [toolResults, setToolResults] = useState<ToolResult[]>([])
  const [isExpanded, setIsExpanded] = useState(true)
  const [filter, setFilter] = useState<string>('all')
  const resultsEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    resultsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [toolResults])

  // Listen for tool results from WebSocket
  useEffect(() => {
    const handleToolResult = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data)
        console.log('🔧 Tool result received:', data)
        
        // Create a new tool result entry
        const newResult: ToolResult = {
          id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date(),
          type: data.type || 'unknown',
          toolName: data.tool_name || data.toolName || 'Unknown Tool',
          action: data.action || 'Unknown Action',
          parameters: data.parameters || data.params || {},
          result: data.result || data.data || data,
          success: data.success !== false, // Default to true unless explicitly false
          executionTime: data.execution_time || data.executionTime,
          raw: event.data
        }
        
        setToolResults(prev => [...prev, newResult])
      } catch (error) {
        console.error('Error parsing tool result:', error)
      }
    }

    // Listen for tool WebSocket messages
    window.addEventListener('websocket-message', (event: any) => {
      handleToolResult(event.detail)
    })

    return () => {
      window.removeEventListener('websocket-message', handleToolResult as any)
    }
  }, [])

  const copyResult = (result: ToolResult) => {
    navigator.clipboard.writeText(JSON.stringify(result, null, 2))
  }

  const clearResults = () => {
    setToolResults([])
  }

  const formatTimestamp = (date: Date) => {
    return date.toLocaleTimeString()
  }

  const getTypeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'mssql_search_result':
      case 'database_search':
        return <Database className="w-4 h-4" />
      case 'report_generation':
        return <Search className="w-4 h-4" />
      case 'navigation_command':
        return <Play className="w-4 h-4" />
      default:
        return <CheckCircle className="w-4 h-4" />
    }
  }

  const getStatusColor = (success: boolean) => {
    return success ? 'text-green-600' : 'text-red-600'
  }

  const getStatusIcon = (success: boolean) => {
    return success ? (
      <CheckCircle className="w-4 h-4 text-green-600" />
    ) : (
      <AlertCircle className="w-4 h-4 text-red-600" />
    )
  }

  const filteredResults = toolResults.filter(result => {
    if (filter === 'all') return true
    if (filter === 'success') return result.success
    if (filter === 'error') return !result.success
    return result.type.toLowerCase().includes(filter.toLowerCase())
  })

  const renderResultContent = (result: ToolResult) => {
    // Special rendering for different tool types
    switch (result.type) {
      case 'mssql_search_result':
        return (
          <div className="space-y-2">
            <div className="bg-blue-50 border border-blue-200 rounded p-3">
              <div className="text-sm font-medium text-blue-800 mb-2">
                Database Search Result:
              </div>
              {result.result && (
                <div className="text-sm text-blue-700">
                  <div><strong>Query:</strong> {result.parameters?.query || 'N/A'}</div>
                  <div><strong>Results Count:</strong> {result.result?.length || 0}</div>
                  {result.result?.slice(0, 3).map((row: any, idx: number) => (
                    <div key={idx} className="mt-2 p-2 bg-blue-100 rounded text-xs">
                      <pre>{JSON.stringify(row, null, 2)}</pre>
                    </div>
                  ))}
                  {result.result?.length > 3 && (
                    <div className="text-xs text-blue-600 mt-1">
                      ... and {result.result.length - 3} more results
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )

      case 'report_generation':
        return (
          <div className="space-y-2">
            <div className="bg-green-50 border border-green-200 rounded p-3">
              <div className="text-sm font-medium text-green-800 mb-2">
                Report Generation Result:
              </div>
              <div className="text-sm text-green-700">
                <div><strong>Report Type:</strong> {result.parameters?.report_type || 'N/A'}</div>
                <div><strong>Status:</strong> {result.result?.status || 'Unknown'}</div>
                {result.result?.file_path && (
                  <div><strong>File:</strong> {result.result.file_path}</div>
                )}
                {result.result?.url && (
                  <div>
                    <strong>URL:</strong> 
                    <a href={result.result.url} target="_blank" rel="noopener noreferrer" 
                       className="text-green-600 hover:text-green-800 ml-1">
                      View Report
                    </a>
                  </div>
                )}
              </div>
            </div>
          </div>
        )

      case 'navigation_command':
        return (
          <div className="space-y-2">
            <div className="bg-purple-50 border border-purple-200 rounded p-3">
              <div className="text-sm font-medium text-purple-800 mb-2">
                Navigation Command:
              </div>
              <div className="text-sm text-purple-700">
                <div><strong>Action:</strong> {result.action}</div>
                <div><strong>Target:</strong> {result.parameters?.target || result.parameters?.url || 'N/A'}</div>
                {result.result?.message && (
                  <div><strong>Result:</strong> {result.result.message}</div>
                )}
              </div>
            </div>
          </div>
        )

      default:
        return (
          <div className="bg-gray-50 border border-gray-200 rounded p-3">
            <div className="text-sm font-medium text-gray-800 mb-2">
              Tool Result:
            </div>
            <pre className="text-xs text-gray-700 overflow-x-auto">
              {JSON.stringify(result.result, null, 2)}
            </pre>
          </div>
        )
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow-xl border border-indigo-100 overflow-hidden backdrop-blur-sm">
      <div className="bg-gradient-to-r from-indigo-500 via-purple-600 to-pink-500 px-6 py-4">
        <div className="flex items-center justify-between text-white">
          <div className="flex items-center space-x-3">
            <Search className="w-6 h-6" />
            <h2 className="text-lg font-semibold">Tools Results Display</h2>
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'} animate-pulse`} />
            <span className="text-sm">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
            {onConnect && onDisconnect && (
              <button
                onClick={isConnected ? onDisconnect : onConnect}
                className="text-white hover:text-gray-200 text-sm px-2 py-1 rounded border border-white/30"
              >
                {isConnected ? 'Disconnect' : 'Connect'}
              </button>
            )}
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-white hover:text-gray-200"
            >
              {isExpanded ? '−' : '+'}
            </button>
          </div>
        </div>
      </div>
      
      {isExpanded && (
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-800">
              Tool Execution Results ({filteredResults.length})
            </h3>
            <div className="flex items-center space-x-2">
              {/* Filter Dropdown */}
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="text-sm border border-gray-300 rounded px-2 py-1"
              >
                <option value="all">All Results</option>
                <option value="success">Successful</option>
                <option value="error">Errors</option>
                <option value="mssql">MSSQL Search</option>
                <option value="report">Report Generation</option>
                <option value="navigation">Navigation</option>
              </select>
              
              <button
                onClick={clearResults}
                className="flex items-center space-x-1 text-sm text-gray-500 hover:text-red-600"
              >
                <Trash2 className="w-4 h-4" />
                <span>Clear</span>
              </button>
              
              <button
                onClick={async () => {
                  try {
                    const response = await fetch(config.api.testDatabaseSearch)
                    const data = await response.json()
                    console.log('Test result:', data)
                  } catch (error) {
                    console.error('Test failed:', error)
                  }
                }}
                className="flex items-center space-x-1 text-sm text-blue-500 hover:text-blue-700"
              >
                <span>Test Tool</span>
              </button>
            </div>
          </div>
          
          <div className="h-96 overflow-y-auto space-y-3 p-4 bg-gray-50 rounded-lg">
            {filteredResults.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <div className="text-4xl mb-2">🔧</div>
                <p>No tool results yet</p>
                <p className="text-sm">
                  {toolResults.length === 0 
                    ? "Tool execution results will appear here when you use voice commands"
                    : `No results match the "${filter}" filter`
                  }
                </p>
              </div>
            ) : (
              filteredResults.map((result) => (
                <div key={result.id} className="bg-white rounded-lg border border-gray-200 p-4">
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-medium text-gray-500">
                        {formatTimestamp(result.timestamp)}
                      </span>
                      <div className="flex items-center space-x-1">
                        {getTypeIcon(result.type)}
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          result.success 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {result.toolName}
                        </span>
                      </div>
                      {getStatusIcon(result.success)}
                      {result.executionTime && (
                        <div className="flex items-center space-x-1 text-xs text-gray-500">
                          <Clock className="w-3 h-3" />
                          <span>{result.executionTime}ms</span>
                        </div>
                      )}
                    </div>
                    <button
                      onClick={() => copyResult(result)}
                      className="text-gray-400 hover:text-gray-600"
                      title="Copy result"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                  </div>
                  
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="text-sm font-medium text-gray-700">
                        Action: {result.action}
                      </div>
                      <div className={`text-sm font-medium ${getStatusColor(result.success)}`}>
                        {result.success ? 'Success' : 'Failed'}
                      </div>
                    </div>
                    
                    {/* Parameters */}
                    {Object.keys(result.parameters).length > 0 && (
                      <div className="bg-gray-50 rounded p-2">
                        <div className="text-sm font-medium text-gray-700 mb-1">Parameters:</div>
                        <div className="text-xs text-gray-600">
                          {Object.entries(result.parameters).map(([key, value]) => (
                            <div key={key}>
                              <strong>{key}:</strong> {String(value)}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Tool-specific content */}
                    {renderResultContent(result)}
                    
                    {/* Raw JSON */}
                    <details className="text-sm">
                      <summary className="cursor-pointer text-gray-600 hover:text-gray-800">
                        Raw JSON Data
                      </summary>
                      <pre className="mt-2 text-xs bg-gray-100 p-2 rounded overflow-x-auto">
                        {result.raw}
                      </pre>
                    </details>
                  </div>
                </div>
              ))
            )}
            <div ref={resultsEndRef} />
          </div>
        </div>
      )}
    </div>
  )
}
