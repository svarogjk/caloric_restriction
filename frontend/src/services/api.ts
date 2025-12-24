import axios from 'axios'
import { Dataset } from '../store/searchSlice'

const API_BASE_URL = '/api'

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

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
}

export const searchDatasets = async (
    query: string,
    model: string,
    maxDatasets: number = 10,
    rankingMultiplier: number = 3,
    organism: string | null = null
): Promise<SurvivalAnalysisResponse> => {
    try {
        const response = await apiClient.post('/search', {
            query: query,
            model: model,
            max_datasets: maxDatasets,
            ranking_multiplier: rankingMultiplier,
            organism: organism,
            min_occurrence: 2,
        })
        return response.data
    } catch (error) {
        console.error('Error searching datasets:', error)
        throw error
    }
}

export const getDatasetDetails = async (datasetId: string): Promise<Dataset> => {
    try {
        const response = await apiClient.get<Dataset>(`/datasets/${datasetId}`)
        return response.data
    } catch (error) {
        console.error('Error fetching dataset details:', error)
        throw error
    }
}

export const downloadDataset = async (
    datasetId: string,
    format: 'csv' | 'json' = 'csv'
): Promise<Blob> => {
    try {
        const response = await apiClient.get(
            `/datasets/${datasetId}/download?format=${format}`,
            {
                responseType: 'blob',
            }
        )
        return response.data
    } catch (error) {
        console.error('Error downloading dataset:', error)
        throw error
    }
}

export const getAvailableModels = async (): Promise<string[]> => {
    try {
        const response = await apiClient.get<string[]>('/models')
        return response.data
    } catch (error) {
        console.error('Error fetching models:', error)
        throw error
    }
}
