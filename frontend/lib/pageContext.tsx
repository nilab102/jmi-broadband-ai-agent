'use client'

import React, { createContext, useContext, useState, ReactNode } from 'react'

// Supported pages - Only broadband page for the redesigned interface
export const SUPPORTED_PAGES = {
  'broadband': 'Broadband Search'
} as const

export type SupportedPage = keyof typeof SUPPORTED_PAGES

interface PageContextType {
  currentPage: SupportedPage
  setCurrentPage: (page: SupportedPage) => void
  getPageDisplayName: (page: SupportedPage) => string
  isSupportedPage: (page: string) => page is SupportedPage
}

const PageContext = createContext<PageContextType | undefined>(undefined)

interface PageProviderProps {
  children: ReactNode
  initialPage?: SupportedPage
}

export function PageProvider({ children, initialPage = 'broadband' }: PageProviderProps) {
  const [currentPage, setCurrentPage] = useState<SupportedPage>(initialPage)

  const getPageDisplayName = (page: SupportedPage): string => {
    return SUPPORTED_PAGES[page] || page
  }

  const isSupportedPage = (page: string): page is SupportedPage => {
    return page in SUPPORTED_PAGES
  }

  const value: PageContextType = {
    currentPage,
    setCurrentPage,
    getPageDisplayName,
    isSupportedPage
  }

  return (
    <PageContext.Provider value={value}>
      {children}
    </PageContext.Provider>
  )
}

export function usePageContext(): PageContextType {
  const context = useContext(PageContext)
  if (context === undefined) {
    throw new Error('usePageContext must be used within a PageProvider')
  }
  return context
}
