'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { config, getRTVIConfig } from './config'
import { usePageContext } from './pageContext'
import { useUserContext } from './userContext'

export interface VoiceMessage {
  id: string
  type: 'user' | 'assistant' | 'system' | 'error' | 'tool_call' | 'tool_result'
  content: string
  timestamp: Date
  isAudio?: boolean
  toolCall?: ToolCall
  toolResult?: ToolResult
}

export interface ToolCall {
  toolName: string
  action: string
  parameters: Record<string, any>
  timestamp: Date
  status: 'pending' | 'executing' | 'completed' | 'failed'
}

export interface ToolResult {
  toolName: string
  action: string
  result: any
  timestamp: Date
  success: boolean
  displayData?: {
    title: string
    summary: string
    details: Record<string, any>
    visualizations?: any[]
  }
}

interface VoiceClientHook {
  isConnected: boolean
  isInConversation: boolean
  connectionStatus: string
  messages: VoiceMessage[]
  toolCallsInProgress: ToolCall[]
  recentToolResults: ToolResult[]
  isToolsConnected: boolean
  
  // Connection methods
  connect: () => void
  disconnect: () => void
  connectToolWebSocket: () => void
  
  // Utility methods
  clearMessages: () => void
  clearToolCalls: () => void
}

export function useVoiceClient(): VoiceClientHook {
  // Get current page and user ID from contexts
  const { currentPage } = usePageContext()
  const { userId } = useUserContext()
  
  // Connection state
  const [isConnected, setIsConnected] = useState(false)
  const [isInConversation, setIsInConversation] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState('Disconnected')
  const [messages, setMessages] = useState<VoiceMessage[]>([])
  
  // Tool state
  const [toolCallsInProgress, setToolCallsInProgress] = useState<ToolCall[]>([])
  const [recentToolResults, setRecentToolResults] = useState<ToolResult[]>([])
  const [isToolsConnected, setIsToolsConnected] = useState(false)
  
  // Client refs
  const mainWebSocketRef = useRef<any>(null) // RTVI client
  const toolWebSocketRef = useRef<WebSocket | null>(null)
  const productWebSocketRef = useRef<WebSocket | null>(null)

  const addMessage = useCallback((message: Omit<VoiceMessage, 'id' | 'timestamp'>) => {
    const newMessage: VoiceMessage = {
      ...message,
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date()
    }
    console.log('🎤 Adding message:', newMessage)
    setMessages(prev => {
      const updated = [...prev, newMessage]
      console.log('🎤 Total messages now:', updated.length)
      return updated
    })
  }, [])

  const connectToolWebSocket = useCallback(() => {
    if (toolWebSocketRef.current?.readyState === WebSocket.OPEN) {
      console.log('🔧 Tool WebSocket already connected')
      return
    }

    // Guard: ensure userId is available before attempting connection
    if (!userId || !userId.trim()) {
      console.warn('🔧 Cannot connect Tool WebSocket: userId is not available')
      console.warn('🔧 userId value:', userId, 'typeof:', typeof userId, 'length:', userId?.length)
      console.warn('🔧 config.defaultUserId:', config.defaultUserId)
      addMessage({
        type: 'error',
        content: '❌ Cannot connect WebSocket: User ID is not set. Please set a valid User ID first.'
      })
      return
    }

    console.log('🔧 Attempting to connect to Tool WebSocket...')

    // For development with self-signed certificates, we need to handle SSL errors
    const toolWsUrl = config.websocket.tools(userId.trim(), currentPage)
    console.log('🔧 Tool WebSocket URL:', toolWsUrl)
    console.log('🔧 Current page context:', currentPage)
    console.log('🔧 Current user ID:', userId)
    
    const toolWs = new WebSocket(toolWsUrl)
    
    toolWs.onopen = () => {
      console.log('✅ Tool WebSocket connected successfully')
      setIsToolsConnected(true)
      addMessage({
        type: 'system',
        content: '🔧 Tool WebSocket connected'
      })
    }
    
    toolWs.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('🔧 Tool WebSocket message received:', data)
        
        // Dispatch message to WebSocket monitor
        window.dispatchEvent(new CustomEvent('websocket-message', {
          detail: event
        }))
        
        handleToolAction(data)
      } catch (error) {
        console.error('Error parsing tool message:', error)
      }
    }
    
    toolWs.onclose = (event) => {
      console.log('🔌 Tool WebSocket disconnected:', event.code, event.reason)
      setIsToolsConnected(false)
      addMessage({
        type: 'system',
        content: '🔌 Tool WebSocket disconnected'
      })
    }
    
    toolWs.onerror = (error) => {
      console.error('❌ Tool WebSocket error:', error)
      setIsToolsConnected(false)
      addMessage({
        type: 'error',
        content: '❌ Tool WebSocket connection error - Backend may not be running or SSL certificate issue'
      })
      
      // Retry connection after 5 seconds
      setTimeout(() => {
        if (!isToolsConnected) {
          console.log('🔄 Retrying tool WebSocket connection...')
          connectToolWebSocket()
        }
      }, 5000)
    }
    
    toolWebSocketRef.current = toolWs
  }, [addMessage, userId, currentPage])

  const connect = useCallback(async () => {
    if (isConnected) {
      return
    }

    // Guard: ensure userId is available before attempting connection
    if (!userId || !userId.trim()) {
      console.warn('🎤 Cannot connect: userId is not available')
      addMessage({
        type: 'error',
        content: '❌ Cannot connect: User ID is not set. Please set a valid User ID first.'
      })
      return
    }

    try {
      setConnectionStatus('Connecting...')

      // Connect to tool WebSocket first
      connectToolWebSocket()

      // Import the WebSocket transport (this handles protobuf serialization)
      const { WebSocketTransport } = await import('@pipecat-ai/websocket-transport')
      
      // Create transport with current page context
      const transport = new WebSocketTransport()
      
      console.log('🎤 Connecting with current page context:', currentPage)
      console.log('🎤 Current page value type:', typeof currentPage)
      
      const rtviConfig = {
        transport,
        params: getRTVIConfig(currentPage, userId),
        enableMic: true,
        enableCam: false,
        callbacks: {
          onConnected: () => {
            setIsConnected(true)
            setConnectionStatus('Connected')
            addMessage({
              type: 'system',
              content: '✅ Connected to Voice Agent'
            })
          },
          onDisconnected: () => {
            setIsConnected(false)
            setIsInConversation(false)
            setConnectionStatus('Disconnected')
            addMessage({
              type: 'system',
              content: '👋 Disconnected from voice conversation'
            })
          },
          onBotReady: (data: any) => {
            console.log(`🎤 Voice bot ready:`, data)
            addMessage({
              type: 'system',
              content: '🤖 AI is ready to chat!'
            })
          },
          onUserTranscript: (data: any) => {
            console.log('🎤 User transcript received:', data)
            if (data.text && data.text.trim()) {
              addMessage({
                type: 'user',
                content: data.text,
                isAudio: true
              })
            }
          },
          onBotTranscript: (data: any) => {
            console.log('🎤 Bot transcript received:', data)
            if (data.text && data.text.trim()) {
              addMessage({
                type: 'assistant',
                content: data.text
              })
            }
          },
          onMessageError: (error: any) => {
            console.error('🎤 Message error:', error)
            addMessage({
              type: 'error',
              content: `Message error: ${error.message || 'Unknown error'}`
            })
          },
          onError: (error: any) => {
            console.error('🎤 Error:', error)
            addMessage({
              type: 'error',
              content: `Connection error: ${error.message || 'Unknown error'}`
            })
          },
        },
      }

      // Import RTVI client dynamically
      const { RTVIClient } = await import('@pipecat-ai/client-js')
      const rtviClient = new RTVIClient(rtviConfig)
      
      console.log('🎤 Initializing devices...')
      await rtviClient.initDevices()

      console.log('🎤 Connecting to voice bot...')
      await rtviClient.connect()

      // Store the client reference
      mainWebSocketRef.current = rtviClient as any

    } catch (error) {
      console.error('Failed to connect:', error)
      setConnectionStatus('Connection Failed')
      addMessage({
        type: 'error',
        content: `Failed to connect to Voice Agent: ${error instanceof Error ? error.message : 'Unknown error'}`
      })
    }
  }, [addMessage, connectToolWebSocket, isConnected, userId, currentPage])

  const disconnect = useCallback(async () => {
    console.log('🎤 Disconnecting from voice conversation...')
    
    if (mainWebSocketRef.current) {
      try {
        await (mainWebSocketRef.current as any).disconnect()
      } catch (error) {
        console.error('Error disconnecting RTVI client:', error)
      }
      mainWebSocketRef.current = null
    }
    
    if (toolWebSocketRef.current) {
      toolWebSocketRef.current.close()
      toolWebSocketRef.current = null
    }
    
    if (productWebSocketRef.current) {
      productWebSocketRef.current.close()
      productWebSocketRef.current = null
    }
    
    setIsConnected(false)
    setIsInConversation(false)
    setConnectionStatus('Disconnected')
  }, [])

  // Removed startConversation and stopConversation functions as requested

  // Handle tool actions
  const handleToolAction = useCallback((data: any) => {
    console.log('🔧 Tool action:', data)
    
    switch (data.type) {
      case 'mssql_search_result':
        addMessage({
          type: 'system',
          content: `🔍 MSSQL Search: ${data.action}`,
        })
        break
      
      case 'quotation_command':
        addMessage({
          type: 'system',
          content: `🔧 Quotation Tool: ${data.action}`,
        })
        break
      
      case 'navigation_command':
        addMessage({
          type: 'system',
          content: `🧭 Navigation Tool: ${data.action}`,
        })
        break
      
      case 'product_command':
        addMessage({
          type: 'system',
          content: `📦 Product Info Tool: ${data.action}`,
        })
        break

      default:
        addMessage({
          type: 'system',
          content: `🔧 Tool activated: ${data.type}`,
        })
    }
  }, [addMessage])

  const clearMessages = useCallback(() => {
    setMessages([])
    console.log('🧹 Messages cleared')
  }, [])

  const clearToolCalls = useCallback(() => {
    setToolCallsInProgress([])
    setRecentToolResults([])
    console.log('🧹 Tool calls cleared')
  }, [])

        // Auto-connect tool WebSocket on mount and when page changes
      useEffect(() => {
        console.log('🔧 Auto-connecting tool WebSocket...')
        console.log('🔧 Current page:', currentPage)
        console.log('🔧 Current user ID:', userId)

        // Guard: ensure userId is available before attempting auto-connection
        if (!userId || !userId.trim()) {
          console.log('🔧 Skipping auto-connect: userId not available yet')
          console.log('🔧 userId value:', userId, 'typeof:', typeof userId, 'length:', userId?.length)
          console.log('🔧 config.defaultUserId:', config.defaultUserId)
          return
        }

        // First test if backend is reachable
        fetch(config.api.health)
          .then(response => {
            if (response.ok) {
              console.log('✅ Backend health check passed')
              connectToolWebSocket()
            } else {
              console.error('❌ Backend health check failed:', response.status)
              addMessage({
                type: 'error',
                content: `❌ Backend health check failed: ${response.status}`
              })
            }
          })
          .catch(error => {
            console.error('❌ Backend health check error:', error)
            addMessage({
              type: 'error',
              content: '❌ Cannot reach backend - please ensure it is running on https://176.9.16.194:8200'
            })
          })
      }, [connectToolWebSocket, addMessage, currentPage, userId])

  // Handle userId changes - disconnect and reconnect with new userId
  useEffect(() => {
    console.log('👤 User ID changed, handling reconnection...')

    // Disconnect existing connections
    if (toolWebSocketRef.current?.readyState === WebSocket.OPEN) {
      console.log('🔌 Disconnecting tool WebSocket due to user ID change')
      toolWebSocketRef.current.close()
      toolWebSocketRef.current = null
      setIsToolsConnected(false)
    }

    if (mainWebSocketRef.current) {
      console.log('🔌 Disconnecting main WebSocket due to user ID change')
      mainWebSocketRef.current.disconnect?.()
      mainWebSocketRef.current = null
      setIsConnected(false)
      setIsInConversation(false)
      setConnectionStatus('Disconnected')
    }

    // Add system message about user ID change
    addMessage({
      type: 'system',
      content: `👤 User ID changed to: ${userId}. Please reconnect to continue.`
    })

    // Auto-reconnect after a short delay
    const reconnectTimeout = setTimeout(() => {
      console.log('🔄 Auto-reconnecting with new user ID...')
      // Test backend health and reconnect
      fetch(config.api.health)
        .then(response => {
          if (response.ok) {
            console.log('✅ Backend health check passed, reconnecting...')
            connectToolWebSocket()
          } else {
            console.error('❌ Backend health check failed after user ID change')
          }
        })
        .catch(error => {
          console.error('❌ Backend health check error after user ID change:', error)
        })
    }, 1000) // 1 second delay to allow cleanup

    return () => clearTimeout(reconnectTimeout)
  }, [userId, addMessage, connectToolWebSocket]) // Only trigger on userId changes

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return {
    isConnected,
    isInConversation,
    connectionStatus,
    messages,
    toolCallsInProgress,
    recentToolResults,
    isToolsConnected,
    
    // Connection methods
    connect,
    disconnect,
    connectToolWebSocket,
    
    // Utility methods
    clearMessages,
    clearToolCalls,
  }
}
