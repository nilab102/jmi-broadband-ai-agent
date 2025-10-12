'use client'

import React, { useState, useEffect } from 'react'
import { X, MessageCircle, Mic, ArrowLeft } from 'lucide-react'
import { TextConversation } from './TextConversation'
import { VoiceInterface } from './VoiceInterface'

interface ChatbotModalProps {
  isOpen: boolean
  onClose: () => void
  mode: 'text' | 'voice'
  onModeChange: (mode: 'text' | 'voice') => void
}

export function ChatbotModal({ isOpen, onClose, mode, onModeChange }: ChatbotModalProps) {
  const [currentStep, setCurrentStep] = useState<'selector' | 'chat'>('selector')
  const [selectedMode, setSelectedMode] = useState<'text' | 'voice'>('text')

  // Reset to selector when modal opens
  useEffect(() => {
    if (isOpen) {
      setCurrentStep('selector')
    }
  }, [isOpen])

  // Close on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden'
    }

    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = 'unset'
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  // Step 1: Chat Mode Selector
  if (currentStep === 'selector') {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/50 backdrop-blur-sm">
        <div className="bg-white rounded-2xl sm:rounded-3xl shadow-2xl border border-gray-200 overflow-hidden max-w-sm sm:max-w-md w-full mx-auto">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-500 via-purple-600 to-pink-500 px-4 sm:px-6 py-3 sm:py-4">
            <div className="flex items-center justify-between text-white">
              <h2 className="text-base sm:text-lg font-semibold">Choose Chat Mode</h2>
              <button
                onClick={onClose}
                className="p-1 hover:bg-white/20 rounded-full transition-colors"
              >
                <X className="w-4 h-4 sm:w-5 sm:h-5" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-4 sm:p-6">
            <p className="text-gray-600 text-center mb-8">
              Select your preferred way to interact with the AI agent
            </p>

            <div className="grid grid-cols-1 gap-3 sm:gap-4">
              {/* Text Chat Option */}
              <button
                onClick={() => {
                  setSelectedMode('text')
                  setCurrentStep('chat')
                  onModeChange('text')
                }}
                className="group relative p-4 sm:p-6 bg-gradient-to-br from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100 border border-blue-200 rounded-xl sm:rounded-2xl transition-all duration-300 hover:shadow-lg hover:scale-105"
              >
                <div className="flex flex-col items-center text-center space-y-3 sm:space-y-4">
                  <div className="w-12 h-12 sm:w-16 sm:h-16 bg-blue-500 rounded-xl sm:rounded-2xl flex items-center justify-center group-hover:bg-blue-600 transition-colors shadow-lg">
                    <MessageCircle className="w-6 h-6 sm:w-8 sm:h-8 text-white" />
                  </div>
                  <div>
                    <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-1 sm:mb-2">Text Chat</h3>
                    <p className="text-xs sm:text-sm text-gray-600">Type your broadband queries and get instant responses</p>
                  </div>
                </div>
              </button>

              {/* Voice Chat Option */}
              <button
                onClick={() => {
                  setSelectedMode('voice')
                  setCurrentStep('chat')
                  onModeChange('voice')
                }}
                className="group relative p-4 sm:p-6 bg-gradient-to-br from-green-50 to-emerald-50 hover:from-green-100 hover:to-emerald-100 border border-green-200 rounded-xl sm:rounded-2xl transition-all duration-300 hover:shadow-lg hover:scale-105"
              >
                <div className="flex flex-col items-center text-center space-y-3 sm:space-y-4">
                  <div className="w-12 h-12 sm:w-16 sm:h-16 bg-green-500 rounded-xl sm:rounded-2xl flex items-center justify-center group-hover:bg-green-600 transition-colors shadow-lg">
                    <Mic className="w-6 h-6 sm:w-8 sm:h-8 text-white" />
                  </div>
                  <div>
                    <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-1 sm:mb-2">Voice Chat</h3>
                    <p className="text-xs sm:text-sm text-gray-600">Speak naturally and get voice responses</p>
                  </div>
                </div>
              </button>
            </div>

            {/* Footer */}
            <div className="mt-6 pt-4 border-t border-gray-100 text-center">
              <p className="text-xs text-gray-500">
                Choose your preferred interaction method
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Step 2: Actual Chat Interface
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-end p-3 sm:p-4 pointer-events-none">
      <div className="bg-white rounded-xl sm:rounded-2xl shadow-2xl border border-gray-200 overflow-hidden transition-all duration-300 pointer-events-auto w-full max-w-sm sm:max-w-lg h-[500px] sm:h-[600px]">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-500 via-purple-600 to-pink-500 px-3 sm:px-4 py-2 sm:py-3 text-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setCurrentStep('selector')}
                className="p-1 hover:bg-white/20 rounded-full transition-colors"
                title="Back to chat mode selection"
              >
                <ArrowLeft className="w-3 h-3 sm:w-4 sm:h-4" />
              </button>
              {mode === 'text' ? (
                <MessageCircle className="w-4 h-4 sm:w-5 sm:h-5" />
              ) : (
                <Mic className="w-4 h-4 sm:w-5 sm:h-5" />
              )}
              <span className="font-semibold text-sm sm:text-base">
                {mode === 'text' ? 'Text Chat' : 'Voice Chat'}
              </span>
            </div>

            <button
              onClick={onClose}
              className="p-1 hover:bg-white/20 rounded-full transition-colors"
              title="Close chat"
            >
              <X className="w-3 h-3 sm:w-4 sm:h-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="h-full">
          {mode === 'text' ? (
            <div className="h-full">
              <TextConversation />
            </div>
          ) : (
            <div className="h-full p-3 sm:p-4">
              <VoiceInterface />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
