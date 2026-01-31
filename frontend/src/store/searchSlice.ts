import { createSlice, PayloadAction } from '@reduxjs/toolkit'

export interface KMCurveData {
    times: number[]
    survival_probabilities: number[]
    ci_lower: number[] | null
    ci_upper: number[] | null
    n_samples: number
    n_events: number
}

export interface GeneDatasetResult {
    dataset_id: string
    dataset_title: string
    hazard_ratio: number
    hazard_ratio_ci_lower: number
    hazard_ratio_ci_upper: number
    cox_p_value: number
    log_rank_p_value: number
    risk_direction: 'high_risk' | 'low_risk'
    n_samples: number
    median_survival_high: number | null
    median_survival_low: number | null
    km_curve_high: KMCurveData | null
    km_curve_low: KMCurveData | null
}

export interface GeneSurvival {
    gene_id: string
    gene_symbol: string | null
    n_datasets: number
    avg_hazard_ratio: number
    avg_cox_p_value: number
    avg_log_rank_p_value: number
    predominant_risk: 'high_risk' | 'low_risk'
    risk_direction_consistency: number
    datasets: string[]
    per_dataset_results: GeneDatasetResult[] | null
}

export interface AnalysisResult {
    query: string
    n_datasets_analyzed: number
    n_datasets_with_survival: number
    common_genes: GeneSurvival[]
    processing_time: number
    timestamp: string
    ranking_quality_score?: number
    ranking_recommendations?: string
}

export interface QueryEstimation {
    confidenceScore: number
    estimatedDatasets: number
    estimatedTimeSeconds: number
    canProceed: boolean
    suggestions: string[]
    improvedQuery?: string
}

export interface Dataset {
    id: string
    title: string
    accession: string
}

export interface SearchState {
    query: string
    selectedModel: string
    datasetCount: number
    rankingMultiplier: number
    organism: string | null
    results: AnalysisResult | null
    loading: boolean
    error: string | null
    expandedGeneId: string | null
    // Estimation state
    estimation: QueryEstimation | null
    estimationLoading: boolean
}

const initialState: SearchState = {
    query: '',
    selectedModel: 'mistral',
    datasetCount: 10,
    rankingMultiplier: 3,
    organism: null,  // null means any organism
    results: null,
    loading: false,
    error: null,
    expandedGeneId: null,
    estimation: null,
    estimationLoading: false,
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
        setOrganism: (state, action: PayloadAction<string | null>) => {
            state.organism = action.payload
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
        setEstimation: (state, action: PayloadAction<QueryEstimation | null>) => {
            state.estimation = action.payload
        },
        setEstimationLoading: (state, action: PayloadAction<boolean>) => {
            state.estimationLoading = action.payload
        },
        clearEstimation: (state) => {
            state.estimation = null
            state.estimationLoading = false
        },
    },
})

export const {
    setQuery,
    setSelectedModel,
    setDatasetCount,
    setRankingMultiplier,
    setOrganism,
    setLoading,
    setResults,
    setError,
    expandGene,
    setEstimation,
    setEstimationLoading,
    clearEstimation,
} = searchSlice.actions

export default searchSlice.reducer
