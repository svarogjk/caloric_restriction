import React, { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState, AppDispatch } from '../../store/store'
import { checkAuth, logout } from '../../store/authSlice'
import { Login } from './Login'
import { Register } from './Register'

interface AuthGuardProps {
    children: React.ReactNode
    requireAuth?: boolean
}

type AuthView = 'login' | 'register'

export const AuthGuard: React.FC<AuthGuardProps> = ({ children, requireAuth = true }) => {
    const dispatch = useDispatch<AppDispatch>()
    const { isAuthenticated, loading, token } = useSelector((state: RootState) => state.auth)
    const [authView, setAuthView] = useState<AuthView>('login')
    const [initialCheckDone, setInitialCheckDone] = useState(false)

    useEffect(() => {
        if (token && !isAuthenticated) {
            dispatch(checkAuth()).finally(() => setInitialCheckDone(true))
        } else {
            setInitialCheckDone(true)
        }
    }, [dispatch, token, isAuthenticated])

    useEffect(() => {
        const handleUnauthorized = () => {
            dispatch(logout())
        }
        window.addEventListener('auth:unauthorized', handleUnauthorized)
        return () => {
            window.removeEventListener('auth:unauthorized', handleUnauthorized)
        }
    }, [dispatch])

    if (!initialCheckDone || loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-100">
                <div className="text-center">
                    <svg className="animate-spin h-10 w-10 text-blue-600 mx-auto" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <p className="mt-4 text-gray-600">Loading...</p>
                </div>
            </div>
        )
    }

    if (!requireAuth) {
        return <>{children}</>
    }

    if (!isAuthenticated) {
        if (authView === 'login') {
            return (
                <Login
                    onSwitchToRegister={() => setAuthView('register')}
                    onLoginSuccess={() => {}}
                />
            )
        }
        return (
            <Register
                onSwitchToLogin={() => setAuthView('login')}
                onRegisterSuccess={() => setAuthView('login')}
            />
        )
    }

    return <>{children}</>
}

export default AuthGuard
