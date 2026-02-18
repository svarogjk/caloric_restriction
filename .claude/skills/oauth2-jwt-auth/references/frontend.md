# OAuth2 JWT Frontend Implementation

## Auth API Service (`frontend/src/services/authApi.ts`)

```typescript
import axios from 'axios'

const TOKEN_KEY = 'auth_token'

export interface User {
    id: string; username: string; email: string; full_name: string | null; disabled: boolean;
}
export interface Token {
    access_token: string; token_type: string;
}

export const getStoredToken = (): string | null => localStorage.getItem(TOKEN_KEY)
export const setStoredToken = (token: string): void => localStorage.setItem(TOKEN_KEY, token)
export const removeStoredToken = (): void => localStorage.removeItem(TOKEN_KEY)

export const login = async (username: string, password: string): Promise<Token> => {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)
    const response = await axios.post<Token>('/api/auth/token', formData.toString(), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return response.data
}

export const register = async (userData: UserCreate): Promise<User> => {
    const response = await axios.post<User>('/api/auth/register', userData)
    return response.data
}

export const getCurrentUser = async (token: string): Promise<User> => {
    const response = await axios.get<User>('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
}
```

## Auth Redux Slice (`frontend/src/store/authSlice.ts`)

```typescript
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { login as loginApi, getCurrentUser, getStoredToken, setStoredToken, removeStoredToken } from '../services/authApi'

interface AuthState {
    user: User | null; token: string | null; isAuthenticated: boolean; loading: boolean; error: string | null;
}

export const loginUser = createAsyncThunk('auth/login',
    async ({ username, password }, { rejectWithValue }) => {
        try {
            const tokenResponse = await loginApi(username, password)
            setStoredToken(tokenResponse.access_token)
            const user = await getCurrentUser(tokenResponse.access_token)
            return { user, token: tokenResponse.access_token }
        } catch (error) {
            removeStoredToken()
            return rejectWithValue(error.response?.data?.detail || 'Login failed')
        }
    }
)

export const checkAuth = createAsyncThunk('auth/check',
    async (_, { rejectWithValue }) => {
        const token = getStoredToken()
        if (!token) return rejectWithValue('No token')
        try { return await getCurrentUser(token) }
        catch { removeStoredToken(); return rejectWithValue('Invalid token') }
    }
)

const authSlice = createSlice({
    name: 'auth',
    initialState: { user: null, token: getStoredToken(), isAuthenticated: false, loading: false, error: null },
    reducers: {
        logout: (state) => { removeStoredToken(); state.user = null; state.token = null; state.isAuthenticated = false; },
    },
    extraReducers: (builder) => {
        builder
            .addCase(loginUser.fulfilled, (state, action) => {
                state.user = action.payload.user; state.token = action.payload.token; state.isAuthenticated = true;
            })
            .addCase(checkAuth.fulfilled, (state, action) => {
                state.user = action.payload; state.isAuthenticated = true;
            })
    },
})
```

## API Client with Interceptors (`frontend/src/services/api.ts`)

```typescript
import axios from 'axios'
import { getStoredToken, removeStoredToken } from './authApi'

const apiClient = axios.create({ baseURL: '/api', headers: { 'Content-Type': 'application/json' } })

apiClient.interceptors.request.use((config) => {
    const token = getStoredToken()
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
})

apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            removeStoredToken()
            window.dispatchEvent(new CustomEvent('auth:unauthorized'))
        }
        return Promise.reject(error)
    }
)
```

## AuthGuard Component (`frontend/src/components/auth/AuthGuard.tsx`)

```typescript
export const AuthGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const dispatch = useDispatch()
    const { isAuthenticated, loading, token } = useSelector((state) => state.auth)
    const [authView, setAuthView] = useState<'login' | 'register'>('login')

    useEffect(() => {
        if (token && !isAuthenticated) dispatch(checkAuth())
    }, [dispatch, token, isAuthenticated])

    useEffect(() => {
        const handleUnauthorized = () => dispatch(logout())
        window.addEventListener('auth:unauthorized', handleUnauthorized)
        return () => window.removeEventListener('auth:unauthorized', handleUnauthorized)
    }, [dispatch])

    if (loading) return <LoadingSpinner />
    if (!isAuthenticated) {
        return authView === 'login'
            ? <Login onSwitchToRegister={() => setAuthView('register')} />
            : <Register onSwitchToLogin={() => setAuthView('login')} />
    }
    return <>{children}</>
}
```

## Usage in App.tsx

```typescript
import { AuthGuard, UserMenu } from './components/auth'

const App = () => (
    <AuthGuard>
        <nav><h1>App Title</h1><UserMenu /></nav>
        <main>{/* Protected content */}</main>
    </AuthGuard>
)
```
