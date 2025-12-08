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
    datasetCount: number
    rankingMultiplier: number
    results: AnalysisResult | null
    loading: boolean
    error: string | null
    expandedGeneId: string | null
    useAiGeneMapping: boolean
    geneMappingModel: string | null
}

const initialState: SearchState = {
    query: '',
    selectedModel: 'mistral',
    datasetCount: 10,
    rankingMultiplier: 3,
    results: null,
    loading: false,
    error: null,
    expandedGeneId: null,
    useAiGeneMapping: true,
    geneMappingModel: null,
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
        setDatasetCount: (state, action: PayloadAction<number>) => {
            state.datasetCount = action.payload
        },
        setRankingMultiplier: (state, action: PayloadAction<number>) => {
            state.rankingMultiplier = action.payload
        },
        setUseAiGeneMapping: (state, action: PayloadAction<boolean>) => {
            state.useAiGeneMapping = action.payload
        },
        setGeneMappingModel: (state, action: PayloadAction<string | null>) => {
            state.geneMappingModel = action.payload
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
    setDatasetCount,
    setRankingMultiplier,
    setUseAiGeneMapping,
    setGeneMappingModel,
    setLoading,
    setResults,
    setError,
    expandGene,
} = searchSlice.actions

export default searchSlice.reducer
