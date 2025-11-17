import { createSlice, PayloadAction } from '@reduxjs/toolkit'

export interface Dataset {
    id: string
    name: string
    description: string
    geneExpression: {
        log2FoldChange: number
        pValue: number
        gene: string
    }[]
}

export interface SearchState {
    query: string
    selectedModel: string
    results: Dataset[]
    loading: boolean
    error: string | null
    expandedDatasetId: string | null
}

const initialState: SearchState = {
    query: '',
    selectedModel: 'all-models',
    results: [],
    loading: false,
    error: null,
    expandedDatasetId: null,
}

const searchSlice = createSlice({
    name: 'search',
    initialState,
    reducers: {
        setQuery: (state, action: PayloadAction<string>) => {
            state.query = action.payload
        },
        setSelectedModel: (state, action: PayloadAction<string>) => {
            state.selectedModel = action.payload
        },
        setLoading: (state, action: PayloadAction<boolean>) => {
            state.loading = action.payload
        },
        setResults: (state, action: PayloadAction<Dataset[]>) => {
            state.results = action.payload
        },
        setError: (state, action: PayloadAction<string | null>) => {
            state.error = action.payload
        },
        expandDataset: (state, action: PayloadAction<string>) => {
            state.expandedDatasetId = state.expandedDatasetId === action.payload ? null : action.payload
        },
    },
})

export const {
    setQuery,
    setSelectedModel,
    setLoading,
    setResults,
    setError,
    expandDataset,
} = searchSlice.actions

export default searchSlice.reducer
