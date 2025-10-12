'use client'

import React, { useState } from 'react'
import { config } from '@/lib/config'

export function ConnectionTest() {
  const [testResults, setTestResults] = useState<string[]>([])
  const [isTesting, setIsTesting] = useState(false)

  const addResult = (result: string) => {
    setTestResults(prev => [...prev, `${new Date().toLocaleTimeString()}: ${result}`])
  }

  const runTests = async () => {
    setIsTesting(true)
    setTestResults([])
    
    addResult('Starting connection tests...')
    
    // Test 1: Health endpoint
    try {
      addResult('Testing health endpoint...')
      const response = await fetch(config.api.health)
      if (response.ok) {
        const data = await response.json()
        addResult(`✅ Health check passed: ${data.status}`)
        addResult(`   Environment: ${data.environment?.mode || 'unknown'}`)
        addResult(`   LLM Provider: ${data.llm_service?.provider || 'unknown'}`)
        addResult(`   LLM Available: ${data.llm_service?.available ? 'Yes' : 'No'}`)
      } else {
        addResult(`❌ Health check failed: ${response.status}`)
      }
    } catch (error) {
      addResult(`❌ Health check error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
    
    // Test 2: Connect endpoint (with required current_page parameter)
    try {
      addResult('Testing connect endpoint...')
      const response = await fetch(config.api.connect, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          user_id: 'test_user',
          current_page: 'dashboard' // Required parameter
        })
      })
      if (response.ok) {
        const data = await response.json()
        addResult(`✅ Connect endpoint passed: ${data.ws_url}`)
        addResult(`   User ID: ${data.user_id || 'auto-generated'}`)
        addResult(`   Current Page: ${data.current_page}`)
      } else {
        const errorData = await response.json().catch(() => ({}))
        addResult(`❌ Connect endpoint failed: ${response.status}`)
        if (errorData.detail) {
          addResult(`   Error: ${JSON.stringify(errorData.detail)}`)
        }
      }
    } catch (error) {
      addResult(`❌ Connect endpoint error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
    
    // Test 3: WebSocket connection (using correct URL format)
    try {
      addResult('Testing WebSocket connection...')
      const wsUrl = config.websocket.conversation('test_user', 'dashboard')
      addResult(`   WebSocket URL: ${wsUrl}`)
      
      const ws = new WebSocket(wsUrl)
      
      const timeout = setTimeout(() => {
        addResult('❌ WebSocket connection timeout')
        ws.close()
      }, 5000)
      
      ws.onopen = () => {
        clearTimeout(timeout)
        addResult('✅ WebSocket connection successful')
        ws.close()
      }
      
      ws.onerror = (error) => {
        clearTimeout(timeout)
        addResult(`❌ WebSocket connection error: ${error}`)
      }
      
      ws.onclose = (event) => {
        clearTimeout(timeout)
        if (event.code === 1000) {
          addResult('✅ WebSocket closed normally')
        } else {
          addResult(`⚠️ WebSocket closed with code: ${event.code}`)
        }
      }
    } catch (error) {
      addResult(`❌ WebSocket test error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
    
    // Test 4: Test database search endpoint (if available)
    try {
      addResult('Testing database search endpoint...')
      const response = await fetch(config.api.testDatabaseSearch)
      if (response.ok) {
        const data = await response.json()
        addResult(`✅ Database search test: ${data.message || 'Success'}`)
      } else {
        addResult(`❌ Database search test failed: ${response.status}`)
      }
    } catch (error) {
      addResult(`❌ Database search test error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
    
    // Test 5: Test function call endpoint
    try {
      addResult('Testing function call endpoint...')
      const response = await fetch(config.api.testFunctionCall)
      if (response.ok) {
        const data = await response.json()
        addResult(`✅ Function call test: ${data.message}`)
        addResult(`   Tool Available: ${data.tool_available ? 'Yes' : 'No'}`)
        addResult(`   Function Calling Enabled: ${data.function_calling_enabled ? 'Yes' : 'No'}`)
      } else {
        addResult(`❌ Function call test failed: ${response.status}`)
      }
    } catch (error) {
      addResult(`❌ Function call test error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
    
    // Test 6: Test tools WebSocket connection
    try {
      addResult('Testing tools WebSocket connection...')
      const toolsWsUrl = config.websocket.tools('test_user', 'dashboard')
      addResult(`   Tools WebSocket URL: ${toolsWsUrl}`)
      
      const ws = new WebSocket(toolsWsUrl)
      
      const timeout = setTimeout(() => {
        addResult('❌ Tools WebSocket connection timeout')
        ws.close()
      }, 5000)
      
      ws.onopen = () => {
        clearTimeout(timeout)
        addResult('✅ Tools WebSocket connection successful')
        ws.close()
      }
      
      ws.onerror = (error) => {
        clearTimeout(timeout)
        addResult(`❌ Tools WebSocket connection error: ${error}`)
      }
      
      ws.onclose = (event) => {
        clearTimeout(timeout)
        if (event.code === 1000) {
          addResult('✅ Tools WebSocket closed normally')
        } else {
          addResult(`⚠️ Tools WebSocket closed with code: ${event.code}`)
        }
      }
    } catch (error) {
      addResult(`❌ Tools WebSocket test error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
    
    addResult('Connection tests completed')
    setIsTesting(false)
  }

  return (
    <div className="bg-white rounded-2xl shadow-xl border border-orange-100 overflow-hidden backdrop-blur-sm">
      <div className="bg-gradient-to-r from-orange-500 via-red-600 to-pink-500 px-6 py-4">
        <div className="flex items-center justify-between text-white">
          <div className="flex items-center space-x-3">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6">
              <path d="M9 12l2 2 4-4"/>
              <path d="M21 12c-1 0-2-1-2-2s1-2 2-2 2 1 2 2-1 2-2 2z"/>
              <path d="M3 12c1 0 2-1 2-2s-1-2-2-2-2 1-2 2 1 2 2 2z"/>
            </svg>
            <h2 className="text-lg font-semibold">Connection Test</h2>
          </div>
          <button
            onClick={runTests}
            disabled={isTesting}
            className="text-white hover:text-gray-200 text-sm px-3 py-1 rounded border border-white/30 disabled:opacity-50"
          >
            {isTesting ? 'Testing...' : 'Run Tests'}
          </button>
        </div>
      </div>
      
      <div className="p-6">
        <div className="h-64 overflow-y-auto space-y-2 p-4 bg-gray-50 rounded-lg">
          {testResults.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <div className="text-4xl mb-2">🔍</div>
              <p>No test results yet</p>
              <p className="text-sm">Click "Run Tests" to check backend connectivity</p>
            </div>
          ) : (
            testResults.map((result, index) => (
              <div key={index} className="text-sm font-mono">
                {result}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
