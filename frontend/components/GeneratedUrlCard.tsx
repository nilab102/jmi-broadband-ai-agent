'use client'

import React from 'react'
import { Globe, ExternalLink } from 'lucide-react'

interface GeneratedUrlCardProps {
  url: string
  onOpenUrl?: (url: string) => void
}

export function GeneratedUrlCard({ url, onOpenUrl }: GeneratedUrlCardProps) {
  if (!url) {
    return null
  }

  return (
    <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-4 sm:p-5 border border-green-200 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-3 gap-3">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
            <Globe className="w-4 h-4 text-white" />
          </div>
          <span className="font-semibold text-green-900">Generated URL</span>
        </div>
        <button
          onClick={() => onOpenUrl?.(url)}
          className="flex items-center space-x-2 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-colors shadow-sm text-sm font-medium"
        >
          <ExternalLink className="w-4 h-4" />
          <span>Open URL</span>
        </button>
      </div>
      <div className="bg-white border border-green-300 rounded-lg p-3 overflow-x-auto">
        <code className="text-xs text-green-700 break-all">{url}</code>
      </div>
    </div>
  )
}
