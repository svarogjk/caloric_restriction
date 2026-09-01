import React, { useState, useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState, AppDispatch } from '../../store/store'
import { registerUser, clearError, clearRegisterSuccess } from '../../store/authSlice'

interface RegisterProps {
    onSwitchToLogin: () => void
    onRegisterSuccess: () => void
    modal?: boolean
}

export const Register: React.FC<RegisterProps> = ({ onSwitchToLogin, onRegisterSuccess, modal = false }) => {
    const dispatch = useDispatch<AppDispatch>()
    const { loading, error, registerSuccess } = useSelector((state: RootState) => state.auth)

    const [username, setUsername] = useState('')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [fullName, setFullName] = useState('')
    const [validationError, setValidationError] = useState<string | null>(null)

    useEffect(() => {
        if (registerSuccess) {
            dispatch(clearRegisterSuccess())
            onRegisterSuccess()
        }
    }, [registerSuccess, dispatch, onRegisterSuccess])

    useEffect(() => {
        return () => {
            dispatch(clearError())
        }
    }, [dispatch])

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        setValidationError(null)

        if (password !== confirmPassword) {
            setValidationError('Passwords do not match')
            return
        }

        if (password.length < 8) {
            setValidationError('Password must be at least 8 characters')
            return
        }

        dispatch(registerUser({
            username,
            email: email || undefined,
            password,
            full_name: fullName || undefined,
        }))
    }

    const displayError = validationError || error

    const wrapper = modal ? 'py-6 px-6' : 'min-h-screen flex items-center justify-center bg-surface-sunken py-12 px-4'
    const inner = modal ? 'w-full space-y-4' : 'max-w-md w-full space-y-6'

    return (
        <div className={wrapper}>
            <div className={inner}>
                <div>
                    <h2 className="mt-2 text-center text-2xl font-bold text-fg-strong">
                        Create your account
                    </h2>
                    <p className="mt-2 text-center text-sm text-fg-muted">
                        Or{' '}
                        <button
                            onClick={onSwitchToLogin}
                            className="font-medium text-accent-fg hover:text-accent-fg"
                        >
                            sign in to existing account
                        </button>
                    </p>
                </div>

                <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
                    {displayError && (
                        <div className="bg-danger-soft border border-danger-border text-danger px-4 py-3 rounded relative">
                            {displayError}
                        </div>
                    )}

                    <div className="rounded-md shadow-sm space-y-4">
                        <div>
                            <label htmlFor="username" className="block text-sm font-medium text-fg">
                                Username *
                            </label>
                            <input
                                id="username"
                                name="username"
                                type="text"
                                autoComplete="username"
                                required
                                minLength={3}
                                maxLength={50}
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-border-strong rounded-md placeholder-fg-faint text-fg-strong focus:outline-none focus:ring-accent-ring focus:border-accent sm:text-sm"
                                placeholder="Username (3-50 characters)"
                            />
                        </div>

                        <div>
                            <label htmlFor="email" className="block text-sm font-medium text-fg">
                                Email <span className="text-fg-faint font-normal">(optional)</span>
                            </label>
                            <input
                                id="email"
                                name="email"
                                type="email"
                                autoComplete="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-border-strong rounded-md placeholder-fg-faint text-fg-strong focus:outline-none focus:ring-accent-ring focus:border-accent sm:text-sm"
                                placeholder="email@example.com (optional)"
                            />
                        </div>

                        <div>
                            <label htmlFor="fullName" className="block text-sm font-medium text-fg">
                                Full Name
                            </label>
                            <input
                                id="fullName"
                                name="fullName"
                                type="text"
                                autoComplete="name"
                                value={fullName}
                                onChange={(e) => setFullName(e.target.value)}
                                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-border-strong rounded-md placeholder-fg-faint text-fg-strong focus:outline-none focus:ring-accent-ring focus:border-accent sm:text-sm"
                                placeholder="John Doe (optional)"
                            />
                        </div>

                        <div>
                            <label htmlFor="password" className="block text-sm font-medium text-fg">
                                Password *
                            </label>
                            <input
                                id="password"
                                name="password"
                                type="password"
                                autoComplete="new-password"
                                required
                                minLength={8}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-border-strong rounded-md placeholder-fg-faint text-fg-strong focus:outline-none focus:ring-accent-ring focus:border-accent sm:text-sm"
                                placeholder="Minimum 8 characters"
                            />
                        </div>

                        <div>
                            <label htmlFor="confirmPassword" className="block text-sm font-medium text-fg">
                                Confirm Password *
                            </label>
                            <input
                                id="confirmPassword"
                                name="confirmPassword"
                                type="password"
                                autoComplete="new-password"
                                required
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-border-strong rounded-md placeholder-fg-faint text-fg-strong focus:outline-none focus:ring-accent-ring focus:border-accent sm:text-sm"
                                placeholder="Confirm your password"
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
                                    Creating account...
                                </span>
                            ) : (
                                'Create account'
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}

export default Register
