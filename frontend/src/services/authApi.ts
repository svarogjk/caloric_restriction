import axios from 'axios'

const API_BASE_URL = '/api'

const authClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

export interface User {
    id: string
    username: string
    email: string
    full_name: string | null
    disabled: boolean
}

export interface UserCreate {
    username: string
    email: string
    password: string
    full_name?: string
}

export interface Token {
    access_token: string
    token_type: string
}

export interface AuthError {
    detail: string
}

const TOKEN_KEY = 'auth_token'

export const getStoredToken = (): string | null => {
    return localStorage.getItem(TOKEN_KEY)
}

export const setStoredToken = (token: string): void => {
    localStorage.setItem(TOKEN_KEY, token)
}

export const removeStoredToken = (): void => {
    localStorage.removeItem(TOKEN_KEY)
}

export const register = async (userData: UserCreate): Promise<User> => {
    const response = await authClient.post<User>('/auth/register', userData)
    return response.data
}

export const login = async (username: string, password: string): Promise<Token> => {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)

    const response = await authClient.post<Token>('/auth/token', formData.toString(), {
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    })
    return response.data
}

export const getCurrentUser = async (token: string): Promise<User> => {
    const response = await authClient.get<User>('/auth/me', {
        headers: {
            Authorization: `Bearer ${token}`,
        },
    })
    return response.data
}

export const isTokenValid = async (token: string): Promise<boolean> => {
    try {
        await getCurrentUser(token)
        return true
    } catch {
        return false
    }
}
