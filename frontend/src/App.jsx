import { useState, useRef, useEffect } from 'react'
import { Send, Shield, User, Bot, Lock, LogOut, Settings } from 'lucide-react'

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [apiKey, setApiKey] = useState(localStorage.getItem('apiKey') || '')
  const [showApiKeyInput, setShowApiKeyInput] = useState(!apiKey)
  const [user, setUser] = useState(null)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleApiKeySubmit = (e) => {
    e.preventDefault()
    if (apiKey.trim()) {
      localStorage.setItem('apiKey', apiKey.trim())
      setShowApiKeyInput(false)
      verifyApiKey()
    }
  }

  const verifyApiKey = async () => {
    try {
      const response = await fetch('/api/auth/current', {
        headers: {
          'X-API-Key': apiKey.trim(),
        },
      })
      if (response.ok) {
        const data = await response.json()
        setUser(data)
      }
    } catch (error) {
      console.error('Failed to verify API key:', error)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('apiKey')
    setApiKey('')
    setUser(null)
    setShowApiKeyInput(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage = { role: 'user', content: input.trim() }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)
    setIsStreaming(true)

    try {
      const response = await fetch('/api/query/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey.trim(),
        },
        body: JSON.stringify({
          query: userMessage.content,
          sources: ['mitre', 'cve', 'logs', 'playbooks'],
          top_k: 5,
        }),
      })

      if (!response.ok) {
        throw new Error('Query failed')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let assistantMessage = { role: 'assistant', content: '' }
      setMessages(prev => [...prev, assistantMessage])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n').filter(line => line.trim())

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') {
              setIsStreaming(false)
              setIsLoading(false)
              break
            }
            try {
              const parsed = JSON.parse(data)
              if (parsed.content) {
                setMessages(prev => {
                  const updated = [...prev]
                  updated[updated.length - 1] = {
                    ...updated[updated.length - 1],
                    content: updated[updated.length - 1].content + parsed.content,
                  }
                  return updated
                })
              }
            } catch (e) {
              // Ignore parse errors for partial chunks
            }
          }
        }
      }
    } catch (error) {
      console.error('Query error:', error)
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Sorry, an error occurred. Please try again.' },
      ])
    } finally {
      setIsLoading(false)
      setIsStreaming(false)
    }
  }

  if (showApiKeyInput) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-gray-800 rounded-lg shadow-xl p-8">
          <div className="flex items-center justify-center mb-6">
            <Shield className="w-12 h-12 text-blue-500" />
          </div>
          <h1 className="text-2xl font-bold text-white text-center mb-2">Security Copilot</h1>
          <p className="text-gray-400 text-center mb-6">Enter your API key to continue</p>
          <form onSubmit={handleApiKeySubmit} className="space-y-4">
            <div>
              <label htmlFor="apiKey" className="block text-sm font-medium text-gray-300 mb-2">
                API Key
              </label>
              <input
                id="apiKey"
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter your API key"
                required
              />
            </div>
            <button
              type="submit"
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
            >
              <Lock className="w-4 h-4 inline mr-2" />
              Authenticate
            </button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900 flex flex-col">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Shield className="w-6 h-6 text-blue-500" />
            <h1 className="text-xl font-bold text-white">Security Copilot</h1>
          </div>
          <div className="flex items-center space-x-4">
            {user && (
              <div className="flex items-center space-x-2 text-gray-300">
                <User className="w-4 h-4" />
                <span className="text-sm">{user.username}</span>
              </div>
            )}
            <button
              onClick={handleLogout}
              className="text-gray-400 hover:text-white transition-colors"
              title="Logout"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Chat Area */}
      <main className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-12">
              <Bot className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-300 mb-2">
                Welcome to Security Copilot
              </h2>
              <p className="text-gray-500">
                Ask me anything about security techniques, CVEs, logs, or incident response playbooks.
              </p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`flex items-start space-x-3 ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {message.role === 'assistant' && (
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                )}
                <div
                  className={`max-w-2xl rounded-lg px-4 py-3 ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-800 text-gray-100'
                  }`}
                >
                  <p className="whitespace-pre-wrap break-words">{message.content}</p>
                </div>
                {message.role === 'user' && (
                  <div className="flex-shrink-0 w-8 h-8 bg-gray-700 rounded-full flex items-center justify-center">
                    <User className="w-5 h-5 text-gray-300" />
                  </div>
                )}
              </div>
            ))
          )}
          {isStreaming && (
            <div className="flex items-start space-x-3 justify-start">
              <div className="flex-shrink-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div className="bg-gray-800 rounded-lg px-4 py-3">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input Area */}
      <footer className="bg-gray-800 border-t border-gray-700 px-4 py-4">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit} className="flex space-x-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
              className="flex-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              placeholder="Ask a security question..."
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-medium py-2 px-4 rounded-lg transition-colors flex items-center"
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
        </div>
      </footer>
    </div>
  )
}

export default App
