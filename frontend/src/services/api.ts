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
    model: string
): Promise<any> => {
    try {
        const response = await apiClient.post('/search', {
            query: query,
            max_datasets: 10,
            organism: 'Mus musculus',
            min_occurrence: 1
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
