'use client'

import React from 'react'
import { usePageContext, SUPPORTED_PAGES, SupportedPage } from '@/lib/pageContext'
import { Mic, MessageCircle, HelpCircle, Database, FileSearch, Settings, Table, Users, LayoutDashboard, Network, Wifi } from 'lucide-react'

// Page icons mapping
const PAGE_ICONS = {
  'voice-control': Mic,
  'text-conversation': MessageCircle,
  'database-query': Database,
  'file-query': FileSearch,
  'user-configuration': Settings,
  'tables': Table,
  'users': Users,
  'dashboard': LayoutDashboard,
  'company-structure': Network,
  'broadband': Wifi
}

export function PageSelector() {
  const { currentPage, setCurrentPage, getPageDisplayName } = usePageContext()

  const handlePageChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const newPage = event.target.value as SupportedPage
    setCurrentPage(newPage)
  }

  const CurrentPageIcon = PAGE_ICONS[currentPage] || HelpCircle

  return (
    <div className="bg-white rounded-2xl shadow-xl border border-blue-100 overflow-hidden backdrop-blur-sm">
      <div className="bg-gradient-to-r from-blue-500 via-indigo-600 to-purple-500 px-6 py-4">
        <div className="flex items-center space-x-3 text-white">
          <CurrentPageIcon className="w-6 h-6" />
          <h2 className="text-lg font-semibold">Current Page</h2>
        </div>
      </div>
      
      <div className="p-6 space-y-4">
        {/* Current Page Display */}
        <div className="flex items-center space-x-3 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <CurrentPageIcon className="w-5 h-5 text-blue-600" />
          <div>
            <div className="text-sm font-medium text-blue-800">Current Page</div>
            <div className="text-lg font-semibold text-blue-900">
              {getPageDisplayName(currentPage)}
            </div>
          </div>
        </div>

        {/* Page Selector */}
        <div className="space-y-2">
          <label htmlFor="page-select" className="block text-sm font-medium text-gray-700">
            Select Page
          </label>
          <select
            id="page-select"
            value={currentPage}
            onChange={handlePageChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white text-gray-900"
          >
            {Object.entries(SUPPORTED_PAGES).map(([key, displayName]) => {
              const Icon = PAGE_ICONS[key as SupportedPage] || HelpCircle
              return (
                <option key={key} value={key} className="flex items-center space-x-2">
                  {displayName}
                </option>
              )
            })}
          </select>
        </div>

        {/* Page Description */}
        <div className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">
          <div className="font-medium mb-1">Page Capabilities:</div>
          {getPageCapabilities(currentPage)}
        </div>

        {/* Connection Status */}
        <div className="flex items-center space-x-2 text-sm text-gray-600">
          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
          <span>Page context will be sent to AI when connecting</span>
        </div>
      </div>
    </div>
  )
}

function getPageCapabilities(page: SupportedPage): string {
  const capabilities = {
    'voice-control': 'Voice interaction with AI assistant',
    'text-conversation': 'Text-based chat with AI assistant',
    'database-query': 'Database search, view reports, generate reports',
    'file-query': 'File search, file upload',
    'user-configuration': 'Configure database, configure business rules',
    'tables': 'Load tables, table visualization, excel import, AI suggestions',
    'users': 'Manage database access, vector database access',
    'dashboard': 'Navigate to other pages',
    'company-structure': 'Navigate to other pages',
    'broadband': 'AI-powered broadband search, comparison, and recommendations'
  }

  return capabilities[page] || 'General navigation and access'
}
