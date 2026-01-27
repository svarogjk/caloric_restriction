import React, { useState } from 'react'
import SearchPage from './components/SearchPage'
import { ChatContainer } from './components/chat'
import { AuthGuard, UserMenu } from './components/auth'

type ActiveView = 'search' | 'chat'

const App: React.FC = () => {
  const [activeView, setActiveView] = useState<ActiveView>('search')

  const handleRunAnalysis = (_query: string) => {
    // Switch to search view when running analysis from chat
    // The query is already set in Redux via ChatContainer
    setActiveView('search')
  }

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-100">
        {/* Navigation */}
        <nav className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4">
            <div className="flex items-center justify-between h-14">
              <h1 className="text-xl font-semibold text-gray-800">
                GEO Survival Analysis
              </h1>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setActiveView('search')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    activeView === 'search'
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  Search
                </button>
                <button
                  onClick={() => setActiveView('chat')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    activeView === 'chat'
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  AI Chat
                </button>
                <div className="w-px h-6 bg-gray-200 mx-2" />
                <UserMenu />
              </div>
            </div>
          </div>
        </nav>

        {/* Content */}
        <main className="h-[calc(100vh-56px)]">
          {activeView === 'search' ? (
            <SearchPage />
          ) : (
            <ChatContainer onRunAnalysis={handleRunAnalysis} />
          )}
        </main>
      </div>
    </AuthGuard>
  )
}

export default App
