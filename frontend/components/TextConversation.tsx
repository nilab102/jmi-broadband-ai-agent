'use client'

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { usePageContext } from '@/lib/pageContext'
import { useUserContext } from '@/lib/userContext'
import { config } from '@/lib/config'
import { Send, MessageCircle, AlertCircle } from 'lucide-react'

interface TextMessage {
  id: string
  type: 'user' | 'assistant' | 'system' | 'error'
  content: string
  timestamp: Date
  isAudio?: boolean
}

export function TextConversation() {
  const { currentPage, getPageDisplayName } = usePageContext()
  const { userId } = useUserContext()
  const [messages, setMessages] = useState<TextMessage[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  
  const websocketRef = useRef<WebSocket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const addMessage = useCallback((message: Omit<TextMessage, 'id' | 'timestamp'>) => {
    const newMessage: TextMessage = {
      ...message,
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date()
    }
    setMessages(prev => [...prev, newMessage])
  }, [])

  const connect = useCallback(() => {
    if (websocketRef.current?.readyState === WebSocket.OPEN) {
      console.log('📝 Text WebSocket already connected')
      return
    }

    // Guard: ensure userId is available before attempting connection
    if (!userId || !userId.trim()) {
      console.warn('📝 Cannot connect Text WebSocket: userId is not available')
      setConnectionError('User ID is not set. Please set a valid User ID first.')
      return
    }

    setIsConnecting(true)
    setConnectionError(null)

    const wsUrl = config.websocket.textConversation(userId, currentPage)
    console.log('📝 Connecting to text conversation WebSocket:', wsUrl)
    console.log('📝 Current page context:', currentPage)
    console.log('📝 Current user ID:', userId)
    
    const ws = new WebSocket(wsUrl)
    
    ws.onopen = () => {
      console.log('✅ Text conversation WebSocket connected')
      setIsConnected(true)
      setIsConnecting(false)
      addMessage({
        type: 'system',
        content: `Connected to text conversation on ${getPageDisplayName(currentPage)} page`
      })
    }
    
    ws.onmessage = (event) => {
      try {
        const response = event.data
        console.log('📥 Received text response:', response)
        addMessage({
          type: 'assistant',
          content: response
        })
      } catch (error) {
        console.error('Error parsing text message:', error)
        addMessage({
          type: 'error',
          content: 'Error parsing response from AI'
        })
      }
    }
    
    ws.onclose = (event) => {
      console.log('🔌 Text WebSocket disconnected:', event.code, event.reason)
      setIsConnected(false)
      setIsConnecting(false)
      addMessage({
        type: 'system',
        content: 'Text conversation disconnected'
      })
    }
    
    ws.onerror = (error) => {
      console.error('❌ Text WebSocket error:', error)
      setIsConnected(false)
      setIsConnecting(false)
      setConnectionError('Failed to connect to text conversation')
      addMessage({
        type: 'error',
        content: 'Failed to connect to text conversation'
      })
    }
    
    websocketRef.current = ws
  }, [currentPage, getPageDisplayName, addMessage, userId])

  const disconnect = useCallback(() => {
    if (websocketRef.current) {
      websocketRef.current.close()
      websocketRef.current = null
    }
    setIsConnected(false)
    setIsConnecting(false)
  }, [])

  const sendMessage = useCallback(async () => {
    if (!inputMessage.trim() || !isConnected) return

    const message = inputMessage.trim()
    setInputMessage('')
    
    addMessage({
      type: 'user',
      content: message
    })

    try {
      websocketRef.current?.send(message)
    } catch (error) {
      console.error('Error sending message:', error)
      addMessage({
        type: 'error',
        content: 'Failed to send message'
      })
    }
  }, [inputMessage, isConnected, addMessage])

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearMessages = () => {
    setMessages([])
  }

  // Handle userId changes - disconnect and notify user
  useEffect(() => {
    console.log('📝 User ID changed in text conversation:', userId)

    // Disconnect existing connection
    if (websocketRef.current) {
      console.log('🔌 Disconnecting text conversation WebSocket due to user ID change')
      websocketRef.current.close()
      websocketRef.current = null
      setIsConnected(false)
      setIsConnecting(false)
    }

    // Add system message about user ID change
    addMessage({
      type: 'system',
      content: `👤 User ID changed to: ${userId}. Please reconnect text conversation to continue.`
    })
  }, [userId, addMessage]) // Only trigger on userId changes

  // Don't auto-connect when component mounts or page changes
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-3 sm:space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500 px-4">
            <div className="text-center max-w-sm">
              <div className="w-16 h-16 mx-auto mb-4 bg-blue-100 rounded-full flex items-center justify-center">
                <MessageCircle className="w-8 h-8 text-blue-500" />
              </div>
              <p className="text-lg font-medium mb-2 text-gray-700">Start a conversation</p>
              <p className="text-sm text-gray-500">Ask me anything about broadband deals, providers, or comparisons</p>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] sm:max-w-xs lg:max-w-md px-3 sm:px-4 py-2 sm:py-3 rounded-2xl shadow-sm relative ${
                  message.type === 'user'
                    ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-br-md ml-auto'
                    : message.type === 'assistant'
                    ? 'bg-white text-gray-800 border border-gray-200 rounded-bl-md'
                    : message.type === 'error'
                    ? 'bg-red-50 text-red-800 border border-red-200 rounded-bl-md'
                    : 'bg-gray-50 text-gray-600 border border-gray-200 rounded-bl-md'
                }`}
              >
                <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                  {message.content}
                </p>
                <p className={`text-xs mt-2 ${
                  message.type === 'user' ? 'text-blue-100' : 'text-gray-400'
                }`}>
                  {message.timestamp.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </p>

                {/* Audio indicator for user messages */}
                {message.type === 'user' && message.isAudio && (
                  <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse" />
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 bg-white p-3 sm:p-4">
        <div className="flex space-x-2 sm:space-x-3">
          <div className="flex-1 relative">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  sendMessage()
                }
              }}
              placeholder={isConnected ? "Type your broadband query..." : !userId?.trim() ? "Please set User ID first..." : "Connecting..."}
              className={`w-full px-3 sm:px-4 py-2 sm:py-3 border rounded-xl resize-none focus:outline-none focus:ring-2 transition-all duration-200 ${
                !isConnected
                  ? !userId?.trim()
                    ? 'border-orange-300 bg-orange-50 focus:ring-orange-500'
                    : 'border-gray-300 bg-gray-50 focus:ring-gray-500'
                  : 'border-blue-300 bg-blue-50 focus:ring-blue-500'
              } text-sm sm:text-base disabled:bg-gray-50 disabled:text-gray-400`}
              rows={1}
              disabled={!isConnected}
            />

            {/* Character count for long messages */}
            {inputMessage.length > 100 && (
              <div className="absolute -top-6 right-0 text-xs text-gray-400">
                {inputMessage.length}/500
              </div>
            )}
          </div>

          <button
            onClick={sendMessage}
            disabled={!isConnected || !inputMessage.trim() || isConnecting || inputMessage.length > 500}
            className={`p-2 sm:p-3 rounded-xl font-medium transition-all duration-200 flex-shrink-0 ${
              !isConnected || !inputMessage.trim() || isConnecting || inputMessage.length > 500
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-gradient-to-r from-blue-500 to-purple-600 text-white hover:from-blue-600 hover:to-purple-700 shadow-lg hover:shadow-xl transform hover:scale-105'
            }`}
            title={!isConnected ? 'Connect to chat first' : !inputMessage.trim() ? 'Type a message first' : 'Send message'}
          >
            <Send className="w-4 h-4 sm:w-5 sm:h-5" />
          </button>
        </div>

        {/* Connection Status & Help */}
        <div className="mt-2 sm:mt-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs sm:text-sm">
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500' :
              !userId?.trim() ? 'bg-orange-500' :
              isConnecting ? 'bg-yellow-500' : 'bg-red-500'
            }`} />
            <span className={
              isConnected ? 'text-green-600' :
              !userId?.trim() ? 'text-orange-600' :
              isConnecting ? 'text-yellow-600' : 'text-red-600'
            }>
              {isConnecting ? 'Connecting...' :
               isConnected ? 'Connected' :
               !userId?.trim() ? 'Set User ID' : 'Disconnected'}
            </span>
          </div>

          {isConnected && (
            <div className="text-gray-500 text-center sm:text-right">
              <span className="hidden sm:inline">Press Enter to send • Shift+Enter for new line</span>
              <span className="sm:hidden">Tap send to submit</span>
            </div>
          )}
        </div>
      </div>

      {/* Connection Controls */}
      <div className="border-t border-gray-200 bg-white p-3 sm:p-4 shadow-sm">
        <div className="flex justify-center space-x-3">
          {!isConnected ? (
            <button
              onClick={connect}
              disabled={isConnecting || !userId?.trim()}
              className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                isConnecting || !userId?.trim()
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:from-green-600 hover:to-emerald-700 shadow-lg hover:shadow-xl transform hover:scale-105'
              }`}
              title={!userId?.trim() ? 'Please set a User ID first' : isConnecting ? 'Connecting...' : 'Connect to Chat'}
            >
              {isConnecting ? 'Connecting...' : 'Connect to Chat'}
            </button>
          ) : (
            <button
              onClick={disconnect}
              className="px-4 py-2 bg-gradient-to-r from-red-500 to-pink-600 text-white rounded-lg font-medium hover:from-red-600 hover:to-pink-700 shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-200"
            >
              Disconnect
            </button>
          )}
        </div>

        {/* Connection Status Info */}
        <div className="mt-2 text-center">
          <div className="text-xs text-gray-500">
            {!userId?.trim() ? (
              <span className="text-orange-600">⚠️ Please set a User ID in Settings to connect</span>
            ) : isConnected ? (
              <span className="text-green-600">✅ Connected and ready to chat</span>
            ) : (
              <span className="text-gray-500">Click "Connect to Chat" to start the conversation</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
