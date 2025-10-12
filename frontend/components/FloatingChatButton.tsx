'use client'

import React, { useState } from 'react'
import { MessageCircle, X, ChevronUp } from 'lucide-react'

interface FloatingChatButtonProps {
  onClick: () => void
  isOpen?: boolean
}

export function FloatingChatButton({ onClick, isOpen = false }: FloatingChatButtonProps) {
  const [isHovered, setIsHovered] = useState(false)

  return (
    <div className="fixed bottom-4 sm:bottom-6 right-4 sm:right-6 z-50">
      {/* Main Button */}
      <button
        onClick={onClick}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className={`
          relative group w-14 h-14 sm:w-16 sm:h-16 rounded-full
          bg-gradient-to-r from-blue-500 via-purple-600 to-pink-500
          hover:from-blue-600 hover:via-purple-700 hover:to-pink-600
          transition-all duration-300 ease-in-out transform
          ${isHovered || isOpen ? 'scale-110 shadow-2xl' : 'scale-100 shadow-lg'}
          border-2 border-white/20 backdrop-blur-sm
          flex items-center justify-center
          hover:shadow-purple-500/25
        `}
      >
        {/* Pulse animation for active state */}
        {isOpen && (
          <div className="absolute inset-0 rounded-full bg-purple-400 animate-ping opacity-20"></div>
        )}

        {/* Icon */}
        <div className="relative z-10">
          {isOpen ? (
            <X className="w-6 h-6 sm:w-7 sm:h-7 text-white" />
          ) : (
            <MessageCircle className="w-6 h-6 sm:w-7 sm:h-7 text-white" />
          )}
        </div>

        {/* Tooltip */}
        <div className={`
          absolute bottom-full right-0 mb-2 px-2 sm:px-3 py-1.5 sm:py-2
          bg-gray-900 text-white text-xs sm:text-sm rounded-lg
          transition-all duration-200
          ${isHovered || isOpen ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2 pointer-events-none'}
          whitespace-nowrap shadow-lg
        `}>
          {isOpen ? 'Close Chat' : 'Open Chat'}
          <div className="absolute top-full right-2 sm:right-3 w-0 h-0 border-l-3 sm:border-l-4 border-r-3 sm:border-r-4 border-t-3 sm:border-t-4 border-transparent border-t-gray-900"></div>
        </div>
      </button>

      {/* Status Indicator */}
      <div className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full border-2 border-white animate-pulse"></div>
    </div>
  )
}
