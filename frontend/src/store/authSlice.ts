import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import {
    User,
    UserCreate,
    Token,
    login as loginApi,
    register as registerApi,
    getCurrentUser,
    getStoredToken,
    setStoredToken,
    removeStoredToken,
} from '../services/authApi'

interface AuthState {
    user: User | null
    token: string | null
    isAuthenticated: boolean
    loading: boolean
    error: string | null
    registerSuccess: boolean
}

const initialState: AuthState = {
    user: null,
    token: getStoredToken(),
    isAuthenticated: false,
    loading: false,
    error: null,
    registerSuccess: false,
}

export const loginUser = createAsyncThunk<
    { user: User; token: string },
    { username: string; password: string },
    { rejectValue: string }
>('auth/login', async ({ username, password }, { rejectWithValue }) => {
    try {
        const tokenResponse: Token = await loginApi(username, password)
        setStoredToken(tokenResponse.access_token)
        const user = await getCurrentUser(tokenResponse.access_token)
        return { user, token: tokenResponse.access_token }
    } catch (error) {
        removeStoredToken()
        if (error instanceof Error) {
            const axiosError = error as { response?: { data?: { detail?: string } } }
            if (axiosError.response?.data?.detail) {
                return rejectWithValue(axiosError.response.data.detail)
            }
            return rejectWithValue(error.message)
        }
        return rejectWithValue('Login failed')
    }
})

export const registerUser = createAsyncThunk<
    User,
    UserCreate,
    { rejectValue: string }
>('auth/register', async (userData, { rejectWithValue }) => {
    try {
        const user = await registerApi(userData)
        return user
    } catch (error) {
        if (error instanceof Error) {
            const axiosError = error as { response?: { data?: { detail?: string } } }
            if (axiosError.response?.data?.detail) {
                return rejectWithValue(axiosError.response.data.detail)
            }
            return rejectWithValue(error.message)
        }
        return rejectWithValue('Registration failed')
    }
})

export const checkAuth = createAsyncThunk<
    User,
    void,
    { rejectValue: string }
>('auth/check', async (_, { rejectWithValue }) => {
    const token = getStoredToken()
    if (!token) {
        return rejectWithValue('No token found')
    }

    try {
        const user = await getCurrentUser(token)
        return user
    } catch (error) {
        removeStoredToken()
        if (error instanceof Error) {
            return rejectWithValue(error.message)
        }
        return rejectWithValue('Token validation failed')
    }
})

const authSlice = createSlice({
    name: 'auth',
    initialState,
    reducers: {
        logout: (state) => {
            removeStoredToken()
            state.user = null
            state.token = null
            state.isAuthenticated = false
            state.error = null
        },
        clearError: (state) => {
            state.error = null
        },
        clearRegisterSuccess: (state) => {
            state.registerSuccess = false
        },
    },
    extraReducers: (builder) => {
        builder
            // Login
            .addCase(loginUser.pending, (state) => {
                state.loading = true
                state.error = null
            })
            .addCase(loginUser.fulfilled, (state, action) => {
                state.loading = false
                state.user = action.payload.user
                state.token = action.payload.token
                state.isAuthenticated = true
                state.error = null
            })
            .addCase(loginUser.rejected, (state, action) => {
                state.loading = false
                state.error = action.payload ?? 'Login failed'
                state.isAuthenticated = false
            })
            // Register
            .addCase(registerUser.pending, (state) => {
                state.loading = true
                state.error = null
                state.registerSuccess = false
            })
            .addCase(registerUser.fulfilled, (state) => {
                state.loading = false
                state.registerSuccess = true
                state.error = null
            })
            .addCase(registerUser.rejected, (state, action) => {
                state.loading = false
                state.error = action.payload ?? 'Registration failed'
                state.registerSuccess = false
            })
            // Check Auth
            .addCase(checkAuth.pending, (state) => {
                state.loading = true
            })
            .addCase(checkAuth.fulfilled, (state, action) => {
                state.loading = false
                state.user = action.payload
                state.isAuthenticated = true
                state.error = null
            })
            .addCase(checkAuth.rejected, (state) => {
                state.loading = false
                state.user = null
                state.token = null
                state.isAuthenticated = false
            })
    },
})

export const { logout, clearError, clearRegisterSuccess } = authSlice.actions
export default authSlice.reducer
