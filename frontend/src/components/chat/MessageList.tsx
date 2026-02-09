import React, { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'
import { Message } from '../../store/chatSlice'

interface MessageListProps {
    messages: Message[]
    isLoading: boolean
    className?: string
    onRunAnalysis?: (query: string) => void
    onModifyQuery?: (query: string) => void
    onExampleClick?: (example: string) => void
}

const MessageList: React.FC<MessageListProps> = ({ messages, isLoading, className = '', onRunAnalysis, onModifyQuery, onExampleClick }) => {
    const messagesEndRef = useRef<HTMLDivElement>(null)

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    if (messages.length === 0 && !isLoading) {
        return (
            <div className={`${className} flex items-center justify-center`}>
                <div className="text-center px-4">
                    <div className="text-gray-400 mb-4">
                        <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                    </div>
                    <h3 className="text-lg font-medium text-gray-700 mb-2">
                        Start a conversation
                    </h3>
                    <p className="text-gray-500 text-sm max-w-md">
                        Ask me about survival analysis, gene expression, or how to query GEO datasets.
                        I can help you formulate better queries and interpret results.
                    </p>
                    <div className="mt-6 space-y-2">
                        <p className="text-xs text-gray-400">Try asking:</p>
                        <div className="flex flex-wrap justify-center gap-2">
                            {[
                                "What genes are associated with breast cancer survival?",
                                "How do I interpret a hazard ratio?",
                                "Find prognostic biomarkers in lung cancer",
                            ].map((example, i) => (
                                <button
                                    key={i}
                                    onClick={() => onExampleClick?.(example)}
                                    className="px-3 py-1.5 bg-gray-100 text-gray-600 text-xs rounded-full hover:bg-indigo-100 hover:text-indigo-700 transition-colors cursor-pointer"
                                >
                                    {example}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    // Track the last user message for context
    const getLastUserMessage = (index: number): string | undefined => {
        for (let i = index - 1; i >= 0; i--) {
            if (messages[i].role === 'user') {
                return messages[i].content
            }
        }
        return undefined
    }

    return (
        <div className={`${className} px-4 py-4`}>
            <div className="max-w-3xl mx-auto space-y-4">
                {messages.map((message, index) => (
                    <MessageBubble
                        key={message.id}
                        message={message}
                        onRunAnalysis={onRunAnalysis}
                        onModifyQuery={onModifyQuery}
                        previousUserMessage={message.role === 'assistant' ? getLastUserMessage(index) : undefined}
                    />
                ))}

                {isLoading && (
                    <div className="flex items-start gap-3">
                        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                            <span className="text-blue-600 text-sm font-medium">AI</span>
                        </div>
                        <div className="bg-gray-100 rounded-lg px-4 py-3">
                            <div className="flex items-center gap-1">
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                            </div>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>
        </div>
    )
}

export default MessageList
