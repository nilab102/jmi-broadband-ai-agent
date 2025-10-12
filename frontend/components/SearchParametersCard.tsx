'use client'

import React from 'react'
import { Search, MapPin, Zap, Calendar, Phone, Wifi, Building, Home, Filter, PlusCircle } from 'lucide-react'

interface SearchParametersCardProps {
  params: Record<string, any>
}

export function SearchParametersCard({ params }: SearchParametersCardProps) {
  if (!params || typeof params !== 'object') {
    return null
  }

  const paramFields = [
    { key: 'postcode', label: 'Postcode', icon: MapPin, color: 'blue' },
    { key: 'speed_in_mb', label: 'Speed', icon: Zap, color: 'yellow' },
    { key: 'contract_length', label: 'Contract', icon: Calendar, color: 'purple' },
    { key: 'phone_calls', label: 'Phone Calls', icon: Phone, color: 'green' },
    { key: 'product_type', label: 'Product Type', icon: Wifi, color: 'cyan' },
    { key: 'providers', label: 'Providers', icon: Building, color: 'indigo' },
    { key: 'current_provider', label: 'Current Provider', icon: Home, color: 'orange' },
    { key: 'sort_by', label: 'Sort By', icon: Filter, color: 'gray' },
    { key: 'new_line', label: 'New Line', icon: PlusCircle, color: 'pink' },
  ]

  // Check if we have at least one non-empty field
  const hasValidFields = paramFields.some(field => params[field.key] && params[field.key].trim() !== '')

  if (!hasValidFields) {
    return null
  }

  const colorClasses = {
    blue: 'bg-blue-100 text-blue-700 border-blue-200',
    yellow: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    purple: 'bg-purple-100 text-purple-700 border-purple-200',
    green: 'bg-green-100 text-green-700 border-green-200',
    indigo: 'bg-indigo-100 text-indigo-700 border-indigo-200',
    cyan: 'bg-cyan-100 text-cyan-700 border-cyan-200',
    gray: 'bg-gray-100 text-gray-700 border-gray-200',
    orange: 'bg-orange-100 text-orange-700 border-orange-200',
    pink: 'bg-pink-100 text-pink-700 border-pink-200'
  }

  return (
    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-4 sm:p-5 border border-blue-200 shadow-sm">
      <div className="flex items-center space-x-2 mb-4">
        <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
          <Search className="w-4 h-4 text-white" />
        </div>
        <span className="font-semibold text-blue-900">Search Parameters</span>
      </div>

      {/* Responsive grid layout */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {paramFields.map(({ key, label, icon: Icon, color }) => {
          const value = params[key]
          const displayValue = value || 'Not specified'

          return (
            <div key={key} className={`flex flex-col space-y-1 p-3 ${colorClasses[color as keyof typeof colorClasses]} rounded-lg border`}>
              <div className="flex items-center space-x-2">
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span className="text-xs font-medium opacity-75 truncate">{label}</span>
              </div>
              <p className="text-sm font-semibold truncate" title={displayValue}>
                {displayValue}
              </p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
