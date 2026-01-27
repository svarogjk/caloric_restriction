import React, { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState, AppDispatch } from '../../store/store'
import {
    fetchConversations,
    createConversation,
    sendMessage,
    loadConversation,
    setSelectedModel,
    clearEstimation,
} from '../../store/chatSlice'
import { setQuery } from '../../store/searchSlice'
import ConversationList from './ConversationList'
import MessageList from './MessageList'
import ChatInput from './ChatInput'
import QueryEstimation from './QueryEstimation'

interface ChatContainerProps {
    onRunAnalysis?: (query: string) => void
}

const ChatContainer: React.FC<ChatContainerProps> = ({ onRunAnalysis }) => {
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
    } = useSelector((state: RootState) => state.chat)

    // Fetch conversations on mount
    useEffect(() => {
        dispatch(fetchConversations())
    }, [dispatch])

    const handleNewConversation = async () => {
        await dispatch(createConversation(undefined))
    }

    const handleSelectConversation = (conversationId: string) => {
        dispatch(loadConversation(conversationId))
    }

    const handleSendMessage = async (content: string) => {
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

    const handleRunAnalysis = (query: string) => {
        // Update the search query in the search slice
        dispatch(setQuery(query))
        dispatch(clearEstimation())

        // Call the parent handler if provided
        if (onRunAnalysis) {
            onRunAnalysis(query)
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
                        AI Assistant
                    </h2>
                    <div className="flex items-center gap-4">
                        <select
                            value={selectedModel}
                            onChange={(e) => handleModelChange(e.target.value as 'mistral' | 'anthropic')}
                            className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="mistral">Mistral</option>
                            <option value="anthropic">Claude</option>
                        </select>
                    </div>
                </div>

                {/* Query Estimation Banner */}
                {currentEstimation && (
                    <QueryEstimation
                        estimation={currentEstimation}
                        onRunAnalysis={handleRunAnalysis}
                        onDismiss={() => dispatch(clearEstimation())}
                    />
                )}

                {/* Error Banner */}
                {error && (
                    <div className="mx-4 mt-2 p-3 bg-red-50 border border-red-200 rounded-lg">
                        <p className="text-sm text-red-700">{error}</p>
                    </div>
                )}

                {/* Messages */}
                <MessageList
                    messages={messages}
                    isLoading={isLoading}
                    className="flex-1 overflow-y-auto"
                />

                {/* Input */}
                <ChatInput
                    onSend={handleSendMessage}
                    disabled={isLoading}
                    placeholder="Ask about survival analysis, genes, or GEO datasets..."
                />
            </div>
        </div>
    )
}

export default ChatContainer
