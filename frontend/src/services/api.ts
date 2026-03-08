import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { getStoredToken, removeStoredToken } from './authApi'

const API_BASE_URL = '/api'

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

// Request interceptor: Add auth token to requests
apiClient.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        const token = getStoredToken()
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)

// Response interceptor: Handle 401 errors
apiClient.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
        if (error.response?.status === 401) {
            removeStoredToken()
            // Optionally redirect to login or dispatch logout action
            window.dispatchEvent(new CustomEvent('auth:unauthorized'))
        }
        return Promise.reject(error)
    }
)

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

export interface GeneSurvivalResponse {
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

export interface SurvivalAnalysisResponse {
    query: string
    n_datasets_analyzed: number
    n_datasets_with_survival: number
    common_genes: GeneSurvivalResponse[]
    processing_time: number
    timestamp: string
    result_id?: string | null
}

export interface AnalysisProgressEvent {
    stage: string
    message: string
    current?: number | null
    total?: number | null
}

export function streamAnalysis(
    query: string,
    model: string,
    maxDatasets: number = 10,
    rankingMultiplier: number = 3,
    organism: string | null = null,
    cancerGenesOnly: boolean = false,
    geneFilter: string[] | null = null,
    minOccurrence: number = 2,
    onProgress: (event: AnalysisProgressEvent) => void,
    onComplete: (result: SurvivalAnalysisResponse) => void,
    onError: (message: string) => void,
): EventSource {
    const params = new URLSearchParams({
        query,
        model,
        max_datasets: String(maxDatasets),
        ranking_multiplier: String(rankingMultiplier),
        min_occurrence: String(minOccurrence),
        cancer_genes_only: String(cancerGenesOnly),
    })
    if (organism) {
        params.set('organism', organism)
    }
    if (geneFilter && geneFilter.length > 0) {
        for (const gene of geneFilter) {
            params.append('gene_filter', gene)
        }
    }

    const es = new EventSource(`/api/search/stream?${params.toString()}`)

    es.onmessage = (event: MessageEvent) => {
        try {
            const data = JSON.parse(event.data as string) as {
                stage: string
                message?: string
                current?: number | null
                total?: number | null
                result?: SurvivalAnalysisResponse
            }
            if (data.stage === 'result') {
                es.close()
                onComplete(data.result!)
            } else if (data.stage === 'error') {
                es.close()
                onError(data.message ?? 'Unknown error')
            } else {
                onProgress({
                    stage: data.stage,
                    message: data.message ?? '',
                    current: data.current ?? undefined,
                    total: data.total ?? undefined,
                })
            }
        } catch (parseErr) {
            console.error('SSE parse error:', parseErr)
        }
    }

    es.onerror = () => {
        es.close()
        onError('Connection lost during analysis')
    }

    return es
}

export async function getAnalysisResult(resultId: string): Promise<SurvivalAnalysisResponse> {
    const response = await axios.get<SurvivalAnalysisResponse>(`/api/results/${resultId}`)
    return response.data
}

export async function listAnalysisResults(limit = 20, offset = 0): Promise<AnalysisHistoryItem[]> {
    const token = getStoredToken()
    const response = await axios.get<AnalysisHistoryItem[]>('/api/results', {
        params: { limit, offset },
        headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    return response.data
}

export interface AnalysisHistoryItem {
    result_id: string
    query: string
    n_datasets_analyzed: number
    n_datasets_with_survival: number
    n_genes_found: number
    processing_time_seconds: number | null
    created_at: string
}

export interface GeneComparisonItem {
    gene_symbol: string
    hr_a: number
    hr_b: number
    p_value_a: number
    p_value_b: number
    n_datasets_a: number
    n_datasets_b: number
    direction_agrees: boolean
}

export interface CompareResponse {
    query_a: string
    query_b: string
    shared_genes: GeneComparisonItem[]
    unique_to_a: string[]
    unique_to_b: string[]
    n_shared: number
    n_unique_a: number
    n_unique_b: number
    direction_agreement_pct: number | null
    spearman_r: number | null
}

export async function compareAnalyses(resultIdA: string, resultIdB: string): Promise<CompareResponse> {
    const response = await apiClient.post<CompareResponse>('/compare', {
        result_id_a: resultIdA,
        result_id_b: resultIdB,
    })
    return response.data
}

export const searchDatasets = async (
    query: string,
    model: string,
    maxDatasets: number = 10,
    rankingMultiplier: number = 3,
    organism: string | null = null,
    cancerGenesOnly: boolean = false,
    geneFilter: string[] | null = null,
): Promise<SurvivalAnalysisResponse> => {
    try {
        const response = await apiClient.post('/search', {
            query: query,
            model: model,
            max_datasets: maxDatasets,
            ranking_multiplier: rankingMultiplier,
            organism: organism,
            min_occurrence: 2,
            cancer_genes_only: cancerGenesOnly,
            gene_filter: geneFilter,
        })
        return response.data
    } catch (error) {
        console.error('Error searching datasets:', error)
        throw error
    }
}

