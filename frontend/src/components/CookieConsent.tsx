import React, { useState, useEffect } from 'react'

const CookieConsent: React.FC = () => {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (!localStorage.getItem('cookieConsent')) {
      setVisible(true)
    }
  }, [])

  const accept = () => {
    localStorage.setItem('cookieConsent', 'true')
    setVisible(false)
  }

  if (!visible) return null

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-lg z-50 px-4 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        <p className="text-sm text-gray-600">
          This site uses cookies to improve your experience. By continuing, you agree to our use of cookies.
        </p>
        <button
          onClick={accept}
          className="shrink-0 px-4 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 transition-colors"
        >
          Accept
        </button>
      </div>
    </div>
  )
}

export default CookieConsent
