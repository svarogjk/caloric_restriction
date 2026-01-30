import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import { chatApi, ConversationListItem } from '../services/chatApi'

// ==================== Types ====================

export interface Message {
    id: string
    role: 'user' | 'assistant' | 'system'
    content: string
    createdAt: string
    modelUsed?: string
    estimation?: QueryEstimation
    suggestedActions?: string[]
    isStreaming?: boolean
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

export interface QueryEstimation {
    confidenceScore: number
    estimatedDatasets: number
    estimatedTimeSeconds: number
    canProceed: boolean
    suggestions: string[]
    improvedQuery?: string
    geoPreview?: GeoPreview
}

export interface Conversation {
    id: string
    title: string | null
    createdAt: string
    updatedAt: string
    contextType: string
    messages: Message[]
}

export interface ChatState {
    conversations: ConversationListItem[]
    activeConversationId: string | null
    activeConversation: Conversation | null
    messages: Message[]
    isLoading: boolean
    isStreaming: boolean
    error: string | null
    currentEstimation: QueryEstimation | null
    selectedModel: 'mistral' | 'anthropic'
    sidebarOpen: boolean
}

const initialState: ChatState = {
    conversations: [],
    activeConversationId: null,
    activeConversation: null,
    messages: [],
    isLoading: false,
    isStreaming: false,
    error: null,
    currentEstimation: null,
    selectedModel: 'mistral',
    sidebarOpen: true,
}

// ==================== Async Thunks ====================

export const fetchConversations = createAsyncThunk(
    'chat/fetchConversations',
    async (_, { rejectWithValue }) => {
        try {
            return await chatApi.listConversations()
        } catch (error) {
            return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch conversations')
        }
    }
)

export const createConversation = createAsyncThunk(
    'chat/createConversation',
    async (title: string | undefined, { rejectWithValue }) => {
        try {
            return await chatApi.createConversation(title)
        } catch (error) {
            return rejectWithValue(error instanceof Error ? error.message : 'Failed to create conversation')
        }
    }
)

export const loadConversation = createAsyncThunk(
    'chat/loadConversation',
    async (conversationId: string, { rejectWithValue }) => {
        try {
            return await chatApi.getConversation(conversationId)
        } catch (error) {
            return rejectWithValue(error instanceof Error ? error.message : 'Failed to load conversation')
        }
    }
)

export const sendMessage = createAsyncThunk(
    'chat/sendMessage',
    async (
        { conversationId, content, model }: {
            conversationId: string
            content: string
            model: string
        },
        { dispatch, rejectWithValue }
    ) => {
        try {
            // Add user message immediately (optimistic update)
            const userMessage: Message = {
                id: `temp-${Date.now()}`,
                role: 'user',
                content,
                createdAt: new Date().toISOString(),
            }
            dispatch(addMessage(userMessage))

            // Send to API
            const response = await chatApi.sendMessage(conversationId, content, model)

            return response
        } catch (error) {
            return rejectWithValue(error instanceof Error ? error.message : 'Failed to send message')
        }
    }
)

export const estimateQuery = createAsyncThunk(
    'chat/estimateQuery',
    async (query: string, { rejectWithValue }) => {
        try {
            return await chatApi.estimateQuery(query)
        } catch (error) {
            return rejectWithValue(error instanceof Error ? error.message : 'Failed to estimate query')
        }
    }
)

export const deleteConversation = createAsyncThunk(
    'chat/deleteConversation',
    async (conversationId: string, { rejectWithValue }) => {
        try {
            await chatApi.deleteConversation(conversationId)
            return conversationId
        } catch (error) {
            return rejectWithValue(error instanceof Error ? error.message : 'Failed to delete conversation')
        }
    }
)

// ==================== Slice ====================

const chatSlice = createSlice({
    name: 'chat',
    initialState,
    reducers: {
        setActiveConversation: (state, action: PayloadAction<string | null>) => {
            state.activeConversationId = action.payload
            if (!action.payload) {
                state.messages = []
                state.activeConversation = null
            }
        },
        addMessage: (state, action: PayloadAction<Message>) => {
            state.messages.push(action.payload)
        },
        updateStreamingMessage: (state, action: PayloadAction<string>) => {
            const lastMessage = state.messages[state.messages.length - 1]
            if (lastMessage && lastMessage.isStreaming) {
                lastMessage.content += action.payload
            }
        },
        completeStreamingMessage: (state) => {
            const lastMessage = state.messages[state.messages.length - 1]
            if (lastMessage && lastMessage.isStreaming) {
                lastMessage.isStreaming = false
            }
        },
        setStreaming: (state, action: PayloadAction<boolean>) => {
            state.isStreaming = action.payload
        },
        setSelectedModel: (state, action: PayloadAction<'mistral' | 'anthropic'>) => {
            state.selectedModel = action.payload
        },
        clearEstimation: (state) => {
            state.currentEstimation = null
        },
        clearError: (state) => {
            state.error = null
        },
        toggleSidebar: (state) => {
            state.sidebarOpen = !state.sidebarOpen
        },
        clearMessages: (state) => {
            state.messages = []
        },
    },
    extraReducers: (builder) => {
        // Fetch conversations
        builder
            .addCase(fetchConversations.pending, (state) => {
                state.isLoading = true
            })
            .addCase(fetchConversations.fulfilled, (state, action) => {
                state.isLoading = false
                state.conversations = action.payload
            })
            .addCase(fetchConversations.rejected, (state, action) => {
                state.isLoading = false
                state.error = action.payload as string
            })

        // Create conversation
        builder
            .addCase(createConversation.fulfilled, (state, action) => {
                const newConv: ConversationListItem = {
                    id: action.payload.conversationId,
                    title: action.payload.title,
                    createdAt: action.payload.createdAt,
                    updatedAt: action.payload.createdAt,
                    contextType: 'general',
                }
                state.conversations.unshift(newConv)
                state.activeConversationId = action.payload.conversationId
                state.messages = []
            })
            .addCase(createConversation.rejected, (state, action) => {
                state.error = action.payload as string
            })

        // Load conversation
        builder
            .addCase(loadConversation.pending, (state) => {
                state.isLoading = true
            })
            .addCase(loadConversation.fulfilled, (state, action) => {
                state.isLoading = false
                state.activeConversationId = action.payload.id
                state.activeConversation = {
                    id: action.payload.id,
                    title: action.payload.title,
                    createdAt: action.payload.createdAt,
                    updatedAt: action.payload.updatedAt,
                    contextType: action.payload.contextType,
                    messages: action.payload.messages.map((msg) => ({
                        id: msg.messageId,
                        role: msg.role as 'user' | 'assistant' | 'system',
                        content: msg.content,
                        createdAt: msg.createdAt,
                        modelUsed: msg.modelUsed || undefined,
                    })),
                }
                state.messages = state.activeConversation.messages
            })
            .addCase(loadConversation.rejected, (state, action) => {
                state.isLoading = false
                state.error = action.payload as string
            })

        // Send message
        builder
            .addCase(sendMessage.pending, (state) => {
                state.isLoading = true
                state.error = null
            })
            .addCase(sendMessage.fulfilled, (state, action) => {
                state.isLoading = false
                // Add assistant message
                const assistantMessage: Message = {
                    id: action.payload.messageId,
                    role: 'assistant',
                    content: action.payload.content,
                    createdAt: action.payload.createdAt,
                    modelUsed: action.payload.modelUsed || undefined,
                    suggestedActions: action.payload.suggestedActions,
                }

                // Handle estimation
                if (action.payload.estimation) {
                    const est = action.payload.estimation
                    assistantMessage.estimation = {
                        confidenceScore: est.confidenceScore,
                        estimatedDatasets: est.estimatedDatasets,
                        estimatedTimeSeconds: est.estimatedTimeSeconds,
                        canProceed: est.canProceed,
                        suggestions: est.suggestions,
                        improvedQuery: est.improvedQuery,
                        geoPreview: est.geoPreview,
                    }
                    state.currentEstimation = assistantMessage.estimation
                }

                state.messages.push(assistantMessage)
            })
            .addCase(sendMessage.rejected, (state, action) => {
                state.isLoading = false
                state.error = action.payload as string
            })

        // Estimate query
        builder
            .addCase(estimateQuery.fulfilled, (state, action) => {
                state.currentEstimation = {
                    confidenceScore: action.payload.confidenceScore,
                    estimatedDatasets: action.payload.estimatedDatasets,
                    estimatedTimeSeconds: action.payload.estimatedTimeSeconds,
                    canProceed: action.payload.canProceed,
                    suggestions: action.payload.suggestions,
                    improvedQuery: action.payload.improvedQuery,
                    geoPreview: action.payload.geoPreview,
                }
            })

        // Delete conversation
        builder
            .addCase(deleteConversation.fulfilled, (state, action) => {
                state.conversations = state.conversations.filter(
                    (conv) => conv.id !== action.payload
                )
                if (state.activeConversationId === action.payload) {
                    state.activeConversationId = null
                    state.messages = []
                    state.activeConversation = null
                }
            })
    },
})

export const {
    setActiveConversation,
    addMessage,
    updateStreamingMessage,
    completeStreamingMessage,
    setStreaming,
    setSelectedModel,
    clearEstimation,
    clearError,
    toggleSidebar,
    clearMessages,
} = chatSlice.actions

export default chatSlice.reducer
