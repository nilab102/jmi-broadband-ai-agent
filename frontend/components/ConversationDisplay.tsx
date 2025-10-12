'use client'

import React from 'react'
import { VoiceMessage } from '@/lib/voiceClient'

interface ConversationDisplayProps {
  messages: VoiceMessage[]
  onClear?: () => void
}

export function ConversationDisplay({ messages, onClear }: ConversationDisplayProps) {
  const getMessageIcon = (type: string) => {
    switch (type) {
      case 'user':
        return '👤'
      case 'assistant':
        return '🤖'
      case 'system':
        return '⚙️'
      case 'error':
        return '❌'
      case 'tool_call':
        return '🔧'
      case 'tool_result':
        return '✅'
      default:
        return '💬'
    }
  }

  const getMessageClass = (type: string) => {
    switch (type) {
      case 'user':
        return 'bg-gradient-to-r from-voice-primary to-voice-secondary text-white'
      case 'assistant':
        return 'bg-gray-100 text-gray-800 border border-gray-200'
      case 'system':
        return 'bg-blue-50 text-blue-800 border border-blue-200'
      case 'error':
        return 'bg-red-50 text-red-800 border border-red-200'
      case 'tool_call':
        return 'bg-yellow-50 text-yellow-800 border border-yellow-200'
      case 'tool_result':
        return 'bg-green-50 text-green-800 border border-green-200'
      default:
        return 'bg-gray-50 text-gray-800 border border-gray-200'
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-800">Conversation</h3>
        {onClear && (
          <button
            onClick={onClear}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Clear
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-3 p-4 bg-gray-50 rounded-lg">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <div className="text-4xl mb-2">🎤</div>
            <p>No messages yet</p>
            <p className="text-sm">Connect and start talking to see messages here</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`p-3 rounded-lg ${getMessageClass(message.type)}`}
            >
              <div className="flex items-start space-x-2">
                <span className="text-lg">{getMessageIcon(message.type)}</span>
                <div className="flex-1">
                  <div className="text-sm font-medium mb-1">
                    {message.type.charAt(0).toUpperCase() + message.type.slice(1)}
                  </div>
                  <div className="text-sm whitespace-pre-wrap">
                    {message.content}
                  </div>
                  {message.isAudio && (
                    <div className="text-xs text-gray-500 mt-1">
                      🎵 Audio input
                    </div>
                  )}
                  <div className="text-xs text-gray-500 mt-1">
                    {message.timestamp.toLocaleTimeString()}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Status */}
      <div className="mt-4 text-xs text-gray-500 text-center">
        {messages.length} message{messages.length !== 1 ? 's' : ''}
      </div>
    </div>
  )
}
