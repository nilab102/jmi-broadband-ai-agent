'use client'

import React from 'react'
import { TrendingUp } from 'lucide-react'

interface RecommendationsCardProps {
  data: any
  isExpanded?: boolean
}

export function RecommendationsCard({ data, isExpanded }: RecommendationsCardProps) {
  if (!data || typeof data !== 'object') {
    return null
  }

  return (
    <div className="bg-gradient-to-br from-indigo-50 to-blue-50 rounded-xl p-4 sm:p-5 border border-indigo-200 shadow-sm">
      <div className="flex items-center space-x-2 mb-4">
        <div className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center">
          <TrendingUp className="w-4 h-4 text-white" />
        </div>
        <div>
          <span className="font-semibold text-indigo-900">AI Recommendations</span>
          <p className="text-xs text-indigo-600">{data?.total_recommendations || 0} recommendations generated</p>
        </div>
      </div>
      {data?.criteria && isExpanded && (
        <div className="bg-white rounded-lg p-4 border border-indigo-200">
          <p className="text-sm font-medium text-gray-700 mb-2">Based on your criteria:</p>
          <div className="space-y-1">
            {Object.entries(data.criteria).map(([key, value]: [string, any]) => (
              value && <div key={key} className="text-xs text-gray-600">{key}: {String(value)}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
