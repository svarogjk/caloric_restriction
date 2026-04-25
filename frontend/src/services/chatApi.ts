import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { getStoredToken, removeStoredToken } from './authApi'

const API_BASE_URL = '/api/chat'

const chatClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

chatClient.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        const token = getStoredToken()
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => Promise.reject(error)
)

chatClient.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
        if (error.response?.status === 401) {
            removeStoredToken()
            window.dispatchEvent(new CustomEvent('auth:unauthorized'))
        }
        return Promise.reject(error)
    }
)

// ==================== Types ====================

export interface CreateConversationResponse {
    conversationId: string
    title: string
    createdAt: string
}

export interface ConversationListItem {
    id: string
    title: string | null
    createdAt: string
    updatedAt: string
    contextType: string
}

export interface DatasetPreview {
    accession: string
    title: string
    summary: string
    sampleCount: number
    platforms: string[]
    organism: string
    hasSurvivalKeywords: boolean
}

export interface GeoPreview {
    totalDatasets: number
    datasetsWithSurvivalKeywords: number
    topDatasets: DatasetPreview[]
    platformCounts: Record<string, number>
    platformDiversity: 'low' | 'medium' | 'high'
    warnings: string[]
    searchQuery: string
}

export interface MessageResponse {
    messageId: string
    role: 'user' | 'assistant'
    content: string
    createdAt: string
    modelUsed?: string
    estimation?: {
        confidenceScore: number
        estimatedDatasets: number
        estimatedTimeSeconds: number
        canProceed: boolean
        suggestions: string[]
        improvedQuery?: string
        geoPreview?: GeoPreview
    }
    suggestedActions?: string[]
}

export interface ConversationResponse {
    id: string
    title: string | null
    createdAt: string
    updatedAt: string
    contextType: string
    messages: MessageResponse[]
}

export interface EstimateQueryResponse {
    confidenceScore: number
    estimatedDatasets: number
    estimatedTimeSeconds: number
    canProceed: boolean
    suggestions: string[]
    improvedQuery?: string
    geoPreview?: GeoPreview
    validation: {
        hasSurvivalKeywords: boolean
        hasCancerType: boolean
        hasOrganism: boolean
        hasGeneFocus: boolean
    }
}

// ==================== API Functions ====================

export const chatApi = {
    /**
     * Create a new conversation
     */
    async createConversation(title?: string): Promise<CreateConversationResponse> {
        const response = await chatClient.post('/conversations', {
            title,
            context_type: 'general',
        })
        return {
            conversationId: response.data.conversation_id,
            title: response.data.title,
            createdAt: response.data.created_at,
        }
    },

    /**
     * List all conversations
     */
    async listConversations(limit: number = 20, offset: number = 0): Promise<ConversationListItem[]> {
        const response = await chatClient.get('/conversations', {
            params: { limit, offset },
        })
        return response.data.map((conv: Record<string, unknown>) => ({
            id: conv.id,
            title: conv.title,
            createdAt: conv.created_at,
            updatedAt: conv.updated_at,
            contextType: conv.context_type,
        }))
    },

    /**
     * Get a conversation with all messages
     */
    async getConversation(conversationId: string): Promise<ConversationResponse> {
        const response = await chatClient.get(`/conversations/${conversationId}`)
        return {
            id: response.data.id,
            title: response.data.title,
            createdAt: response.data.created_at,
            updatedAt: response.data.updated_at,
            contextType: response.data.context_type,
            messages: response.data.messages.map((msg: Record<string, unknown>) => ({
                messageId: msg.message_id,
                role: msg.role,
                content: msg.content,
                createdAt: msg.created_at,
                modelUsed: msg.model_used,
            })),
        }
    },

    /**
     * Send a message and get AI response
     */
    async sendMessage(
        conversationId: string,
        content: string,
        model: string = 'mistral',
    ): Promise<MessageResponse> {
        const response = await chatClient.post(
            `/conversations/${conversationId}/messages`,
            {
                content,
                model,
                stream: false,
            }
        )

        const data = response.data
        return {
            messageId: data.message_id,
            role: data.role,
            content: data.content,
            createdAt: data.created_at,
            modelUsed: data.model_used,
            estimation: data.estimation ? {
                confidenceScore: data.estimation.confidence_score,
                estimatedDatasets: data.estimation.estimated_datasets,
                estimatedTimeSeconds: data.estimation.estimated_time_seconds,
                canProceed: data.estimation.can_proceed,
                suggestions: data.estimation.suggestions,
                improvedQuery: data.estimation.improved_query,
                geoPreview: data.estimation.geo_preview ? {
                    totalDatasets: data.estimation.geo_preview.total_datasets,
                    datasetsWithSurvivalKeywords: data.estimation.geo_preview.datasets_with_survival_keywords,
                    topDatasets: (data.estimation.geo_preview.top_datasets || []).map((ds: Record<string, unknown>) => ({
                        accession: ds.accession,
                        title: ds.title,
                        summary: ds.summary,
                        sampleCount: ds.sample_count,
                        platforms: ds.platforms,
                        organism: ds.organism,
                        hasSurvivalKeywords: ds.has_survival_keywords,
                    })),
                    platformCounts: data.estimation.geo_preview.platform_counts || {},
                    platformDiversity: data.estimation.geo_preview.platform_diversity,
                    warnings: data.estimation.geo_preview.warnings || [],
                    searchQuery: data.estimation.geo_preview.search_query,
                } : undefined,
            } : undefined,
            suggestedActions: data.suggested_actions,
        }
    },

    /**
     * Estimate query success likelihood
     */
    async estimateQuery(query: string): Promise<EstimateQueryResponse> {
        const response = await chatClient.post('/estimate', { query })
        const data = response.data
        return {
            confidenceScore: data.confidence_score,
            estimatedDatasets: data.estimated_datasets,
            estimatedTimeSeconds: data.estimated_time_seconds,
            canProceed: data.can_proceed,
            suggestions: data.suggestions,
            improvedQuery: data.improved_query,
            geoPreview: data.geo_preview ? {
                totalDatasets: data.geo_preview.total_datasets,
                datasetsWithSurvivalKeywords: data.geo_preview.datasets_with_survival_keywords,
                topDatasets: (data.geo_preview.top_datasets || []).map((ds: Record<string, unknown>) => ({
                    accession: ds.accession,
                    title: ds.title,
                    summary: ds.summary,
                    sampleCount: ds.sample_count,
                    platforms: ds.platforms,
                    organism: ds.organism,
                    hasSurvivalKeywords: ds.has_survival_keywords,
                })),
                platformCounts: data.geo_preview.platform_counts || {},
                platformDiversity: data.geo_preview.platform_diversity,
                warnings: data.geo_preview.warnings || [],
                searchQuery: data.geo_preview.search_query,
            } : undefined,
            validation: {
                hasSurvivalKeywords: data.validation?.has_survival_keywords || false,
                hasCancerType: data.validation?.has_cancer_type || false,
                hasOrganism: data.validation?.has_organism || false,
                hasGeneFocus: data.validation?.has_gene_focus || false,
            },
        }
    },

    /**
     * Delete a conversation
     */
    async deleteConversation(conversationId: string): Promise<void> {
        await chatClient.delete(`/conversations/${conversationId}`)
    },

}

// ==================== Streaming ====================

/**
 * Send a message and consume the SSE stream, calling callbacks for each event.
 * The token is passed explicitly so this function has no implicit dependencies.
 */
export async function sendMessageStream(
    conversationId: string,
    content: string,
    model: string,
    token: string | null,
    onToken: (token: string) => void,
    onComplete: (message: MessageResponse) => void,
    onError: (error: string) => void,
): Promise<void> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`

    const response = await fetch(`/api/chat/conversations/${conversationId}/messages?stream=true`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ content, model, stream: true }),
    })

    if (!response.ok) {
        onError(`HTTP ${response.status}`)
        return
    }

    if (!response.body) {
        onError('No response body')
        return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            const data = line.slice(6).trim()
            if (!data || data === '[DONE]') continue

            try {
                const parsed = JSON.parse(data) as Record<string, unknown>

                if (parsed['type'] === 'token' && parsed['content']) {
                    onToken(parsed['content'] as string)
                } else if (parsed['type'] === 'message_complete' && parsed['message']) {
                    const msg = parsed['message'] as {
                        message_id: string
                        role: 'user' | 'assistant'
                        content: string
                        created_at: string
                        model_used?: string
                        suggested_actions?: string[]
                    }
                    const completeMessage: MessageResponse = {
                        messageId: msg.message_id,
                        role: msg.role,
                        content: msg.content,
                        createdAt: msg.created_at,
                        modelUsed: msg.model_used,
                        suggestedActions: msg.suggested_actions,
                    }
                    onComplete(completeMessage)
                } else if (parsed['type'] === 'error') {
                    onError((parsed['message'] as string | undefined) ?? 'Stream error')
                }
            } catch {
                // skip unparseable lines
            }
        }
    }
}
