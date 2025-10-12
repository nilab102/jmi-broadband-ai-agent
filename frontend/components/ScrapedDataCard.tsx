'use client'

import React from 'react'
import { Award, AlertCircle, Zap, Calendar, DollarSign } from 'lucide-react'

interface ScrapedDataCardProps {
  data: any
}

export function ScrapedDataCard({ data }: ScrapedDataCardProps) {
  if (!data || typeof data !== 'object') {
    return null
  }

  // Handle both direct scraped_data and nested structure
  const scrapedData = data.scraped_data || data
  const deals = scrapedData.deals || []
  const totalDeals = scrapedData.total_deals || 0
  const location = scrapedData.metadata?.location || 'Unknown'

  if (totalDeals === 0 && deals.length === 0) {
    return (
      <div className="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-4 sm:p-5 border border-orange-200">
        <div className="flex items-center space-x-2 mb-2">
          <AlertCircle className="w-5 h-5 text-orange-600" />
          <span className="font-semibold text-orange-900">No Deals Found</span>
        </div>
        <p className="text-sm text-orange-700">No broadband deals were found for the specified criteria.</p>
      </div>
    )
  }

  return (
    <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-4 sm:p-5 border border-purple-200 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-2">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center">
            <Award className="w-4 h-4 text-white" />
          </div>
          <div>
            <span className="font-semibold text-purple-900">Broadband Deals</span>
            <p className="text-xs text-purple-600">{totalDeals || deals.length} deals in {location}</p>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {deals.slice(0, 3).map((deal: any, idx: number) => (
          <div key={idx} className="bg-white rounded-lg border border-purple-200 p-4 hover:shadow-md transition-shadow">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start mb-3 gap-2">
              <div>
                <h4 className="font-semibold text-gray-900">{deal.provider?.name || 'Unknown Provider'}</h4>
                <p className="text-sm text-gray-600">{deal.title || 'Broadband Deal'}</p>
              </div>
              <div className="text-right">
                <div className="text-xl sm:text-2xl font-bold text-green-600">{deal.pricing?.monthly_cost || 'N/A'}</div>
                <p className="text-xs text-gray-500">per month</p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 pt-3 border-t border-gray-100">
              <div className="text-center">
                <Zap className="w-4 h-4 text-blue-600 mx-auto mb-1" />
                <p className="text-xs text-gray-500">Speed</p>
                <p className="text-sm font-semibold text-gray-900">{deal.speed?.display || 'N/A'}</p>
              </div>
              <div className="text-center">
                <Calendar className="w-4 h-4 text-purple-600 mx-auto mb-1" />
                <p className="text-xs text-gray-500">Contract</p>
                <p className="text-sm font-semibold text-gray-900">{deal.contract?.length_months || 'N/A'}</p>
              </div>
              <div className="text-center">
                <DollarSign className="w-4 h-4 text-green-600 mx-auto mb-1" />
                <p className="text-xs text-gray-500">Setup</p>
                <p className="text-sm font-semibold text-gray-900">{deal.pricing?.setup_costs || 'N/A'}</p>
              </div>
            </div>
          </div>
        ))}

        {deals.length > 3 && (
          <div className="text-center py-3 bg-purple-100 rounded-lg">
            <p className="text-sm font-medium text-purple-700">+ {deals.length - 3} more deals available</p>
          </div>
        )}
      </div>
    </div>
  )
}
