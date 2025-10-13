'use client'

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { config } from './config'

interface UserContextType {
  userId: string
  setUserId: (userId: string) => void
  isValidUserId: (userId: string) => boolean
  resetToDefault: () => void
}

const UserContext = createContext<UserContextType | undefined>(undefined)

interface UserProviderProps {
  children: ReactNode
}

const USER_ID_STORAGE_KEY = 'voice_agent_user_id'

export function UserProvider({ children }: UserProviderProps) {
  // Get initial userId from localStorage or fallback to config default
  const [userId, setUserIdState] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(USER_ID_STORAGE_KEY)
      const finalUserId = stored || config.defaultUserId
      console.log('👤 UserContext initialization:')
      console.log('👤 - Stored userId:', stored)
      console.log('👤 - Default userId:', config.defaultUserId)
      console.log('👤 - Final userId:', finalUserId)
      return finalUserId
    }
    const finalUserId = config.defaultUserId
    console.log('👤 UserContext initialization (server-side):', finalUserId)
    return finalUserId
  })

  // Validate userId format (basic validation)
  const isValidUserId = (userId: string): boolean => {
    return userId.trim().length > 0 && userId.trim().length <= 50
  }

  // Set userId with validation and persistence
  const setUserId = (newUserId: string) => {
    const trimmedUserId = newUserId.trim()

    if (!isValidUserId(trimmedUserId)) {
      console.warn('Invalid user ID format:', trimmedUserId)
      return
    }

    setUserIdState(trimmedUserId)

    // Persist to localStorage
    if (typeof window !== 'undefined') {
      localStorage.setItem(USER_ID_STORAGE_KEY, trimmedUserId)
    }

    console.log('👤 User ID updated to:', trimmedUserId)
  }

  // Reset to default user ID
  const resetToDefault = () => {
    const defaultUserId = config.defaultUserId
    setUserId(defaultUserId)
    console.log('👤 User ID reset to default:', defaultUserId)
  }

  // Persist userId changes to localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(USER_ID_STORAGE_KEY, userId)
    }
  }, [userId])

  const value: UserContextType = {
    userId,
    setUserId,
    isValidUserId,
    resetToDefault
  }

  return (
    <UserContext.Provider value={value}>
      {children}
    </UserContext.Provider>
  )
}

export function useUserContext(): UserContextType {
  const context = useContext(UserContext)
  if (context === undefined) {
    throw new Error('useUserContext must be used within a UserProvider')
  }
  return context
}


