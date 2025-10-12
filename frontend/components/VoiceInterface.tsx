'use client'

import React, { useState, useCallback } from 'react'
import { useVoiceClient } from '@/lib/voiceClient'
import { usePageContext } from '@/lib/pageContext'
import { Mic, Phone, PhoneOff, Wifi, WifiOff } from 'lucide-react'

interface VoiceInterfaceProps {
  onConnectionChange?: (isConnected: boolean) => void
}

export function VoiceInterface({ onConnectionChange }: VoiceInterfaceProps) {
  const {
    isConnected,
    connectionStatus,
    connect,
    disconnect
  } = useVoiceClient()
  
  const { currentPage, getPageDisplayName } = usePageContext()

  const [isConnecting, setIsConnecting] = useState(false)

  const handleConnect = useCallback(async () => {
    setIsConnecting(true)
    try {
      // Pass the current page when connecting
      await connect()
      console.log('Connecting with page context:', currentPage)
    } catch (error) {
      console.error('Connection failed:', error)
    } finally {
      setIsConnecting(false)
    }
  }, [connect, currentPage])

  const getStatusInfo = () => {
    if (isConnecting) return { text: 'Connecting...', color: 'text-blue-600', icon: Wifi }
    if (!isConnected) return { text: 'Disconnected', color: 'text-gray-500', icon: WifiOff }
    return { text: 'Connected', color: 'text-green-600', icon: Mic }
  }

  const statusInfo = getStatusInfo()
  const StatusIcon = statusInfo.icon

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 mb-6">
        <div className="text-center">
          <div className="relative inline-flex items-center justify-center mb-4">
            {/* Status Indicator */}
            <div className={`w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300 ${
              isConnected 
                ? 'bg-green-100 border-2 border-green-300'
                : 'bg-gray-100 border-2 border-gray-300'
            }`}>
              <StatusIcon className={`w-8 h-8 ${statusInfo.color}`} />
            </div>
            
            {/* Pulse animation for connected */}
            {isConnected && (
              <div className="absolute inset-0 rounded-full bg-green-300 animate-ping opacity-20"></div>
            )}
          </div>
          
          <h3 className={`text-xl font-semibold ${statusInfo.color} mb-2`}>
            {statusInfo.text}
          </h3>
          
          <p className="text-gray-600 text-sm">
            {isConnected 
              ? 'Voice is active - speak naturally'
              : 'Connect to start voice conversation'
            }
          </p>
        </div>
      </div>

      {/* Main Controls */}
      <div className="flex-1 flex flex-col justify-center space-y-4">
        {!isConnected ? (
          /* Connect Button */
          <button
            onClick={handleConnect}
            disabled={isConnecting}
            className={`w-full py-4 px-6 rounded-2xl font-semibold text-white transition-all duration-200 transform hover:scale-105 ${
              isConnecting 
                ? 'bg-gray-400 cursor-not-allowed' 
                : 'bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 shadow-lg hover:shadow-xl'
            }`}
          >
            <div className="flex items-center justify-center space-x-3">
              {isConnecting ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>Connecting...</span>
                </>
              ) : (
                <>
                  <Phone className="w-5 h-5" />
                  <span>Connect to Voice Agent</span>
                </>
              )}
            </div>
          </button>
        ) : (
          /* Connected Controls */
          <div className="space-y-4">
            {/* Disconnect Button */}
            <button
              onClick={disconnect}
              className="w-full py-4 px-6 bg-gradient-to-r from-gray-500 to-gray-600 hover:from-gray-600 hover:to-gray-700 text-white rounded-2xl font-semibold transition-all duration-200 transform hover:scale-105 shadow-lg hover:shadow-xl"
            >
              <div className="flex items-center justify-center space-x-3">
                <PhoneOff className="w-6 h-6" />
                <span className="text-lg">Disconnect</span>
              </div>
            </button>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="flex-shrink-0 space-y-3">
        {/* Page Context */}
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-xl p-3">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
            <span className="text-sm font-medium text-blue-800">Current Page:</span>
            <span className="text-sm text-blue-700">{getPageDisplayName(currentPage)}</span>
          </div>
        </div>

        {/* Connection Status */}
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">Status:</span>
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-gray-400'
              }`}></div>
              <span className={`text-sm font-semibold ${statusInfo.color}`}>
                {connectionStatus}
              </span>
            </div>
          </div>
        </div>

        {/* Security Notice */}
        {isConnected && (
          <div className="bg-green-50 border border-green-200 rounded-xl p-3">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-xs text-green-800 font-medium">
                🔒 Secure & Private • AI-Powered
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
