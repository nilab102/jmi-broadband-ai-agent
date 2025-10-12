'use client'

import React from 'react'
import { Building } from 'lucide-react'

interface ProviderComparisonCardProps {
  data: any
}

export function ProviderComparisonCard({ data }: ProviderComparisonCardProps) {
  if (!data || typeof data !== 'object') {
    return null
  }

  return (
    <div className="bg-gradient-to-br from-pink-50 to-rose-50 rounded-xl p-4 sm:p-5 border border-pink-200 shadow-sm">
      <div className="flex items-center space-x-2 mb-4">
        <div className="w-8 h-8 bg-pink-500 rounded-lg flex items-center justify-center">
          <Building className="w-4 h-4 text-white" />
        </div>
        <div>
          <span className="font-semibold text-pink-900">Provider Comparison</span>
          <p className="text-xs text-pink-600">{data?.total_matches || 0} matching deals</p>
        </div>
      </div>
      <div className="bg-white rounded-lg p-4 border border-pink-200">
        <p className="text-sm font-medium text-gray-700 mb-2">Comparing providers:</p>
        <div className="flex flex-wrap gap-2">
          {data?.providers_compared?.map((provider: string, idx: number) => (
            <span key={idx} className="px-3 py-1 bg-pink-100 text-pink-700 rounded-full text-xs font-medium">
              {provider}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
