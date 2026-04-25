import React, { useState } from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { useSelector } from 'react-redux'
import { RootState } from './store/store'
import { ChatContainer } from './components/chat'
import { UserMenu } from './components/auth'
import AuthModal from './components/auth/AuthModal'
import SharedResultPage from './components/SharedResultPage'
import AnalysisHistoryPage from './components/AnalysisHistoryPage'
import ComparisonPage from './components/ComparisonPage'
import HelpPage from './components/HelpPage'
import CookieConsent from './components/CookieConsent'

const MainLayout: React.FC = () => {
  const { isAuthenticated } = useSelector((state: RootState) => state.auth)
  const [authModalOpen, setAuthModalOpen] = useState(false)

  return (
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
                to="/help"
                className="text-sm font-medium text-gray-500 hover:text-indigo-600 transition-colors"
              >
                Help
              </Link>
              {isAuthenticated && (
                <>
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
                </>
              )}
              {isAuthenticated ? (
                <UserMenu />
              ) : (
                <button
                  onClick={() => setAuthModalOpen(true)}
                  className="px-3 py-1.5 text-sm font-medium text-indigo-600 border border-indigo-300 rounded-md hover:bg-indigo-50 transition-colors"
                >
                  Sign in
                </button>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Content */}
      <main className="h-[calc(100vh-56px)]">
        <Routes>
          <Route path="/" element={<ChatContainer />} />
          <Route path="/help" element={<HelpPage />} />
          <Route path="/history" element={<AnalysisHistoryPage />} />
          <Route path="/compare" element={<ComparisonPage />} />
        </Routes>
      </main>

      {authModalOpen && <AuthModal onClose={() => setAuthModalOpen(false)} />}
      <CookieConsent />
    </div>
  )
}

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public shared result page */}
        <Route path="/results/:resultId" element={<SharedResultPage />} />
        {/* All other routes — no login required */}
        <Route path="/*" element={<MainLayout />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
