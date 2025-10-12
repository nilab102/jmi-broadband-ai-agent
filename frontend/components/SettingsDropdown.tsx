'use client'

import React, { useState } from 'react'
import { Settings, User, Check, Wifi, WifiOff, Search, ChevronUp } from 'lucide-react'
import { useVoiceClient } from '@/lib/voiceClient'
import { UserIdSetter } from './UserIdSetter'

interface SettingsDropdownProps {
  className?: string
}

export function SettingsDropdown({ className = '' }: SettingsDropdownProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isUserConfigOpen, setIsUserConfigOpen] = useState(false)
  const {
    isConnected,
    isToolsConnected
  } = useVoiceClient()

  return (
    <>
      <div className={`relative ${className}`}>
        {/* Settings Button */}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={`
            relative p-2 rounded-full transition-all duration-200
            ${isOpen
              ? 'bg-purple-100 text-purple-600 shadow-lg'
              : 'hover:bg-gray-100 text-gray-600 hover:text-gray-800'
            }
          `}
        >
          <Settings className={`w-5 h-5 ${isOpen ? 'rotate-45' : ''} transition-transform duration-200`} />

          {/* Status indicator */}
          <div className="absolute -top-1 -right-1 w-3 h-3">
            <div className={`w-full h-full rounded-full border border-white ${
              isConnected && isToolsConnected ? 'bg-green-500' : 'bg-red-500'
            }`} />
          </div>
        </button>

        {/* Dropdown Menu */}
        {isOpen && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-40"
              onClick={() => setIsOpen(false)}
            />

            {/* Dropdown */}
            <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-2xl shadow-2xl border border-gray-100 z-50 overflow-hidden">
              {/* Header */}
              <div className="bg-gradient-to-r from-purple-500 to-pink-500 px-4 py-3">
                <div className="flex items-center justify-between text-white">
                  <span className="font-semibold">Settings & Status</span>
                  <button
                    onClick={() => setIsOpen(false)}
                    className="p-1 hover:bg-white/20 rounded-full transition-colors"
                  >
                    <Settings className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Content */}
              <div className="p-4 space-y-4">
                {/* User Configuration */}
                <div className="space-y-2">
                  <button
                    onClick={() => setIsUserConfigOpen(!isUserConfigOpen)}
                    className="w-full flex items-center justify-between p-3 bg-gradient-to-r from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100 rounded-lg transition-all duration-200 border border-blue-200 hover:border-blue-300"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center shadow-sm">
                        <User className="w-4 h-4 text-white" />
                      </div>
                      <div>
                        <span className="font-medium text-gray-900">User Configuration</span>
                        <p className="text-xs text-gray-600">Manage your user ID and settings</p>
                      </div>
                    </div>
                    <div className={`w-4 h-4 transition-transform duration-200 ${isUserConfigOpen ? 'rotate-180' : ''}`}>
                      <ChevronUp className="w-4 h-4 text-gray-600" />
                    </div>
                  </button>

                  {isUserConfigOpen && (
                    <div className="mt-3 p-4 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg border border-blue-200 shadow-sm">
                      <UserIdSetter />
                    </div>
                  )}
                </div>

                {/* Connection Status */}
                <div className="space-y-2">
                  <h4 className="font-medium text-gray-900 text-sm">Connection Status</h4>

                  <div className="flex items-center space-x-3 p-3 bg-green-50 rounded-lg border border-green-200">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                      isConnected ? 'bg-green-500' : 'bg-red-500'
                    }`}>
                      {isConnected ? (
                        <Wifi className="w-4 h-4 text-white" />
                      ) : (
                        <WifiOff className="w-4 h-4 text-white" />
                      )}
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-medium text-gray-900">
                        Voice Agent
                      </div>
                      <div className={`text-xs ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
                        {isConnected ? 'Connected' : 'Disconnected'}
                      </div>
                    </div>
                    <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
                  </div>

                  <div className="flex items-center space-x-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                    <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                      <Search className="w-4 h-4 text-white" />
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-medium text-gray-900">
                        Broadband Tools
                      </div>
                      <div className={`text-xs ${isToolsConnected ? 'text-blue-600' : 'text-gray-600'}`}>
                        {isToolsConnected ? 'Connected' : 'Disconnected'}
                      </div>
                    </div>
                    <div className={`w-2 h-2 rounded-full ${isToolsConnected ? 'bg-blue-500' : 'bg-gray-400'}`} />
                  </div>
                </div>

                {/* Quick Actions */}
                <div className="pt-2 border-t border-gray-100">
                  <div className="text-xs text-gray-500 text-center">
                    Click outside to close • Version 1.0.0
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  )
}
