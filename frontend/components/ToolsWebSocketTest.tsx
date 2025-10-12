'use client'

import React, { useState, useRef } from 'react'
import { config } from '@/lib/config'
import { Play, Send, Wifi, WifiOff } from 'lucide-react'

export function ToolsWebSocketTest() {
  const [isConnected, setIsConnected] = useState(false)
  const [messages, setMessages] = useState<string[]>([])
  const [testMessage, setTestMessage] = useState('{"type": "test", "action": "ping", "timestamp": "' + new Date().toISOString() + '"}')
  const wsRef = useRef<WebSocket | null>(null)

  const connect = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    const toolsWsUrl = config.websocket.tools(config.defaultUserId)
    console.log('🔧 Connecting to Tools WebSocket:', toolsWsUrl)
    
    const ws = new WebSocket(toolsWsUrl)
    
    ws.onopen = () => {
      console.log('✅ Tools WebSocket connected')
      setIsConnected(true)
      setMessages(prev => [...prev, `✅ Connected to ${toolsWsUrl}`])
    }
    
    ws.onmessage = (event) => {
      console.log('📨 Received message:', event.data)
      setMessages(prev => [...prev, `📨 Received: ${event.data}`])
      
      // Dispatch to other components
      window.dispatchEvent(new CustomEvent('websocket-message', {
        detail: event
      }))
    }
    
    ws.onclose = (event) => {
      console.log('🔌 Tools WebSocket disconnected:', event.code, event.reason)
      setIsConnected(false)
      setMessages(prev => [...prev, `🔌 Disconnected: ${event.reason || 'Connection closed'}`])
    }
    
    ws.onerror = (error) => {
      console.error('❌ Tools WebSocket error:', error)
      setIsConnected(false)
      setMessages(prev => [...prev, `❌ Connection error`])
    }
    
    wsRef.current = ws
  }

  const disconnect = () => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
  }

  const sendMessage = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN && testMessage.trim()) {
      try {
        // Validate JSON
        JSON.parse(testMessage)
        wsRef.current.send(testMessage)
        setMessages(prev => [...prev, `📤 Sent: ${testMessage}`])
      } catch (error) {
        setMessages(prev => [...prev, `❌ Invalid JSON: ${error}`])
      }
    }
  }

  const clearMessages = () => {
    setMessages([])
  }

  const sendTestMessages = () => {
    const testMessages = [
      {
        type: "mssql_search_result",
        action: "search_customers",
        parameters: { query: "SELECT * FROM customers WHERE status = 'active'" },
        result: [
          { id: 1, name: "John Doe", status: "active" },
          { id: 2, name: "Jane Smith", status: "active" }
        ],
        success: true,
        execution_time: 45
      },
      {
        type: "report_generation",
        action: "create_sales_report",
        parameters: { report_type: "monthly", period: "2024-01" },
        result: {
          status: "completed",
          file_path: "/reports/sales_2024_01.pdf",
          url: "https://example.com/reports/sales_2024_01.pdf"
        },
        success: true,
        execution_time: 1250
      },
      {
        type: "navigation_command",
        action: "navigate_to_page",
        parameters: { target: "/dashboard", url: "https://example.com/dashboard" },
        result: { message: "Navigation successful" },
        success: true,
        execution_time: 200
      }
    ]

    testMessages.forEach((msg, index) => {
      setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          const message = JSON.stringify(msg)
          wsRef.current.send(message)
          setMessages(prev => [...prev, `📤 Test ${index + 1}: ${msg.type}`])
        }
      }, index * 1000)
    })
  }

  return (
    <div className="bg-white rounded-2xl shadow-xl border border-green-100 overflow-hidden backdrop-blur-sm">
      <div className="bg-gradient-to-r from-green-500 via-emerald-600 to-teal-500 px-6 py-4">
        <div className="flex items-center justify-between text-white">
          <div className="flex items-center space-x-3">
            {isConnected ? <Wifi className="w-6 h-6" /> : <WifiOff className="w-6 h-6" />}
            <h2 className="text-lg font-semibold">Tools WebSocket Test</h2>
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'} animate-pulse`} />
            <span className="text-sm">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>
      
      <div className="p-6 space-y-4">
        {/* Connection Controls */}
        <div className="flex items-center space-x-2">
          <button
            onClick={isConnected ? disconnect : connect}
            className={`px-4 py-2 rounded-lg text-white font-medium ${
              isConnected 
                ? 'bg-red-500 hover:bg-red-600' 
                : 'bg-green-500 hover:bg-green-600'
            }`}
          >
            {isConnected ? 'Disconnect' : 'Connect'}
          </button>
          
          <button
            onClick={sendTestMessages}
            disabled={!isConnected}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center space-x-1"
          >
            <Play className="w-4 h-4" />
            <span>Send Test Results</span>
          </button>
          
          <button
            onClick={clearMessages}
            className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600"
          >
            Clear
          </button>
        </div>

        {/* Custom Message */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">Custom Message (JSON):</label>
          <div className="flex space-x-2">
            <textarea
              value={testMessage}
              onChange={(e) => setTestMessage(e.target.value)}
              placeholder="Enter JSON message to send..."
              className="flex-1 p-2 border border-gray-300 rounded-lg resize-none h-20 text-sm font-mono"
            />
            <button
              onClick={sendMessage}
              disabled={!isConnected}
              className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Messages Log */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-gray-700">Connection Log:</h3>
          <div className="h-40 overflow-y-auto bg-gray-50 border border-gray-200 rounded-lg p-3">
            {messages.length === 0 ? (
              <div className="text-gray-500 text-sm text-center py-8">
                No messages yet. Connect to start testing.
              </div>
            ) : (
              <div className="space-y-1">
                {messages.map((message, index) => (
                  <div key={index} className="text-sm text-gray-700 font-mono">
                    <span className="text-gray-500">[{new Date().toLocaleTimeString()}]</span> {message}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Info */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm">
          <div className="text-blue-800 font-medium mb-1">WebSocket Endpoint:</div>
          <div className="text-blue-700 font-mono text-xs break-all">
            {config.websocket.tools(config.defaultUserId)}
          </div>
          <div className="text-blue-600 text-xs mt-2">
            This component tests the direct connection to the tools WebSocket endpoint. 
            Messages sent here will appear in the Tools Results Display component above.
          </div>
        </div>
      </div>
    </div>
  )
}
