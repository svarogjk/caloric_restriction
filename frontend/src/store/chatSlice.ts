import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import { chatApi, sendMessageStream, ConversationListItem, UserSettings, PatientContextPayload, ResearchContextPayload, ConsoleAction } from '../services/chatApi'
import { getStoredToken } from '../services/authApi'
import {
    streamAnalysis, listAnalysisResults,
    type SurvivalAnalysisResponse, type SurvivalAnalysisResponse as AnalysisResult,
    type AnalysisHistoryItem,
} from '../services/api'

// ==================== Types ====================

// Analysis result types live in services/api.ts — the shape comes off the wire,
// so there is one definition and these are aliases for the names the UI uses.
export type {
    KMCurveData, GeneDatasetResult, TreatmentArmResult, HeterogeneityStats,
    AnalysisDiagnostics,
    GeneSurvivalResponse as GeneSurvival,
    SurvivalAnalysisResponse as AnalysisResult,
} from '../services/api'

export interface Message {
    id: string
    role: 'user' | 'assistant' | 'system'
    content: string
    createdAt: string
    modelUsed?: string
    estimation?: QueryEstimation
    suggestedActions?: string[]
    domainScore?: number
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
    selectedModel: 'mistral' | 'mistral-large' | 'anthropic'
    sidebarOpen: boolean
    // Search/Analysis settings
    datasetCount: number
    rankingMultiplier: number
    organism: string | null
    cancerGenesOnly: boolean
    geneFilterInput: string
    hazardRatioUpper: number
    hazardRatioLower: number
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
    // Patient personalization (carried from the landing into the analysis)
    personalizeEnabled: boolean
    patientExpression: string
}

const initialState: ChatState = {
    conversations: [],
    activeConversationId: null,
    activeConversation: null,
    messages: [],
    isLoading: false,
    error: null,
    currentEstimation: null,
    selectedModel: 'mistral-large',
    sidebarOpen: true,
    // Search/Analysis settings
    datasetCount: 20,
    rankingMultiplier: 10,
    organism: 'Homo sapiens',
    cancerGenesOnly: true,
    geneFilterInput: '',
    hazardRatioUpper: 1.2,
    hazardRatioLower: 0.8,
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
    // Patient personalization
    personalizeEnabled: false,
    patientExpression: '',
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
        { conversationId, content, model, patientContext, researchContext }: {
            conversationId: string
            content: string
            model: string
            /** De-identified clinical console chart snapshot — omit outside the console. */
            patientContext?: PatientContextPayload | null
            /** Session state with no patient involved — analysis in flight, last result. */
            researchContext?: ResearchContextPayload | null
        },
        { dispatch, getState, rejectWithValue }
    ) => {
        try {
            // Read current user settings from Redux state
            const state = (getState() as { chat: ChatState }).chat
            const {
                organism, cancerGenesOnly, datasetCount, rankingMultiplier, geneFilterInput,
                hazardRatioUpper, hazardRatioLower,
            } = state
            const candidateGenes: string[] | null = geneFilterInput.trim()
                ? geneFilterInput.split(/[\n,]+/).map((g) => g.trim().toUpperCase()).filter((g) => g.length > 0)
                : null
            const userSettings: UserSettings = {
                organism,
                cancer_genes_only: cancerGenesOnly,
                num_datasets: datasetCount,
                ranking_multiplier: rankingMultiplier,
                candidate_genes: candidateGenes,
                hazard_ratio_upper: hazardRatioUpper,
                hazard_ratio_lower: hazardRatioLower,
            }

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

            // Console action intents arrive via a separate SSE event, ahead of
            // message_complete — captured here and merged into the resolved
            // MessageResponse so callers can read them off the thunk's payload.
            let capturedActions: ConsoleAction[] = []

            return await new Promise<import('../services/chatApi').MessageResponse>((resolve, reject) => {
                sendMessageStream(
                    conversationId,
                    content,
                    model,
                    token,
                    userSettings,
                    (token) => {
                        dispatch(appendStreamToken(token))
                    },
                    (message) => {
                        dispatch(finalizeStreaming())
                        resolve({ ...message, actions: capturedActions })
                    },
                    (errorMsg) => {
                        dispatch(finalizeStreaming())
                        reject(new Error(errorMsg))
                    },
                    patientContext ?? null,
                    (actions) => { capturedActions = actions },
                    researchContext ?? null,
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

/**
 * The EventSource behind the in-flight analysis, if any.
 *
 * `streamAnalysis` closes itself on result/error, but nothing closed it when the
 * component that started it went away — so navigating off the console mid-run
 * left an open SSE connection and a thunk resolving into nothing.
 */
let activeAnalysisStream: EventSource | null = null

/** Close an in-flight analysis stream. The server-side run continues; this only
 *  stops the browser listening. Safe to call when nothing is running. */
export function abortActiveAnalysis(): void {
    activeAnalysisStream?.close()
    activeAnalysisStream = null
}

export const runAnalysis = createAsyncThunk(
    'chat/runAnalysis',
    async (
        { query, geneFilter: geneFilterOverride }: {
            query: string
            /** Restrict the run to these genes. The agent passes them for a
             *  question about specific genes; this also flips the response's
             *  diagnostics.gene_filter_applied, which is what decides whether a
             *  p-value may be presented as FDR-adjusted. */
            geneFilter?: string[]
        },
        { getState, dispatch, rejectWithValue }
    ) => {
        const state = getState() as { chat: ChatState }
        const {
            selectedModel, datasetCount, rankingMultiplier, organism, cancerGenesOnly, geneFilterInput,
            hazardRatioUpper, hazardRatioLower,
        } = state.chat

        // An explicit override (from the agent) wins over the settings-panel list.
        const geneFilter: string[] | null = geneFilterOverride?.length
            ? geneFilterOverride.map((g) => g.trim().toUpperCase()).filter((g) => g.length > 0)
            : geneFilterInput.trim()
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
            activeAnalysisStream?.close()
            activeAnalysisStream = streamAnalysis(
                query,
                selectedModel,
                datasetCount,
                rankingMultiplier,
                organism,
                cancerGenesOnly,
                geneFilter,
                2,
                hazardRatioUpper,
                hazardRatioLower,
                (progress) => {
                    dispatch(setAnalysisProgress({
                        stage: progress.stage,
                        message: progress.message,
                        current: progress.current ?? undefined,
                        total: progress.total ?? undefined,
                    }))
                },
                (result) => {
                    activeAnalysisStream = null
                    resolve(result)
                },
                (errorMessage) => {
                    activeAnalysisStream = null
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
        setSelectedModel: (state, action: PayloadAction<'mistral' | 'mistral-large' | 'anthropic'>) => {
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
        setHazardRatioUpper: (state, action: PayloadAction<number>) => {
            state.hazardRatioUpper = action.payload
        },
        setHazardRatioLower: (state, action: PayloadAction<number>) => {
            state.hazardRatioLower = action.payload
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
        setPersonalizeEnabled: (state, action: PayloadAction<boolean>) => {
            state.personalizeEnabled = action.payload
            // Personalization needs a saved result to score against, so opting
            // in auto-enables saving the analysis.
            if (action.payload) state.autoSave = true
        },
        setPatientExpression: (state, action: PayloadAction<string>) => {
            state.patientExpression = action.payload
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
                    domainScore: action.payload.domainScore,
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
                state.analysisResults = action.payload
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
    setHazardRatioUpper,
    setHazardRatioLower,
    clearAnalysisResults,
    setAnalysisProgress,
    startStreaming,
    appendStreamToken,
    finalizeStreaming,
    setAutoSave,
    setResultId,
    setPersonalizeEnabled,
    setPatientExpression,
} = chatSlice.actions

export default chatSlice.reducer
