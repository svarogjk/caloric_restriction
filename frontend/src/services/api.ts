import axios from 'axios'
import { Dataset } from '../store/searchSlice'

const API_BASE_URL = '/api'

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

export const searchDatasets = async (
    query: string,
    model: string,
    maxDatasets: number = 10,
    rankingMultiplier: number = 3,
    useAiGeneMapping: boolean = true,
    geneMappingModel?: string
): Promise<any> => {
    try {
        const response = await apiClient.post('/search', {
            query: query,
            model: model,
            max_datasets: maxDatasets,
            ranking_multiplier: rankingMultiplier,
            organism: 'Mus musculus',
            min_occurrence: 2,
            use_ai_gene_mapping: useAiGeneMapping,
            gene_mapping_model: geneMappingModel || null
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
