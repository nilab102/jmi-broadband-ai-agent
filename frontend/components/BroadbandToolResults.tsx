'use client'

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useUserContext } from '@/lib/userContext'
import { usePageContext } from '@/lib/pageContext'
import { config } from '@/lib/config'
import {
  Wifi, Copy, ExternalLink, CheckCircle, AlertCircle, Clock,
  MapPin, Zap, Calendar, Phone, Building, Search, Filter, Globe,
  TrendingUp, DollarSign, Award, ChevronDown, ChevronUp, Home, PlusCircle
} from 'lucide-react'
import { SearchParametersCard } from './SearchParametersCard'
import { GeneratedUrlCard } from './GeneratedUrlCard'
import { ScrapedDataCard } from './ScrapedDataCard'
import { RecommendationsCard } from './RecommendationsCard'
import { ProviderComparisonCard } from './ProviderComparisonCard'
import { NoResultsCard } from './NoResultsCard'

interface BroadbandToolResult {
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

interface BroadbandToolResultsProps {
  isConnected: boolean
  onConnect?: () => void
  onDisconnect?: () => void
}

export function BroadbandToolResults({ isConnected, onConnect, onDisconnect }: BroadbandToolResultsProps) {
  const [toolResults, setToolResults] = useState<BroadbandToolResult[]>([])
  const [filter, setFilter] = useState<string>('all')
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set())
  const [toolWebSocketConnected, setToolWebSocketConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [manualControl, setManualControl] = useState(false)
  const [showDebug, setShowDebug] = useState(false)
  const [debugMessages, setDebugMessages] = useState<string[]>([])
  const [autoScroll, setAutoScroll] = useState(true)
  const [userScrolled, setUserScrolled] = useState(false)

  const toolWebSocketRef = useRef<WebSocket | null>(null)
  const resultsContainerRef = useRef<HTMLDivElement | null>(null)
  const { userId } = useUserContext()
  const { currentPage } = usePageContext()

  const connectToolWebSocket = () => {
    if (toolWebSocketRef.current?.readyState === WebSocket.OPEN) {
      console.log('🔧 Broadband Tool WebSocket already connected')
      return
    }

    if (!userId || !userId.trim()) {
      console.warn('🔧 Broadband Tool: Cannot connect - userId not available')
      setConnectionError('User ID is not set. Please set a valid User ID first.')
      return
    }

    setIsConnecting(true)
    setConnectionError(null)

    const toolWsUrl = config.websocket.tools(userId.trim(), currentPage)
    console.log('🔧 Broadband Tool WebSocket URL:', toolWsUrl)
    console.log('🔧 Broadband Tool Current page context:', currentPage)
    console.log('🔧 Broadband Tool Current user ID:', userId)

    const toolWs = new WebSocket(toolWsUrl)

    toolWs.onopen = () => {
      console.log('✅ Broadband Tool WebSocket connected successfully')
      setToolWebSocketConnected(true)
      setIsConnecting(false)
    }

    toolWs.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        const timestamp = new Date().toLocaleTimeString()
        
        // Add to debug messages
        setDebugMessages(prev => [...prev.slice(-9), `[${timestamp}] Received: ${JSON.stringify(data).substring(0, 100)}...`])
        
        console.log('📡 Broadband Tool WebSocket RAW message received:', data)
        console.log('📡 Message structure - type:', data.type, 'action:', data.action, 'data:', data.data)

        // PROCESS ALL MESSAGES - Don't filter anything
        const newResult: BroadbandToolResult = {
          id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date(),
          type: data.type || 'broadband_action',
          toolName: data.tool_name || data.toolName || 'Broadband Tool',
          action: data.action || 'tool_execution',
          parameters: data.parameters || data.params || {},
          result: data.result || data.data || data,
          success: data.success !== false,
          executionTime: data.execution_time || data.executionTime,
          raw: event.data
        }

        console.log('✅ Processing and adding tool result:', newResult.action, newResult)
        setToolResults(prev => {
          const updated = [...prev, newResult]
          console.log('📊 Total tool results now:', updated.length)
          return updated
        })

        // AUTO-OPEN URL if action is "open_url"
        if (newResult.action === 'open_url') {
          const urlToOpen = newResult.result?.url || newResult.result?.value
          if (urlToOpen) {
            console.log('🌐 AUTO-OPENING URL:', urlToOpen)
            window.open(urlToOpen, '_blank', 'noopener,noreferrer')
            setDebugMessages(prev => [...prev.slice(-9), `[${timestamp}] 🌐 Auto-opened URL: ${urlToOpen.substring(0, 50)}...`])
          }
        }
      } catch (error) {
        console.error('❌ Error parsing broadband tool result:', error, 'Raw data:', event.data)
        setDebugMessages(prev => [...prev.slice(-9), `[ERROR] Failed to parse message`])
      }
    }

    toolWs.onclose = (event) => {
      console.log('🔌 Broadband Tool WebSocket disconnected:', event.code, event.reason)
      setToolWebSocketConnected(false)
      setIsConnecting(false)
      
      // Show user-friendly disconnect message
      if (event.code !== 1000) { // 1000 = normal closure
        const timestamp = new Date().toLocaleTimeString()
        setDebugMessages(prev => [...prev.slice(-9), `[${timestamp}] ⚠️ Disconnected (code: ${event.code})`])
        
        // Auto-reconnect after 3 seconds if not manual closure
        if (!manualControl && userId) {
          setTimeout(() => {
            console.log('🔄 Auto-reconnecting Tool WebSocket...')
            connectToolWebSocket()
          }, 3000)
        }
      }
    }

    toolWs.onerror = (error) => {
      console.error('❌ Broadband Tool WebSocket error:', error)
      setToolWebSocketConnected(false)
      setIsConnecting(false)
      const timestamp = new Date().toLocaleTimeString()
      setConnectionError('Failed to connect to tool WebSocket. Will retry...')
      setDebugMessages(prev => [...prev.slice(-9), `[${timestamp}] ❌ WebSocket error occurred`])
    }

    toolWebSocketRef.current = toolWs
  }

  const disconnectToolWebSocket = () => {
    if (toolWebSocketRef.current) {
      console.log('🔌 Manually disconnecting Broadband Tool WebSocket')
      toolWebSocketRef.current.close()
      toolWebSocketRef.current = null
      setToolWebSocketConnected(false)
      setIsConnecting(false)
      setConnectionError(null)
    }
  }

  // Auto-scroll effect - scroll when new results arrive
  useEffect(() => {
    if (autoScroll && !userScrolled && resultsContainerRef.current && toolResults.length > 0) {
      // Small delay to ensure DOM is updated
      setTimeout(() => {
        if (resultsContainerRef.current) {
          resultsContainerRef.current.scrollTo({
            top: resultsContainerRef.current.scrollHeight,
            behavior: 'smooth'
          })
        }
      }, 100)
    }
  }, [toolResults, autoScroll, userScrolled])

  // Handle manual scrolling - disable auto-scroll if user scrolls up
  const handleScroll = useCallback(() => {
    if (!resultsContainerRef.current) return
    
    const { scrollTop, scrollHeight, clientHeight } = resultsContainerRef.current
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50
    
    // If user scrolls up, disable auto-scroll
    if (!isAtBottom && autoScroll) {
      setUserScrolled(true)
      console.log('👆 User scrolled up - auto-scroll paused')
    }
    
    // If user scrolls back to bottom, re-enable auto-scroll
    if (isAtBottom && userScrolled) {
      setUserScrolled(false)
      console.log('👇 User scrolled to bottom - auto-scroll resumed')
    }
  }, [autoScroll, userScrolled])

  // Auto-connect when voice/chat WebSocket connects OR when manual control is disabled
  useEffect(() => {
    // Connect if: (voice is connected OR manual control is off) AND userId is available
    const shouldConnect = (isConnected || !manualControl) && userId && userId.trim()
    
    if (shouldConnect && !toolWebSocketRef.current) {
      console.log('🔌 Connecting Tool WebSocket (Voice connected:', isConnected, ', Manual:', manualControl, ')')
      connectToolWebSocket()
    }

    // Cleanup on unmount
    return () => {
      if (toolWebSocketRef.current) {
        toolWebSocketRef.current.close()
        toolWebSocketRef.current = null
      }
    }
  }, [userId, currentPage, manualControl, isConnected])

  // Handle manual control toggle
  useEffect(() => {
    if (manualControl && toolWebSocketRef.current) {
      // If switching to manual control while connected, keep the connection
      console.log('🔧 Manual control enabled, preserving existing connection')
    }
  }, [manualControl])

  // Handle userId changes - reconnect with new userId
  useEffect(() => {
    console.log('👤 Broadband Tool: User ID changed, reconnecting...')

    // Close existing connection
    if (toolWebSocketRef.current?.readyState === WebSocket.OPEN) {
      console.log('🔌 Broadband Tool: Closing existing WebSocket due to user ID change')
      toolWebSocketRef.current.close()
      toolWebSocketRef.current = null
      setToolWebSocketConnected(false)
    }

    // Reconnect after a short delay
    const reconnectTimeout = setTimeout(() => {
      if (userId && userId.trim()) {
        console.log('🔄 Broadband Tool: Reconnecting with new user ID...')
        // The useEffect above will handle reconnection
      }
    }, 1000)

    return () => clearTimeout(reconnectTimeout)
  }, [userId])

  const copyResult = (result: BroadbandToolResult) => {
    navigator.clipboard.writeText(JSON.stringify(result, null, 2))
  }

  const clearResults = () => {
    setToolResults([])
  }

  const toggleExpanded = (id: string) => {
    setExpandedResults(prev => {
      const newSet = new Set(prev)
      if (newSet.has(id)) {
        newSet.delete(id)
      } else {
        newSet.add(id)
      }
      return newSet
    })
  }

  const formatTimestamp = (date: Date) => {
    return date.toLocaleTimeString()
  }

  const filteredResults = toolResults.filter(result => {
    if (filter === 'all') return true
    if (filter === 'success') return result.success
    if (filter === 'error') return !result.success
    return result.type.toLowerCase().includes(filter.toLowerCase())
  })

  const openUrl = (url: string) => {
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer')
    }
  }

  const renderExtractedParams = (params: any) => {
    console.log('🔍 renderExtractedParams called with:', params)
    return <SearchParametersCard params={params} />
  }

  const renderGeneratedUrl = (url: string) => {
    console.log('🌐 renderGeneratedUrl called with:', url)
    return <GeneratedUrlCard url={url} onOpenUrl={openUrl} />
  }

  const renderScrapedData = (data: any) => {
    console.log('📊 renderScrapedData called with:', data)
    return <ScrapedDataCard data={data} />
  }

  const renderResultContent = (result: BroadbandToolResult) => {
    // The data structure from backend is: { type, action, data: { ...all the fields } }
    // result.result contains the entire message, so we need to look in result.result for the data
    const data = result.result
    const isExpanded = expandedResults.has(result.id)

    console.log('🎨 Rendering result content for action:', result.action, 'Data:', data)

    switch (result.action) {
      case 'url_generated':
        // Handle both data structures: test button uses generated_params, tool uses extracted_params
        const paramsToRender = data?.extracted_params || data?.generated_params
        // Handle both URL structures: test button uses value, tool uses generated_url  
        const urlToRender = data?.generated_url || data?.value
        return (
          <div className="space-y-4">
            {renderExtractedParams(paramsToRender)}
            {renderGeneratedUrl(urlToRender)}
          </div>
        )

      case 'open_url':
        const urlToOpen = data?.url || data?.value
        return (
          <div className="bg-gradient-to-br from-cyan-50 to-blue-50 rounded-xl p-5 border border-cyan-200 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-cyan-500 rounded-lg flex items-center justify-center">
                  <ExternalLink className="w-4 h-4 text-white" />
                </div>
                <div>
                  <span className="font-semibold text-cyan-900">URL Opened in New Tab</span>
                  <p className="text-xs text-cyan-600">Automatically opened</p>
                </div>
              </div>
              <button
                onClick={() => openUrl(urlToOpen)}
                className="flex items-center space-x-2 px-3 py-1.5 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg transition-colors text-sm"
              >
                <ExternalLink className="w-3 h-3" />
                <span>Open Again</span>
              </button>
            </div>
            <div className="bg-white border border-cyan-300 rounded-lg p-3">
              <code className="text-xs text-cyan-700 break-all">{urlToOpen}</code>
            </div>
          </div>
        )

      case 'data_scraped':
        return renderScrapedData(data?.scraped_data || data)

      case 'recommendations_generated':
        return <RecommendationsCard data={data} isExpanded={isExpanded} />

      case 'provider_comparison':
        return <ProviderComparisonCard data={data} />

      default:
        return (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <div className="text-sm font-medium text-gray-800 mb-2">Raw Data:</div>
            <pre className="text-xs text-gray-700 overflow-x-auto whitespace-pre-wrap">
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        )
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
      <div className="bg-gradient-to-r from-indigo-500 via-purple-600 to-pink-500 px-4 sm:px-6 py-3 sm:py-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-white">
          <div className="flex items-center space-x-3">
            <Wifi className="w-5 h-5 sm:w-6 sm:h-6" />
            <h2 className="text-base sm:text-lg font-semibold">Broadband Tool Results</h2>
          </div>
          <div className="flex items-center space-x-2 sm:space-x-3">
            {/* Manual Control Toggle */}
            <div className="flex items-center space-x-2">
              <span className="text-xs">Manual:</span>
              <button
                onClick={() => setManualControl(!manualControl)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  manualControl ? 'bg-green-400' : 'bg-gray-400'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    manualControl ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* Tool WebSocket Status */}
            <div className="flex items-center space-x-2 bg-white/20 rounded-lg px-3 py-1">
              <div className={`w-2 h-2 rounded-full ${
                toolWebSocketConnected ? 'bg-green-400' :
                isConnecting ? 'bg-yellow-400' : 'bg-red-400'
              } animate-pulse`} />
              <span className="text-xs font-medium">
                {toolWebSocketConnected ? 'Tool WS Connected' :
                 isConnecting ? 'Tool WS Connecting...' : 'Tool WS Disconnected'}
              </span>
            </div>

            {/* Voice WebSocket Status */}
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'} animate-pulse`} />
              <span className="text-xs">{isConnected ? 'Voice Connected' : 'Voice Disconnected'}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="p-4 sm:p-6">
        {/* Connection Status */}
        {connectionError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-red-500" />
              <span className="text-sm text-red-700">{connectionError}</span>
            </div>
          </div>
        )}

        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 mb-4">
          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
            <h3 className="text-base sm:text-lg font-semibold text-gray-800">Results ({filteredResults.length})</h3>
            {toolResults.length === 0 && !toolWebSocketConnected && (
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                Waiting for tool WebSocket connection...
              </span>
            )}
            {userScrolled && (
              <span className="text-xs text-orange-500 bg-orange-50 px-2 py-1 rounded flex items-center space-x-1">
                <span>⏸️</span>
                <span>Auto-scroll paused</span>
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {/* Auto-scroll Toggle */}
            <button
              onClick={() => {
                setAutoScroll(!autoScroll)
                if (!autoScroll) setUserScrolled(false) // Re-enable when turning on
              }}
              className={`text-xs px-2 sm:px-3 py-1.5 rounded-lg transition-colors ${
                autoScroll
                  ? 'bg-green-500 hover:bg-green-600 text-white'
                  : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
              }`}
              title={autoScroll ? 'Auto-scroll enabled' : 'Auto-scroll disabled'}
            >
              {autoScroll ? '↓ Auto' : '⏸️ Manual'}
            </button>
            {/* Manual Connect/Disconnect Buttons - only show when manual control is enabled */}
            {manualControl && (
              <>
                {!toolWebSocketConnected && !isConnecting ? (
                  <button
                    onClick={connectToolWebSocket}
                    className="text-sm bg-green-500 hover:bg-green-600 text-white px-3 py-1.5 rounded-lg transition-colors"
                    title="Connect to tool WebSocket"
                  >
                    Connect Tool
                  </button>
                ) : toolWebSocketConnected ? (
                  <button
                    onClick={disconnectToolWebSocket}
                    className="text-sm bg-red-500 hover:bg-red-600 text-white px-3 py-1.5 rounded-lg transition-colors"
                    title="Disconnect from tool WebSocket"
                  >
                    Disconnect Tool
                  </button>
                ) : null}
              </>
            )}

            {/* Debug Toggle */}
            <button
              onClick={() => setShowDebug(!showDebug)}
              className={`text-sm px-3 py-1.5 rounded-lg transition-colors ${
                showDebug 
                  ? 'bg-yellow-500 hover:bg-yellow-600 text-white' 
                  : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
              }`}
              title="Toggle debug panel"
            >
              Debug {showDebug ? 'ON' : 'OFF'}
            </button>

            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="text-sm border border-gray-300 rounded-lg px-3 py-1.5"
            >
              <option value="all">All Results</option>
              <option value="success">Successful</option>
              <option value="error">Errors</option>
            </select>
            <button
              onClick={clearResults}
              className="text-sm text-gray-500 hover:text-red-600 px-3 py-1.5"
            >
              Clear All
            </button>

            {/* Debug Test Button */}
            <button
              onClick={() => {
                // Create a test result that EXACTLY matches backend structure
                const backendMessage = {
                  type: 'url_action',
                  action: 'url_generated',
                  data: {
                    Action_type: 'url_generated',
                    param: 'url,postcode',
                    value: 'https://broadband.justmovein.co/packages?location=E14+9WB,E14 9WB',
                    page: 'broadband',
                    interaction_type: 'url_generation',
                    timestamp: new Date().toISOString(),
                    user_id: userId,
                    success: true,
                    generated_params: {
                      postcode: 'E149WB',
                      speed_in_mb: '100Mb',
                      contract_length: '',
                      phone_calls: 'Show me everything',
                      product_type: 'broadband,phone',
                      providers: '',
                      current_provider: '',
                      sort_by: 'Recommended',
                      new_line: ''
                    }
                  }
                }

                const testResult: BroadbandToolResult = {
                  id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                  timestamp: new Date(),
                  type: backendMessage.type,
                  toolName: 'Broadband Tool',
                  action: backendMessage.action,
                  parameters: {},
                  result: backendMessage.data,  // This is the key - data goes into result
                  success: true,
                  executionTime: 150,
                  raw: JSON.stringify(backendMessage)
                }
                console.log('🧪 Adding test tool result with backend structure:', testResult)
                setToolResults(prev => [...prev, testResult])
              }}
              className="text-sm text-blue-500 hover:text-blue-700 px-3 py-1.5"
              title="Add test result to verify display"
            >
              Test
            </button>
          </div>
        </div>

        {/* Debug Panel */}
        {showDebug && (
          <div className="mb-4 bg-gray-900 text-green-400 rounded-lg p-4 font-mono text-xs">
            <div className="flex justify-between items-center mb-2">
              <span className="font-semibold text-yellow-400">🔍 WebSocket Debug Log</span>
              <button
                onClick={() => setDebugMessages([])}
                className="text-red-400 hover:text-red-300 text-xs"
              >
                Clear Log
              </button>
            </div>
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {debugMessages.length === 0 ? (
                <p className="text-gray-500">No messages received yet...</p>
              ) : (
                debugMessages.map((msg, idx) => (
                  <div key={idx} className="text-green-400">{msg}</div>
                ))
              )}
            </div>
            <div className="mt-2 pt-2 border-t border-gray-700 text-gray-400">
              <div>Connection Status: {toolWebSocketConnected ? '✅ Connected' : '❌ Disconnected'}</div>
              <div>User ID: {userId || 'Not set'}</div>
              <div>Page: {currentPage}</div>
              <div>Total Results: {toolResults.length}</div>
            </div>
          </div>
        )}

        <div
          ref={resultsContainerRef}
          onScroll={handleScroll}
          className="space-y-4 max-h-[500px] sm:max-h-[600px] overflow-y-auto scroll-smooth"
        >
          {filteredResults.length === 0 ? (
            <NoResultsCard
              isConnected={toolWebSocketConnected}
              manualControl={manualControl}
              onConnect={connectToolWebSocket}
            />
          ) : (
            filteredResults.map((result) => {
              const isExpanded = expandedResults.has(result.id)

              // Get appropriate colors based on action type
              const getActionColors = (action: string) => {
                switch (action) {
                  case 'url_generated': return {
                    bg: 'from-blue-500 to-indigo-600',
                    text: 'text-blue-900',
                    border: 'border-blue-200',
                    bgLight: 'bg-blue-50'
                  }
                  case 'open_url': return {
                    bg: 'from-cyan-500 to-teal-600',
                    text: 'text-cyan-900',
                    border: 'border-cyan-200',
                    bgLight: 'bg-cyan-50'
                  }
                  case 'data_scraped': return {
                    bg: 'from-purple-500 to-pink-600',
                    text: 'text-purple-900',
                    border: 'border-purple-200',
                    bgLight: 'bg-purple-50'
                  }
                  case 'recommendations_generated': return {
                    bg: 'from-green-500 to-emerald-600',
                    text: 'text-green-900',
                    border: 'border-green-200',
                    bgLight: 'bg-green-50'
                  }
                  case 'provider_comparison': return {
                    bg: 'from-orange-500 to-red-600',
                    text: 'text-orange-900',
                    border: 'border-orange-200',
                    bgLight: 'bg-orange-50'
                  }
                  default: return {
                    bg: 'from-gray-500 to-slate-600',
                    text: 'text-gray-900',
                    border: 'border-gray-200',
                    bgLight: 'bg-gray-50'
                  }
                }
              }

              const colors = getActionColors(result.action)

              return (
                <div key={result.id} className={`rounded-xl border shadow-sm overflow-hidden hover:shadow-lg transition-all duration-200 ${colors.border} ${colors.bgLight}`}>
                  {/* Header with gradient background */}
                  <div className={`bg-gradient-to-r ${colors.bg} px-4 sm:px-5 py-3 sm:py-4 text-white`}>
                    <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2">
                      <div className="flex items-center space-x-3">
                        <div className={`w-3 h-3 rounded-full ${result.success ? 'bg-green-300' : 'bg-red-300'} shadow-sm`} />
                        <div>
                          <h4 className="font-bold text-white text-base sm:text-lg capitalize">
                            {result.action.replace('_', ' ')}
                          </h4>
                          <p className="text-xs text-white/80 opacity-90">
                            {formatTimestamp(result.timestamp)}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        {result.executionTime && (
                          <div className="flex items-center space-x-1 bg-white/20 rounded-full px-2 py-1">
                            <Clock className="w-3 h-3" />
                            <span className="text-xs font-medium">{result.executionTime}ms</span>
                          </div>
                        )}
                        <button
                          onClick={() => copyResult(result)}
                          className="p-1.5 rounded-full bg-white/20 hover:bg-white/30 transition-colors"
                          title="Copy result data"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => toggleExpanded(result.id)}
                          className="p-1.5 rounded-full bg-white/20 hover:bg-white/30 transition-colors"
                          title={isExpanded ? "Collapse details" : "Expand details"}
                        >
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Content */}
                  <div className="p-4 sm:p-5">
                    {renderResultContent(result)}

                    {/* Expandable raw data */}
                    {isExpanded && (
                      <div className="mt-6 pt-4 border-t border-gray-200">
                        <div className="flex items-center justify-between mb-3">
                          <h5 className="text-sm font-semibold text-gray-700">Raw JSON Data</h5>
                          <button
                            onClick={() => copyResult(result)}
                            className="text-xs text-blue-600 hover:text-blue-800 flex items-center space-x-1"
                          >
                            <Copy className="w-3 h-3" />
                            <span>Copy</span>
                          </button>
                        </div>
                        <div className="bg-gray-900 rounded-lg p-4 overflow-x-auto">
                          <pre className="text-xs text-green-400 whitespace-pre-wrap font-mono">
                            {JSON.stringify(JSON.parse(result.raw), null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
