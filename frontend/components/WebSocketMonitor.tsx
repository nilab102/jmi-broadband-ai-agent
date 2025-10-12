'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Database, X, Copy, Trash2 } from 'lucide-react'
import { config } from '@/lib/config'

interface WebSocketMessage {
  id: string
  timestamp: Date
  type: string
  data: any
  raw: string
}

interface WebSocketMonitorProps {
  isConnected: boolean
  onConnect?: () => void
  onDisconnect?: () => void
}

export function WebSocketMonitor({ isConnected, onConnect, onDisconnect }: WebSocketMonitorProps) {
  const [messages, setMessages] = useState<WebSocketMessage[]>([])
  const [isExpanded, setIsExpanded] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Listen for WebSocket messages
  useEffect(() => {
    const handleWebSocketMessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data)
        const newMessage: WebSocketMessage = {
          id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date(),
          type: data.type || 'unknown',
          data: data,
          raw: event.data
        }
        
        setMessages(prev => [...prev, newMessage])
        console.log('🔍 WebSocket Monitor received:', newMessage)
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }

    // Add event listener to window for WebSocket messages
    window.addEventListener('websocket-message', (event: any) => {
      handleWebSocketMessage(event.detail)
    })

    return () => {
      window.removeEventListener('websocket-message', handleWebSocketMessage as any)
    }
  }, [])

  const copyMessage = (message: WebSocketMessage) => {
    navigator.clipboard.writeText(JSON.stringify(message, null, 2))
  }

  const clearMessages = () => {
    setMessages([])
  }

  const formatTimestamp = (date: Date) => {
    return date.toLocaleTimeString()
  }

  return (
    <div className="bg-white rounded-2xl shadow-xl border border-purple-100 overflow-hidden backdrop-blur-sm">
      <div className="bg-gradient-to-r from-purple-500 via-indigo-600 to-blue-500 px-6 py-4">
        <div className="flex items-center justify-between text-white">
          <div className="flex items-center space-x-3">
            <Database className="w-6 h-6" />
            <h2 className="text-lg font-semibold">MSSQL Search WebSocket Monitor</h2>
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
              Raw WebSocket Messages ({messages.length})
            </h3>
            <div className="flex items-center space-x-2">
              <button
                onClick={clearMessages}
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
            {messages.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <div className="text-4xl mb-2">🔍</div>
                <p>No WebSocket messages yet</p>
                <p className="text-sm">MSSQL search tool messages will appear here</p>
              </div>
            ) : (
              messages.map((message) => (
                <div key={message.id} className="bg-white rounded-lg border border-gray-200 p-4">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-medium text-gray-500">
                        {formatTimestamp(message.timestamp)}
                      </span>
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        message.type === 'mssql_search_result' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-blue-100 text-blue-800'
                      }`}>
                        {message.type}
                      </span>
                    </div>
                    <button
                      onClick={() => copyMessage(message)}
                      className="text-gray-400 hover:text-gray-600"
                      title="Copy message"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-gray-700">
                      Message Type: {message.type}
                    </div>
                    
                    {message.type === 'mssql_search_result' && (
                      <div className="bg-green-50 border border-green-200 rounded p-3">
                        <div className="text-sm font-medium text-green-800 mb-2">
                          MSSQL Search Result:
                        </div>
                        <pre className="text-xs text-green-700 overflow-x-auto">
                          {JSON.stringify(message.data, null, 2)}
                        </pre>
                      </div>
                    )}
                    
                    <details className="text-sm">
                      <summary className="cursor-pointer text-gray-600 hover:text-gray-800">
                        Raw JSON Data
                      </summary>
                      <pre className="mt-2 text-xs bg-gray-100 p-2 rounded overflow-x-auto">
                        {message.raw}
                      </pre>
                    </details>
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>
      )}
    </div>
  )
}
