'use client'

import React, { useState } from 'react'
import { ChatbotModal } from '@/components/ChatbotModal'
import { BroadbandToolResults } from '@/components/BroadbandToolResults'
import { FloatingChatButton } from '@/components/FloatingChatButton'
import { SettingsDropdown } from '@/components/SettingsDropdown'
import { PageProvider } from '@/lib/pageContext'
import { UserProvider } from '@/lib/userContext'
import { useVoiceClient } from '@/lib/voiceClient'
import { Wifi, MessageCircle, Mic, Zap, Search } from 'lucide-react'

function BroadbandPageContent() {
  const {
    isConnected,
    isToolsConnected,
    connectToolWebSocket,
    disconnect
  } = useVoiceClient()

  const [isChatModalOpen, setIsChatModalOpen] = useState(false)
  const [chatMode, setChatMode] = useState<'text' | 'voice'>('text')

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-indigo-50">
      {/* Header */}
      <header className="bg-white/90 backdrop-blur-md border-b border-blue-100 sticky top-0 z-30 shadow-sm">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-8 py-3 sm:py-4">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
            <div className="flex items-center space-x-3 min-w-0">
              <div className="flex items-center space-x-2">
                <Wifi className="w-5 h-5 sm:w-6 sm:h-6 lg:w-8 lg:h-8 text-blue-600" />
                <Zap className="w-5 h-5 sm:w-6 sm:h-6 lg:w-8 lg:h-8 text-purple-600" />
              </div>
              <div className="min-w-0 flex-1">
                <h1 className="text-base sm:text-lg lg:text-2xl font-bold text-gray-900 truncate">
                  Broadband Search Agent
                </h1>
                <p className="text-xs sm:text-sm text-gray-600 truncate">
                  AI-Powered Broadband Comparison & Search
                </p>
              </div>
            </div>

            {/* Settings Dropdown */}
            <div className="flex-shrink-0">
              <SettingsDropdown />
            </div>
          </div>

          {/* Responsive Description */}
          <div className="mt-2 sm:mt-3">
            <p className="text-xs sm:text-sm text-gray-600 text-center">
              Find the best broadband deals with AI-powered search and voice interaction
            </p>
          </div>
        </div>
      </header>

      {/* Main Content - Full Width */}
      <main className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-8 py-4 sm:py-6 lg:py-8">
        {/* Tool Results - Full Width */}
        <div className="w-full">
          <BroadbandToolResults
            isConnected={isToolsConnected}
            onConnect={connectToolWebSocket}
            onDisconnect={disconnect}
          />
        </div>
      </main>

      {/* Floating Chat Button */}
      <FloatingChatButton
        onClick={() => setIsChatModalOpen(true)}
        isOpen={isChatModalOpen}
      />

      {/* Chat Modal */}
      <ChatbotModal
        isOpen={isChatModalOpen}
        onClose={() => setIsChatModalOpen(false)}
        mode={chatMode}
        onModeChange={setChatMode}
      />

      {/* Responsive Footer */}
      <footer className="mt-6 sm:mt-8 lg:mt-12 bg-white/50 backdrop-blur-sm border-t border-blue-100">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-8 py-3 sm:py-4 lg:py-6">
          <div className="flex flex-wrap justify-center items-center gap-3 sm:gap-4 lg:gap-8 text-gray-600">
            <div className="flex items-center space-x-2">
              <Wifi className="w-4 h-4 sm:w-5 sm:h-5 text-blue-600" />
              <span className="text-xs sm:text-sm">Broadband Search</span>
            </div>
            <div className="flex items-center space-x-2">
              <MessageCircle className="w-4 h-4 sm:w-5 sm:h-5 text-purple-600" />
              <span className="text-xs sm:text-sm">AI Chat</span>
            </div>
            <div className="flex items-center space-x-2">
              <Mic className="w-4 h-4 sm:w-5 sm:h-5 text-green-600" />
              <span className="text-xs sm:text-sm">Voice Interaction</span>
            </div>
            <div className="flex items-center space-x-2">
              <Zap className="w-4 h-4 sm:w-5 sm:h-5 text-orange-600" />
              <span className="text-xs sm:text-sm">Smart Recommendations</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default function VoiceAgentPage() {
  return (
    <UserProvider>
      <PageProvider initialPage="broadband">
        <BroadbandPageContent />
      </PageProvider>
    </UserProvider>
  )
}
