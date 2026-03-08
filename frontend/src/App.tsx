import React from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { ChatContainer } from './components/chat'
import { AuthGuard, UserMenu } from './components/auth'
import SharedResultPage from './components/SharedResultPage'
import AnalysisHistoryPage from './components/AnalysisHistoryPage'
import ComparisonPage from './components/ComparisonPage'

const AuthenticatedApp: React.FC = () => (
  <AuthGuard>
    <div className="min-h-screen bg-gray-100">
      {/* Navigation */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex items-center justify-between h-14">
            <Link to="/" className="text-xl font-semibold text-gray-800 hover:text-indigo-600 transition-colors">
              GEO Survival Analysis
            </Link>
            <div className="flex items-center gap-4">
              <Link
                to="/history"
                className="text-sm font-medium text-gray-500 hover:text-indigo-600 transition-colors"
              >
                History
              </Link>
              <Link
                to="/compare"
                className="text-sm font-medium text-gray-500 hover:text-indigo-600 transition-colors"
              >
                Compare
              </Link>
              <UserMenu />
            </div>
          </div>
        </div>
      </nav>

      {/* Content */}
      <main className="h-[calc(100vh-56px)]">
        <Routes>
          <Route path="/" element={<ChatContainer />} />
          <Route path="/history" element={<AnalysisHistoryPage />} />
          <Route path="/compare" element={<ComparisonPage />} />
        </Routes>
      </main>
    </div>
  </AuthGuard>
)

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public route — no auth required */}
        <Route path="/results/:resultId" element={<SharedResultPage />} />

        {/* All other routes require auth */}
        <Route path="/*" element={<AuthenticatedApp />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
