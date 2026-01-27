import { configureStore } from '@reduxjs/toolkit'
import searchReducer from './searchSlice'
import chatReducer from './chatSlice'
import authReducer from './authSlice'

export const store = configureStore({
    reducer: {
        search: searchReducer,
        chat: chatReducer,
        auth: authReducer,
    },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
