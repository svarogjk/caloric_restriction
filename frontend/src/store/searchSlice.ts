import { createSlice, PayloadAction } from '@reduxjs/toolkit'

export interface GeneOccurrence {
    gene_id: string
    n_datasets: number
    avg_log_fc: number
    direction_consistency: number
    datasets: string[]
}

export interface AnalysisResult {
    query: string
    n_datasets_analyzed: number
    n_datasets_with_degs: number
    common_genes: GeneOccurrence[]
    processing_time: number
    timestamp: string
}

export interface SearchState {
    query: string
    selectedModel: string
    results: AnalysisResult | null
    loading: boolean
    error: string | null
    expandedGeneId: string | null
}

const initialState: SearchState = {
    query: '',
    selectedModel: 'mistral',
    results: null,
    loading: false,
    error: null,
    expandedGeneId: null,
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
        setResults: (state, action: PayloadAction<AnalysisResult>) => {
            state.results = action.payload
        },
        setError: (state, action: PayloadAction<string | null>) => {
            state.error = action.payload
        },
        expandGene: (state, action: PayloadAction<string>) => {
            state.expandedGeneId = state.expandedGeneId === action.payload ? null : action.payload
        },
    },
})

export const {
    setQuery,
    setSelectedModel,
    setLoading,
    setResults,
    setError,
    expandGene,
} = searchSlice.actions

export default searchSlice.reducer
