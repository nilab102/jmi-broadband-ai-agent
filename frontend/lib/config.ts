// Configuration for the voice agent frontend

// Environment detection and URL selection
const getBackendUrl = () => {
  const environment = process.env.NEXT_PUBLIC_ENVIRONMENT || 'development'

  console.log(`🔧 === FRONTEND ENVIRONMENT DEBUG INFO ===`)
  console.log(`🔧 Environment: ${environment}`)
  console.log(`🔧 NEXT_PUBLIC_DEV_BACKEND_URL: ${process.env.NEXT_PUBLIC_DEV_BACKEND_URL || 'NOT_SET'}`)
  console.log(`🔧 NEXT_PUBLIC_PROD_BACKEND_URL: ${process.env.NEXT_PUBLIC_PROD_BACKEND_URL || 'NOT_SET'}`)

  let selectedUrl: string

  // Fix hardcoded fallback - use proper defaults based on environment
  if (environment === 'production') {
    selectedUrl = process.env.NEXT_PUBLIC_PROD_BACKEND_URL || 'https://176.9.16.194:8200'
    if (!process.env.NEXT_PUBLIC_PROD_BACKEND_URL) {
      console.warn('⚠️ NEXT_PUBLIC_PROD_BACKEND_URL not set, using default production URL')
    }
  } else {
    selectedUrl = process.env.NEXT_PUBLIC_DEV_BACKEND_URL || 'https://localhost:8200'
    if (!process.env.NEXT_PUBLIC_DEV_BACKEND_URL) {
      console.warn('⚠️ NEXT_PUBLIC_DEV_BACKEND_URL not set, using default development URL')
    }
  }

  console.log(`🌐 Backend URL: ${selectedUrl}`)
  console.log(`🔧 ===============================`)

  return selectedUrl
}

// Backend URL configuration
const backendConfig = {
  baseUrl: getBackendUrl(),
  voicePrefix: '/voice',
  environment: process.env.NEXT_PUBLIC_ENVIRONMENT || 'development',
}

export const config = {
  // Backend URL configuration
  backend: backendConfig,
  
  // WebSocket URLs
  websocket: {
    conversation: (userId?: string, currentPage?: string) => {
      const base = `${backendConfig.baseUrl.replace('https://', 'wss://').replace('http://', 'ws://')}${backendConfig.voicePrefix}/ws`
      const params = new URLSearchParams()
      if (userId) params.append('user_id', userId)
      if (currentPage) params.append('current_page', currentPage)
      const queryString = params.toString()
      return queryString ? `${base}?${queryString}` : base
    },
    tools: (userId: string, currentPage?: string) => {
      const base = `${backendConfig.baseUrl.replace('https://', 'wss://').replace('http://', 'ws://')}${backendConfig.voicePrefix}/ws/tools`
      const params = new URLSearchParams()
      params.append('user_id', userId)
      if (currentPage) params.append('current_page', currentPage)
      return `${base}?${params.toString()}`
    },
    textConversation: (userId: string, currentPage?: string) => {
      const base = `${backendConfig.baseUrl.replace('https://', 'wss://').replace('http://', 'ws://')}${backendConfig.voicePrefix}/ws/text-conversation`
      const params = new URLSearchParams()
      params.append('user_id', userId)
      if (currentPage) params.append('current_page', currentPage)
      return `${base}?${params.toString()}`
    },
  },
  
  // API endpoints
  api: {
    connect: `${backendConfig.baseUrl}${backendConfig.voicePrefix}/connect`,
    health: `${backendConfig.baseUrl}${backendConfig.voicePrefix}/health`,
    testDatabaseSearch: `${backendConfig.baseUrl}${backendConfig.voicePrefix}/test-database-search`,
    testFunctionCall: `${backendConfig.baseUrl}${backendConfig.voicePrefix}/test-function-call`,
  },
  
  // User configuration
  defaultUserId: process.env.NEXT_PUBLIC_DEFAULT_USER_ID || 'frontend_user',
  
  // Environment and debugging
  environment: backendConfig.environment,
  isProduction: backendConfig.environment === 'production',
  isDevelopment: backendConfig.environment === 'development',
  enableDebug: process.env.NEXT_PUBLIC_ENABLE_VOICE_DEBUG === 'true',
}

// Helper function to get the base RTVI config
export const getRTVIConfig = (currentPage?: string, userId?: string) => {
  console.log(`🔗 getRTVIConfig called with current_page:`, currentPage, 'userId:', userId)
  console.log(`🔗 current_page type:`, typeof currentPage, 'userId type:', typeof userId)

  let connectEndpoint = `${backendConfig.voicePrefix}/connect`

  const params = new URLSearchParams()
  if (userId) params.append('user_id', userId)
  if (currentPage) params.append('current_page', currentPage)

  const queryString = params.toString()
  if (queryString) {
    connectEndpoint += `?${queryString}`
  }

  console.log(`🔗 Creating RTVI config with connect endpoint:`, connectEndpoint)
  return {
    baseUrl: backendConfig.baseUrl,
    endpoints: { connect: connectEndpoint },
  };
}
