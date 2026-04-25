import React, { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'
import { Message } from '../../store/chatSlice'

interface MessageListProps {
    messages: Message[]
    isLoading: boolean
    isStreaming?: boolean
    streamingContent?: string
    className?: string
    onRunAnalysis?: (query: string) => void
    onModifyQuery?: (query: string) => void
    onExampleClick?: (example: string) => void
}

const MessageList: React.FC<MessageListProps> = ({ messages, isLoading, isStreaming = false, streamingContent = '', className = '', onRunAnalysis, onModifyQuery, onExampleClick }) => {
    const messagesEndRef = useRef<HTMLDivElement>(null)

    // Auto-scroll to bottom when new messages arrive or streaming content grows
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages, streamingContent])

    if (messages.length === 0 && !isLoading) {
        const EXAMPLE_QUERIES = [
            { label: 'Lung adenocarcinoma OS', query: 'lung adenocarcinoma overall survival' },
            { label: 'Breast cancer biomarkers', query: 'breast cancer overall survival biomarkers' },
            { label: 'Colorectal cancer prognosis', query: 'colorectal cancer overall survival prognosis' },
        ]

        return (
            <div className={`${className} flex items-center justify-center`}>
                <div className="text-center px-4 max-w-xl">
                    {/* Free access statement — NAR requirement */}
                    <div className="mb-6 px-4 py-2 bg-green-50 border border-green-200 rounded-lg text-xs text-green-700">
                        This website is free and open to all users and there is no login requirement.
                    </div>

                    <div className="text-gray-400 mb-4">
                        <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                    </div>
                    <h3 className="text-lg font-medium text-gray-700 mb-2">
                        Cross-cohort survival biomarker discovery
                    </h3>
                    <p className="text-gray-500 text-sm">
                        Type a cancer type and survival endpoint, or click an example below to run a live analysis
                        across multiple independent GEO datasets.
                    </p>

                    {/* Try example — auto-runs analysis */}
                    <div className="mt-6">
                        <p className="text-xs font-medium text-gray-500 mb-3">Try a live example:</p>
                        <div className="flex flex-wrap justify-center gap-2">
                            {EXAMPLE_QUERIES.map((ex) => (
                                <button
                                    key={ex.query}
                                    onClick={() => onRunAnalysis?.(ex.query)}
                                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 transition-colors font-medium shadow-sm"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    {ex.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Chat examples */}
                    <div className="mt-5">
                        <p className="text-xs text-gray-400 mb-2">Or ask a question:</p>
                        <div className="flex flex-wrap justify-center gap-2">
                            {[
                                "Which genes predict OS in breast cancer?",
                                "Explain hazard ratio interpretation",
                                "How do I use batch gene mode?",
                            ].map((example) => (
                                <button
                                    key={example}
                                    onClick={() => onExampleClick?.(example)}
                                    className="px-3 py-1.5 bg-gray-100 text-gray-600 text-xs rounded-full hover:bg-indigo-100 hover:text-indigo-700 transition-colors"
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

                {isStreaming && (
                    <div className="flex items-start gap-3">
                        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                            <span className="text-blue-600 text-sm font-medium">AI</span>
                        </div>
                        <div className="max-w-[70%]">
                            <div className="bg-gray-100 rounded-lg px-4 py-3">
                                <div className="text-sm text-gray-800 whitespace-pre-wrap">
                                    {streamingContent || (
                                        <div className="flex items-center gap-1">
                                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                        </div>
                                    )}
                                    {streamingContent && (
                                        <span className="animate-pulse">&#9612;</span>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {isLoading && !isStreaming && (
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
