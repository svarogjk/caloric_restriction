import axios from 'axios'

const API_BASE_URL = '/api/chat'

const chatClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

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

    /**
     * Get available chat models
     */
    async getModels(): Promise<string[]> {
        const response = await chatClient.get('/models')
        return response.data
    },
}
