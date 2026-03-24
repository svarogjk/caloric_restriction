import React, { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState, AppDispatch } from '../../store/store'
import {
    fetchConversations,
    createConversation,
    sendMessage,
    loadConversation,
    setSelectedModel,
    clearEstimation,
    setDatasetCount,
    setRankingMultiplier,
    setOrganism,
    setCancerGenesOnly,
    setGeneFilterInput,
    runAnalysis,
    saveAnalysisResult,
    clearAnalysisResults,
} from '../../store/chatSlice'
import ConversationList from './ConversationList'
import MessageList from './MessageList'
import ChatInput from './ChatInput'
import QueryEstimation from './QueryEstimation'
import AnalysisResultsDisplay from './AnalysisResultsDisplay'
import AnalysisProgress from './AnalysisProgress'

const ChatContainer: React.FC = () => {
    const dispatch = useDispatch<AppDispatch>()
    const {
        conversations,
        activeConversationId,
        messages,
        isLoading,
        error,
        currentEstimation,
        selectedModel,
        sidebarOpen,
        datasetCount,
        rankingMultiplier,
        organism,
        cancerGenesOnly,
        geneFilterInput,
        analysisResults,
        analysisLoading,
        analysisError,
        analysisProgress,
        isStreaming,
        streamingContent,
        autoSave,
    } = useSelector((state: RootState) => state.chat)

    const [settingsOpen, setSettingsOpen] = useState(false)
    const [inputValue, setInputValue] = useState('')

    // Fetch conversations on mount
    useEffect(() => {
        dispatch(fetchConversations())
    }, [dispatch])

    const handleNewConversation = async () => {
        dispatch(clearAnalysisResults())
        await dispatch(createConversation(undefined))
    }

    const handleSelectConversation = (conversationId: string) => {
        dispatch(clearAnalysisResults())
        dispatch(loadConversation(conversationId))
    }

    const handleSendMessage = async (content: string) => {
        setInputValue('') // Clear input after sending
        if (!activeConversationId) {
            // Create a new conversation first
            const result = await dispatch(createConversation(undefined))
            if (createConversation.fulfilled.match(result)) {
                await dispatch(sendMessage({
                    conversationId: result.payload.conversationId,
                    content,
                    model: selectedModel,
                }))
            }
        } else {
            await dispatch(sendMessage({
                conversationId: activeConversationId,
                content,
                model: selectedModel,
            }))
        }
    }

    const handleModifyQuery = (query: string) => {
        setInputValue(query)
    }

    const handleRunAnalysis = async (query: string) => {
        dispatch(clearEstimation())
        const resultAction = await dispatch(runAnalysis({ query }))
        if (autoSave && runAnalysis.fulfilled.match(resultAction)) {
            dispatch(saveAnalysisResult(resultAction.payload))
        }
    }

    const handleModelChange = (model: 'mistral' | 'anthropic') => {
        dispatch(setSelectedModel(model))
    }

    return (
        <div className="flex h-full bg-gray-100">
            {/* Sidebar */}
            {sidebarOpen && (
                <ConversationList
                    conversations={conversations}
                    activeConversationId={activeConversationId}
                    onSelectConversation={handleSelectConversation}
                    onNewConversation={handleNewConversation}
                    className="w-64 flex-shrink-0"
                />
            )}

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col bg-white">
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
                    <h2 className="text-lg font-semibold text-gray-800">
                        GEO Survival Analysis
                    </h2>
                    <div className="flex items-center gap-3">
                        {/* Settings Toggle */}
                        <button
                            onClick={() => setSettingsOpen(!settingsOpen)}
                            className={`p-2 rounded-md transition-colors ${
                                settingsOpen
                                    ? 'bg-indigo-100 text-indigo-600'
                                    : 'text-gray-500 hover:bg-gray-100'
                            }`}
                            title="Analysis Settings"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                        </button>

                        {/* Model Selector */}
                        <select
                            value={selectedModel}
                            onChange={(e) => handleModelChange(e.target.value as 'mistral' | 'anthropic')}
                            className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        >
                            <option value="mistral">Mistral</option>
                            <option value="anthropic">Claude</option>
                        </select>
                    </div>
                </div>

                {/* Settings Panel */}
                {settingsOpen && (
                    <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                        <div className="flex flex-wrap items-center gap-4">
                            {/* Dataset Count */}
                            <div className="flex items-center gap-2">
                                <label className="text-sm font-medium text-gray-700">
                                    Datasets:
                                </label>
                                <select
                                    value={datasetCount}
                                    onChange={(e) => dispatch(setDatasetCount(Number(e.target.value)))}
                                    className="px-2 py-1 text-sm border border-gray-300 rounded-md bg-white"
                                >
                                    <option value={10}>10</option>
                                    <option value={20}>20</option>
                                    <option value={50}>50</option>
                                    <option value={100}>100</option>
                                    <option value={500}>500</option>
                                    <option value={1000}>1000</option>
                                </select>
                            </div>

                            {/* Ranking Multiplier */}
                            <div className="flex items-center gap-2">
                                <label className="text-sm font-medium text-gray-700">
                                    Ranking:
                                </label>
                                <input
                                    type="range"
                                    min={1}
                                    max={10}
                                    value={rankingMultiplier}
                                    onChange={(e) => dispatch(setRankingMultiplier(Number(e.target.value)))}
                                    className="w-20"
                                />
                                <span className="text-sm text-gray-600 w-8">{rankingMultiplier}x</span>
                            </div>

                            {/* Organism */}
                            <div className="flex items-center gap-2">
                                <label className="text-sm font-medium text-gray-700">
                                    Organism:
                                </label>
                                <select
                                    value={organism || ''}
                                    onChange={(e) => dispatch(setOrganism(e.target.value || null))}
                                    className="px-2 py-1 text-sm border border-gray-300 rounded-md bg-white"
                                >
                                    <option value="">Any</option>
                                    <option value="Homo sapiens">Human</option>
                                    <option value="Mus musculus">Mouse</option>
                                </select>
                            </div>

                            {/* Cancer Genes Only */}
                            <div className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    id="chat-cancer-genes-only"
                                    checked={cancerGenesOnly}
                                    onChange={(e) => dispatch(setCancerGenesOnly(e.target.checked))}
                                    className="w-4 h-4 text-purple-600 border-gray-300 rounded cursor-pointer"
                                />
                                <label htmlFor="chat-cancer-genes-only" className="text-sm font-medium text-gray-700 cursor-pointer">
                                    Cancer genes only (~600)
                                </label>
                            </div>
                        </div>

                        {/* Candidate Genes Batch Mode */}
                        <div className="mt-3">
                            <label htmlFor="chat-gene-filter" className="text-sm font-medium text-gray-700 block mb-1">
                                Candidate Genes (optional batch mode)
                            </label>
                            <textarea
                                id="chat-gene-filter"
                                value={geneFilterInput}
                                onChange={(e) => dispatch(setGeneFilterInput(e.target.value))}
                                placeholder={"TP53\nBRCA1\nMYC\nEGFR\nPIK3CA\n(one per line or comma-separated)"}
                                rows={4}
                                className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md bg-white resize-y font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            />
                            {geneFilterInput.trim() && (
                                <p className="text-xs text-indigo-600 mt-1">
                                    {geneFilterInput.split(/[\n,]+/).map((g) => g.trim()).filter((g) => g.length > 0).length} genes selected — analysis restricted to these candidates
                                </p>
                            )}
                        </div>

                        <p className="text-xs text-gray-500 mt-2">
                            These settings affect survival analysis when running queries.
                        </p>
                    </div>
                )}

                {/* Query Estimation Banner */}
                {currentEstimation && (
                    <QueryEstimation
                        estimation={currentEstimation}
                        originalQuery={[...messages].reverse().find(m => m.role === 'user')?.content ?? ''}
                        onRunAnalysis={handleRunAnalysis}
                        onDismiss={() => dispatch(clearEstimation())}
                    />
                )}

                {/* Error Banner */}
                {(error || analysisError) && (
                    <div className="mx-4 mt-2 p-3 bg-red-50 border border-red-200 rounded-lg">
                        <p className="text-sm text-red-700">{error || analysisError}</p>
                    </div>
                )}

                {/* Analysis Progress (SSE streaming) */}
                {analysisLoading && (
                    analysisProgress ? (
                        <AnalysisProgress progress={analysisProgress} />
                    ) : (
                        <div className="mx-4 mt-2 p-4 bg-indigo-50 border border-indigo-200 rounded-lg">
                            <div className="flex items-center gap-3">
                                <svg className="animate-spin h-5 w-5 text-indigo-600" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                <div>
                                    <p className="text-sm font-medium text-indigo-800">Starting analysis...</p>
                                    <p className="text-xs text-indigo-600">Connecting to analysis stream.</p>
                                </div>
                            </div>
                        </div>
                    )
                )}

                {/* Analysis Results */}
                {analysisResults && !analysisLoading && (
                    <div className="mx-4 mt-2">
                        <AnalysisResultsDisplay
                            results={analysisResults}
                            onClose={() => dispatch(clearAnalysisResults())}
                        />
                    </div>
                )}

                {/* Messages */}
                <MessageList
                    messages={messages}
                    isLoading={isLoading}
                    isStreaming={isStreaming}
                    streamingContent={streamingContent}
                    onRunAnalysis={handleRunAnalysis}
                    onModifyQuery={handleModifyQuery}
                    onExampleClick={handleSendMessage}
                    className="flex-1 overflow-y-auto"
                />

                {/* Input */}
                <ChatInput
                    onSend={handleSendMessage}
                    disabled={isLoading || isStreaming || analysisLoading}
                    placeholder="Ask about survival analysis, genes, or GEO datasets..."
                    value={inputValue}
                    onChange={setInputValue}
                />
            </div>
        </div>
    )
}

export default ChatContainer
