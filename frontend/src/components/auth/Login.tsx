import React, { useState, useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState, AppDispatch } from '../../store/store'
import { loginUser, clearError } from '../../store/authSlice'

interface LoginProps {
    onSwitchToRegister: () => void
    onLoginSuccess: () => void
    modal?: boolean
}

export const Login: React.FC<LoginProps> = ({ onSwitchToRegister, onLoginSuccess, modal = false }) => {
    const dispatch = useDispatch<AppDispatch>()
    const { loading, error, isAuthenticated } = useSelector((state: RootState) => state.auth)

    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')

    useEffect(() => {
        if (isAuthenticated) {
            onLoginSuccess()
        }
    }, [isAuthenticated, onLoginSuccess])

    useEffect(() => {
        return () => {
            dispatch(clearError())
        }
    }, [dispatch])

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        dispatch(loginUser({ username, password }))
    }

    const wrapper = modal ? 'py-6 px-6' : 'min-h-screen flex items-center justify-center bg-surface-sunken py-12 px-4'
    const inner = modal ? 'w-full space-y-6' : 'max-w-md w-full space-y-8'

    return (
        <div className={wrapper}>
            <div className={inner}>
                <div>
                    <h2 className="mt-2 text-center text-2xl font-bold text-fg-strong">
                        Sign in to your account
                    </h2>
                    <p className="mt-2 text-center text-sm text-fg-muted">
                        Or{' '}
                        <button
                            onClick={onSwitchToRegister}
                            className="font-medium text-accent-fg hover:text-accent-fg"
                        >
                            create a new account
                        </button>
                    </p>
                </div>

                <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
                    {error && (
                        <div className="bg-danger-soft border border-danger-border text-danger px-4 py-3 rounded relative">
                            {error}
                        </div>
                    )}

                    <div className="rounded-md shadow-sm space-y-4">
                        <div>
                            <label htmlFor="username" className="block text-sm font-medium text-fg">
                                Username
                            </label>
                            <input
                                id="username"
                                name="username"
                                type="text"
                                autoComplete="username"
                                required
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-border-strong rounded-md placeholder-fg-faint text-fg-strong focus:outline-none focus:ring-accent-ring focus:border-accent sm:text-sm"
                                placeholder="Username"
                            />
                        </div>

                        <div>
                            <label htmlFor="password" className="block text-sm font-medium text-fg">
                                Password
                            </label>
                            <input
                                id="password"
                                name="password"
                                type="password"
                                autoComplete="current-password"
                                required
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-border-strong rounded-md placeholder-fg-faint text-fg-strong focus:outline-none focus:ring-accent-ring focus:border-accent sm:text-sm"
                                placeholder="Password"
                            />
                        </div>
                    </div>

                    <div>
                        <button
                            type="submit"
                            disabled={loading}
                            className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-on-accent bg-accent hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-accent-ring disabled:bg-accent disabled:cursor-not-allowed"
                        >
                            {loading ? (
                                <span className="flex items-center">
                                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-on-accent" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                    Signing in...
                                </span>
                            ) : (
                                'Sign in'
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}

export default Login
