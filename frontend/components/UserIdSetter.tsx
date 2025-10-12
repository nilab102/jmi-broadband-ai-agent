'use client'

import React, { useState, useEffect } from 'react'
import { useUserContext } from '@/lib/userContext'
import { User, Check, X, RotateCcw } from 'lucide-react'

export function UserIdSetter() {
  const { userId, setUserId, isValidUserId, resetToDefault } = useUserContext()
  const [inputValue, setInputValue] = useState(userId)
  const [showSuccess, setShowSuccess] = useState(false)

  // Update input value when userId changes externally
  useEffect(() => {
    setInputValue(userId)
  }, [userId])

  const handleSave = () => {
    if (isValidUserId(inputValue)) {
      setUserId(inputValue)
      setShowSuccess(true)

      // Hide success message after 2 seconds
      setTimeout(() => setShowSuccess(false), 2000)
    }
  }

  const handleCancel = () => {
    setInputValue(userId)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSave()
    } else if (e.key === 'Escape') {
      handleCancel()
    }
  }

  const isInputValid = isValidUserId(inputValue)
  const hasChanges = inputValue !== userId

  return (
    <div className="bg-white rounded-xl sm:rounded-2xl shadow-lg border border-purple-100 overflow-hidden">
      <div className="bg-gradient-to-r from-purple-500 via-violet-600 to-indigo-500 px-4 sm:px-6 py-3 sm:py-4">
        <div className="flex items-center space-x-3 text-white">
          <User className="w-5 h-5 sm:w-6 sm:h-6" />
          <h2 className="text-base sm:text-lg font-semibold">User Configuration</h2>
        </div>
      </div>

      <div className="p-4 sm:p-6 space-y-4">
        {/* Current User ID Display */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div className="text-sm text-gray-600">Current User ID:</div>
          <div className="text-sm font-mono bg-gray-100 px-3 py-1 rounded truncate">
            {userId}
          </div>
        </div>

        {/* Input Section */}
        <div className="space-y-3">
          <label htmlFor="userIdInput" className="block text-sm font-medium text-gray-700">
            Set New User ID
          </label>

          <div className="space-y-3">
            <input
              id="userIdInput"
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Enter user ID..."
              className={`w-full px-4 py-3 border-2 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-colors text-base font-medium ${
                isInputValid
                  ? hasChanges
                    ? 'border-blue-400 bg-blue-50'
                    : 'border-gray-300 bg-white'
                  : 'border-red-400 bg-red-50'
              }`}
            />

            <div className="flex flex-col sm:flex-row gap-2 sm:space-x-3">
              <button
                onClick={handleSave}
                disabled={!isInputValid || !hasChanges}
                className={`px-6 py-3 rounded-lg font-medium transition-all duration-200 flex items-center justify-center space-x-2 ${
                  !isInputValid || !hasChanges
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : 'bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:from-green-600 hover:to-emerald-700 shadow-lg hover:shadow-xl transform hover:scale-105'
                }`}
                title={(!isInputValid || !hasChanges) ? 'Enter a valid user ID and make changes' : 'Save user ID'}
              >
                <Check className="w-4 h-4" />
                <span>Save User ID</span>
              </button>
              
              <button
                onClick={() => setInputValue(userId)}
                disabled={!hasChanges}
                className={`px-6 py-3 rounded-lg font-medium transition-all duration-200 flex items-center justify-center space-x-2 ${
                  !hasChanges
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : 'bg-gradient-to-r from-gray-500 to-gray-600 text-white hover:from-gray-600 hover:to-gray-700 shadow-lg hover:shadow-xl transform hover:scale-105'
                }`}
                title={!hasChanges ? 'No changes to cancel' : 'Cancel changes'}
              >
                <X className="w-4 h-4" />
                <span>Cancel</span>
              </button>
            </div>
          </div>

          {/* Validation Messages */}
          {!isInputValid && inputValue.length > 0 && (
            <div className="text-sm text-red-600">
              User ID must be 1-50 characters long
            </div>
          )}

          {hasChanges && isInputValid && (
            <div className="text-sm text-blue-600">
              Click save to update user ID
            </div>
          )}

          {/* Success Message */}
          {showSuccess && (
            <div className="text-sm text-green-600 flex items-center space-x-2">
              <Check className="w-4 h-4" />
              <span>User ID updated successfully!</span>
            </div>
          )}
        </div>

        {/* Reset to Default Button */}
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 pt-4 border-t border-gray-200">
          <button
            onClick={resetToDefault}
            className="flex items-center justify-center space-x-2 px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 transition-all duration-200 rounded-lg hover:bg-gray-50 border border-gray-300 hover:border-gray-400"
            title="Reset to default user ID"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Reset to Default</span>
          </button>

          <div className="text-xs text-gray-500 text-center sm:text-right">
            Press Enter to save, Esc to cancel
          </div>
        </div>
      </div>
    </div>
  )
}


