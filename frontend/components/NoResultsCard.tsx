'use client'

import React from 'react'
import { Wifi, AlertCircle, CheckCircle } from 'lucide-react'

interface NoResultsCardProps {
  isConnected?: boolean
  manualControl?: boolean
  onConnect?: () => void
}

export function NoResultsCard({ isConnected, manualControl, onConnect }: NoResultsCardProps) {
  return (
    <div className="text-center py-8 sm:py-16 bg-gradient-to-br from-gray-50 to-blue-50 rounded-xl border-2 border-dashed border-gray-200">
      <div className="relative">
        <Wifi className="w-16 sm:w-20 h-16 sm:h-20 text-gray-300 mx-auto mb-6" />
        {!isConnected && (
          <div className="absolute -top-2 -right-2 w-6 h-6 bg-yellow-400 rounded-full flex items-center justify-center animate-pulse">
            <AlertCircle className="w-4 h-4 text-white" />
          </div>
        )}
      </div>

      <div className="space-y-2">
        <h3 className="text-lg font-semibold text-gray-700">No Tool Results Yet</h3>
        <p className="text-gray-500 max-w-sm mx-auto text-sm sm:text-base">
          {!isConnected
            ? manualControl
              ? "Manual control enabled. Click 'Connect Tool' to establish WebSocket connection."
              : "Waiting for WebSocket connection to establish..."
            : "Use the chat interface above to search for broadband deals. Results will appear here automatically."
          }
        </p>

        {isConnected && (
          <div className="mt-4 p-3 bg-white rounded-lg border border-green-200 max-w-md mx-auto">
            <div className="flex items-center space-x-2 text-green-700">
              <CheckCircle className="w-4 h-4" />
              <span className="text-sm font-medium">Ready to receive tool results</span>
            </div>
          </div>
        )}

        {manualControl && (
          <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200 max-w-md mx-auto">
            <div className="text-center">
              <p className="text-xs text-blue-600 mb-2">Manual Control Mode</p>
              <p className="text-xs text-blue-500">Toggle off for automatic connections</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
