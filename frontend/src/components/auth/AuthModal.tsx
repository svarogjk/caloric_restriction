import React, { useState, useEffect } from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../../store/store'
import { Login } from './Login'
import { Register } from './Register'

interface AuthModalProps {
    onClose: () => void
}

type AuthView = 'login' | 'register'

const AuthModal: React.FC<AuthModalProps> = ({ onClose }) => {
    const { isAuthenticated } = useSelector((state: RootState) => state.auth)
    const [view, setView] = useState<AuthView>('login')

    // Close automatically on successful login
    useEffect(() => {
        if (isAuthenticated) {
            onClose()
        }
    }, [isAuthenticated, onClose])

    return (
        <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
            onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
        >
            <div className="bg-surface rounded-xl shadow-xl w-full max-w-md mx-4 relative">
                <button
                    onClick={onClose}
                    className="absolute top-3 right-3 text-fg-faint hover:text-fg-muted transition-colors"
                    aria-label="Close"
                >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>

                <div className="p-1">
                    {view === 'login' ? (
                        <Login
                            onSwitchToRegister={() => setView('register')}
                            onLoginSuccess={onClose}
                            modal
                        />
                    ) : (
                        <Register
                            onSwitchToLogin={() => setView('login')}
                            onRegisterSuccess={() => setView('login')}
                            modal
                        />
                    )}
                </div>
            </div>
        </div>
    )
}

export default AuthModal
