import React from 'react'
import { ChatContainer } from './components/chat'
import { AuthGuard, UserMenu } from './components/auth'

const App: React.FC = () => {
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
              <UserMenu />
            </div>
          </div>
        </nav>

        {/* Content */}
        <main className="h-[calc(100vh-56px)]">
          <ChatContainer />
        </main>
      </div>
    </AuthGuard>
  )
}

export default App
