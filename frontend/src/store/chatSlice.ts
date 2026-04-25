import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import { chatApi, sendMessageStream, ConversationListItem } from '../services/chatApi'
import { getStoredToken } from '../services/authApi'
import { streamAnalysis, SurvivalAnalysisResponse, listAnalysisResults, AnalysisHistoryItem } from '../services/api'

// ==================== Types ====================

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

export interface HeterogeneityStats {
    q_statistic?: number | null
    i_squared?: number | null
    p_heterogeneity?: number | null
    tau_squared?: number | null
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
    heterogeneity_stats?: HeterogeneityStats | null
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
    result_id?: string | null
}

export interface Message {
    id: string
    role: 'user' | 'assistant' | 'system'
    content: string
    createdAt: string
    modelUsed?: string
    estimation?: QueryEstimation
    suggestedActions?: string[]
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

export interface AnalysisProgress {
    stage: string
    message: string
    current?: number
    total?: number
}

export interface ChatState {
    conversations: ConversationListItem[]
    activeConversationId: string | null
    activeConversation: Conversation | null
    messages: Message[]
    isLoading: boolean
    error: string | null
    currentEstimation: QueryEstimation | null
    selectedModel: 'mistral' | 'anthropic'
    sidebarOpen: boolean
    // Search/Analysis settings
    datasetCount: number
    rankingMultiplier: number
    organism: string | null
    cancerGenesOnly: boolean
    geneFilterInput: string
    // Analysis state
    analysisResults: AnalysisResult | null
    analysisLoading: boolean
    analysisError: string | null
    analysisProgress: AnalysisProgress | null
    conversationsLastFetched: number | null
    // Streaming state
    streamingMessageId: string | null
    streamingContent: string
    isStreaming: boolean
    // Analysis history
    analysisHistory: AnalysisHistoryItem[]
    historyLoading: boolean
    // Save settings
    autoSave: boolean
    isSaving: boolean
}

const initialState: ChatState = {
    conversations: [],
    activeConversationId: null,
    activeConversation: null,
    messages: [],
    isLoading: false,
    error: null,
    currentEstimation: null,
    selectedModel: 'mistral',
    sidebarOpen: true,
    // Search/Analysis settings
    datasetCount: 10,
    rankingMultiplier: 3,
    organism: null,
    cancerGenesOnly: false,
    geneFilterInput: '',
    // Analysis state
    analysisResults: null,
    analysisLoading: false,
    analysisError: null,
    analysisProgress: null,
    conversationsLastFetched: null,
    // Streaming state
    streamingMessageId: null,
    streamingContent: '',
    isStreaming: false,
    // Analysis history
    analysisHistory: [],
    historyLoading: false,
    // Save settings
    autoSave: false,
    isSaving: false,
}

// ==================== Async Thunks ====================

const CONVERSATIONS_CACHE_TTL_MS = 30_000

export const fetchConversations = createAsyncThunk(
    'chat/fetchConversations',
    async (_, { rejectWithValue }) => {
        try {
            return await chatApi.listConversations()
        } catch (error) {
            return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch conversations')
        }
    },
    {
        condition: (_, { getState }): boolean => {
            const { conversationsLastFetched } = (getState() as { chat: ChatState }).chat
            if (conversationsLastFetched !== null && Date.now() - conversationsLastFetched < CONVERSATIONS_CACHE_TTL_MS) {
                return false
            }
            return true
        },
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
            const tempId = `temp-${Date.now()}`
            const userMessage: Message = {
                id: tempId,
                role: 'user',
                content,
                createdAt: new Date().toISOString(),
            }
            dispatch(addMessage(userMessage))

            // Get auth token (optional — guest users can still chat)
            const token = getStoredToken()

            // Start streaming
            dispatch(startStreaming(tempId))

            return await new Promise<import('../services/chatApi').MessageResponse>((resolve, reject) => {
                sendMessageStream(
                    conversationId,
                    content,
                    model,
                    token,
                    (token) => {
                        dispatch(appendStreamToken(token))
                    },
                    (message) => {
                        dispatch(finalizeStreaming())
                        resolve(message)
                    },
                    (errorMsg) => {
                        dispatch(finalizeStreaming())
                        reject(new Error(errorMsg))
                    },
                )
            }).catch((error: unknown) => {
                return rejectWithValue(error instanceof Error ? error.message : 'Failed to send message')
            })
        } catch (error) {
            dispatch(finalizeStreaming())
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

export const runAnalysis = createAsyncThunk(
    'chat/runAnalysis',
    async (
        { query }: { query: string },
        { getState, dispatch, rejectWithValue }
    ) => {
        const state = getState() as { chat: ChatState }
        const { selectedModel, datasetCount, rankingMultiplier, organism, cancerGenesOnly, geneFilterInput } = state.chat

        // Parse gene filter input: split by newlines and commas, trim, filter empty, uppercase
        const geneFilter: string[] | null = geneFilterInput.trim()
            ? geneFilterInput
                .split(/[\n,]+/)
                .map((g) => g.trim().toUpperCase())
                .filter((g) => g.length > 0)
            : null

        // Add a system message indicating analysis is starting
        const systemMessage: Message = {
            id: `analysis-start-${Date.now()}`,
            role: 'system',
            content: `Running survival analysis for: "${query}"${geneFilter ? ` (${geneFilter.length} candidate genes)` : ''}`,
            createdAt: new Date().toISOString(),
        }
        dispatch(addMessage(systemMessage))

        return new Promise<SurvivalAnalysisResponse>((resolve, reject) => {
            streamAnalysis(
                query,
                selectedModel,
                datasetCount,
                rankingMultiplier,
                organism,
                cancerGenesOnly,
                geneFilter,
                2,
                (progress) => {
                    dispatch(setAnalysisProgress({
                        stage: progress.stage,
                        message: progress.message,
                        current: progress.current ?? undefined,
                        total: progress.total ?? undefined,
                    }))
                },
                (result) => {
                    resolve(result)
                },
                (errorMessage) => {
                    reject(new Error(errorMessage))
                },
            )
        }).catch((error: unknown) => {
            return rejectWithValue(error instanceof Error ? error.message : 'Failed to run analysis')
        })
    }
)

export const saveAnalysisResult = createAsyncThunk(
    'chat/saveAnalysisResult',
    async (result: AnalysisResult, { rejectWithValue }) => {
        try {
            const token = getStoredToken()
            const response = await fetch('/api/results', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify(result),
            })
            if (!response.ok) throw new Error(`HTTP ${response.status}`)
            const data = await response.json() as { result_id: string }
            return data.result_id
        } catch (error) {
            return rejectWithValue(error instanceof Error ? error.message : 'Save failed')
        }
    }
)

export const fetchAnalysisHistory = createAsyncThunk(
    'chat/fetchAnalysisHistory',
    async (_, { rejectWithValue }) => {
        try {
            return await listAnalysisResults()
        } catch (error) {
            return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch analysis history')
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
        setSelectedModel: (state, action: PayloadAction<'mistral' | 'anthropic'>) => {
            state.selectedModel = action.payload
        },
        clearEstimation: (state) => {
            state.currentEstimation = null
        },
        clearError: (state) => {
            state.error = null
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
        setCancerGenesOnly: (state, action: PayloadAction<boolean>) => {
            state.cancerGenesOnly = action.payload
        },
        setGeneFilterInput: (state, action: PayloadAction<string>) => {
            state.geneFilterInput = action.payload
        },
        clearAnalysisResults: (state) => {
            state.analysisResults = null
            state.analysisError = null
            state.analysisProgress = null
        },
        setAnalysisProgress: (state, action: PayloadAction<AnalysisProgress | null>) => {
            state.analysisProgress = action.payload
        },
        startStreaming: (state, action: PayloadAction<string>) => {
            state.streamingMessageId = action.payload
            state.streamingContent = ''
            state.isStreaming = true
        },
        appendStreamToken: (state, action: PayloadAction<string>) => {
            state.streamingContent += action.payload
        },
        finalizeStreaming: (state) => {
            state.streamingMessageId = null
            state.streamingContent = ''
            state.isStreaming = false
        },
        setAutoSave: (state, action: PayloadAction<boolean>) => {
            state.autoSave = action.payload
        },
        setResultId: (state, action: PayloadAction<string>) => {
            if (state.analysisResults) {
                state.analysisResults.result_id = action.payload
            }
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
                state.conversationsLastFetched = Date.now()
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
                state.conversationsLastFetched = null  // invalidate: updatedAt changed server-side
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

        // Fetch analysis history
        builder
            .addCase(fetchAnalysisHistory.pending, (state) => {
                state.historyLoading = true
            })
            .addCase(fetchAnalysisHistory.fulfilled, (state, action) => {
                state.historyLoading = false
                state.analysisHistory = action.payload
            })
            .addCase(fetchAnalysisHistory.rejected, (state) => {
                state.historyLoading = false
            })

        // Run analysis
        builder
            .addCase(runAnalysis.pending, (state) => {
                state.analysisLoading = true
                state.analysisError = null
                state.analysisProgress = null
            })
            .addCase(runAnalysis.fulfilled, (state, action) => {
                state.analysisLoading = false
                state.analysisResults = action.payload as AnalysisResult
                state.analysisProgress = null
                state.currentEstimation = null
            })
            .addCase(runAnalysis.rejected, (state, action) => {
                state.analysisLoading = false
                state.analysisError = action.payload as string
                state.analysisProgress = null
            })

        // Save analysis result
        builder
            .addCase(saveAnalysisResult.pending, (state) => {
                state.isSaving = true
            })
            .addCase(saveAnalysisResult.fulfilled, (state, action) => {
                state.isSaving = false
                if (state.analysisResults) {
                    state.analysisResults.result_id = action.payload
                }
            })
            .addCase(saveAnalysisResult.rejected, (state) => {
                state.isSaving = false
            })
    },
})

export const {
    setActiveConversation,
    addMessage,
    setSelectedModel,
    clearEstimation,
    clearError,
    setDatasetCount,
    setRankingMultiplier,
    setOrganism,
    setCancerGenesOnly,
    setGeneFilterInput,
    clearAnalysisResults,
    setAnalysisProgress,
    startStreaming,
    appendStreamToken,
    finalizeStreaming,
    setAutoSave,
    setResultId,
} = chatSlice.actions

export default chatSlice.reducer
