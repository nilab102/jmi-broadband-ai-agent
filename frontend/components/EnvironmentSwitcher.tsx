'use client'

import React from 'react'
import { config } from '@/lib/config'
import { Globe, Server, Laptop } from 'lucide-react'

export function EnvironmentSwitcher() {
  const getEnvironmentIcon = () => {
    return config.isProduction ? <Server className="w-4 h-4" /> : <Laptop className="w-4 h-4" />
  }

  const getEnvironmentColor = () => {
    return config.isProduction ? 'bg-red-100 text-red-800 border-red-200' : 'bg-blue-100 text-blue-800 border-blue-200'
  }

  const getStatusText = () => {
    return config.isProduction ? 'Production' : 'Development'
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Globe className="w-5 h-5 text-gray-600" />
          <div>
            <h3 className="text-sm font-medium text-gray-900">Environment</h3>
            <p className="text-xs text-gray-500">Current backend configuration</p>
          </div>
        </div>
        
        <div className={`flex items-center space-x-2 px-3 py-1 rounded-full border ${getEnvironmentColor()}`}>
          {getEnvironmentIcon()}
          <span className="text-sm font-medium">{getStatusText()}</span>
        </div>
      </div>
      
      <div className="mt-3 space-y-2">
        <div className="flex justify-between items-center text-sm">
          <span className="text-gray-600">Backend URL:</span>
          <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
            {config.backend.baseUrl}
          </span>
        </div>
        
        <div className="flex justify-between items-center text-sm">
          <span className="text-gray-600">User ID:</span>
          <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
            {config.defaultUserId}
          </span>
        </div>
        
        {config.enableDebug && (
          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-600">Debug Mode:</span>
            <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
              Enabled
            </span>
          </div>
        )}
      </div>
      
      <div className="mt-3 p-3 bg-gray-50 rounded-lg">
        <h4 className="text-xs font-medium text-gray-800 mb-2">💡 How to Switch Environments</h4>
        <div className="text-xs text-gray-600 space-y-1">
          <div>1. Edit <code className="bg-gray-200 px-1 rounded">.env.local</code></div>
          <div>2. Change <code className="bg-gray-200 px-1 rounded">NEXT_PUBLIC_ENVIRONMENT</code> to:</div>
          <div className="ml-4">
            • <code className="bg-blue-100 text-blue-800 px-1 rounded">development</code> → localhost:8200
          </div>
          <div className="ml-4">
            • <code className="bg-red-100 text-red-800 px-1 rounded">production</code> → 176.9.16.194:8200
          </div>
          <div>3. Restart the frontend (<code className="bg-gray-200 px-1 rounded">npm run dev</code>)</div>
        </div>
      </div>
    </div>
  )
}
