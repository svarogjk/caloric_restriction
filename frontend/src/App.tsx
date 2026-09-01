import React, { useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useSelector } from 'react-redux'
import { RootState } from './store/store'
import { ChatContainer } from './components/chat'
import AuthModal from './components/auth/AuthModal'
import SharedResultPage from './components/SharedResultPage'
import AnalysisHistoryPage from './components/AnalysisHistoryPage'
import ComparisonPage from './components/ComparisonPage'
import HelpPage from './components/HelpPage'
import CookieConsent from './components/CookieConsent'
import ClinicalConsole from './components/console/ClinicalConsole'
import ClinicalHeader from './components/console/ClinicalHeader'

const MainLayout: React.FC = () => {
  const { isAuthenticated } = useSelector((state: RootState) => state.auth)
  const [authModalOpen, setAuthModalOpen] = useState(false)

  return (
    <div className="min-h-screen bg-canvas">
      <ClinicalHeader isAuthenticated={isAuthenticated} onOpenAuthModal={() => setAuthModalOpen(true)} />

      {/* Content */}
      <main className="h-[calc(100vh-var(--spacing-header))]">
        <Routes>
          {/* The clinical console is the front door — one thread, patient chart + conversation together. */}
          <Route path="/" element={<ClinicalConsole />} />
          {/* Free-text cross-cohort discovery — auxiliary, reached via the header. */}
          <Route path="/research" element={<ChatContainer />} />
          {/* Kept for one release for parity/bookmarks, then retires in favour of "/". */}
          {/* Retired: the console covers the same gallery → intake → readout →
              treatment path, with one scoring instance instead of two. */}
          <Route path="/oncologist" element={<Navigate to="/" replace />} />
          <Route path="/console" element={<Navigate to="/" replace />} />
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
