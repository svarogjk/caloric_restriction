import React, { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import MessageBubble from './MessageBubble'
import { Message } from '../../store/chatSlice'
import { RESEARCH_EXAMPLES, type ResearchExample } from '../../utils/samplePatients'

interface MessageListProps {
    messages: Message[]
    isLoading: boolean
    isStreaming?: boolean
    streamingContent?: string
    className?: string
    onRunAnalysis?: (query: string) => void
    onModifyQuery?: (query: string) => void
    onExampleClick?: (example: string) => void
    /** Focuses the chat input and moves the cursor to the end — replaces a
     *  document.querySelector on the input's placeholder text. */
    onFocusInput?: () => void
    /** The chat input's current value, so clinical actions don't need to read the DOM for it. */
    inputValue?: string
}

// Conversational follow-up questions (go through the AI chat, not the analysis pipeline)
const AI_QUESTIONS = [
    'What does a C-index of 0.7 mean in practice?',
    'How do I interpret a hazard ratio above 2.0?',
    'What is the difference between prognostic and predictive biomarkers?',
    'What is heterogeneity (I²) and why does it matter?',
]

/**
 * Research-mode empty state — pure cross-cohort discovery, no patient
 * involved. The patient-facing workflow lives at "/" (ClinicalConsole);
 * this page is reached only via "Research" in the header.
 */
const MessageList: React.FC<MessageListProps> = ({
    messages, isLoading, isStreaming = false, streamingContent = '',
    className = '', onRunAnalysis, onModifyQuery, onExampleClick, onFocusInput,
}) => {
    const messagesEndRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages, streamingContent])

    const handleResearchSelect = (ex: ResearchExample) => {
        onModifyQuery?.(ex.text)
        onFocusInput?.()
    }

    if (messages.length === 0 && !isLoading) {
        return (
            <div className={`${className} flex items-start justify-center overflow-y-auto`}>
                <div className="px-4 max-w-2xl w-full py-6 space-y-6">

                    {/* Free access statement — NAR requirement */}
                    <div className="px-4 py-2 bg-ok-soft border border-ok-border rounded-lg text-xs text-ok text-center">
                        This website is free and open to all users and there is no login requirement.
                    </div>

                    {/* Hero */}
                    <div className="text-center">
                        <h3 className="text-lg font-semibold text-fg-strong">
                            Cross-cohort survival biomarker discovery
                        </h3>
                        <p className="text-sm text-fg-muted mt-1">
                            Ask a question in plain English — the app searches GEO, runs Cox regression across
                            independent cohorts, and returns Kaplan-Meier curves, forest plots, and hazard ratios.
                        </p>
                    </div>

                    <section className="rounded-2xl border border-border-accent bg-accent-soft/30 p-4 space-y-3">
                        <header>
                            <h4 className="flex items-center gap-2 text-sm font-semibold text-accent-fg">
                                🔬 Explore biomarkers
                            </h4>
                            <p className="text-xs text-fg-muted mt-1 leading-relaxed">
                                Discover, validate, or compare predictive and prognostic biomarker genes
                                across independent GEO cohorts. No patient needed.
                            </p>
                        </header>

                        <div className="space-y-2">
                            {RESEARCH_EXAMPLES.map((ex, i) => (
                                <button
                                    key={i}
                                    onClick={() => handleResearchSelect(ex)}
                                    className="w-full group flex items-start gap-3 px-4 py-3 rounded-xl border border-border-accent bg-surface hover:border-border-accent hover:bg-accent-soft/60 transition-all text-left"
                                >
                                    <span className="flex-1 text-sm text-fg leading-relaxed group-hover:text-fg-strong">
                                        {ex.text}
                                    </span>
                                    <svg
                                        className="w-4 h-4 mt-0.5 flex-shrink-0 text-fg-faint group-hover:text-accent-fg transition-colors"
                                        fill="none" stroke="currentColor" viewBox="0 0 24 24"
                                    >
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                            d="M3 12h18m-6-6l6 6-6 6" />
                                    </svg>
                                </button>
                            ))}
                        </div>

                        <p className="text-[11px] text-fg-faint">
                            Clicking pre-fills the input — press Enter to run, or edit it first. Or type your
                            own query below: any cancer type, any survival endpoint.
                        </p>
                    </section>

                    {/* Clinical console cross-link */}
                    <div className="text-center text-xs">
                        <Link to="/" className="text-accent-fg font-medium hover:underline">
                            Have a patient? Go to the Clinical Console →
                        </Link>
                        <span className="text-fg-faint"> — curated models, score in seconds.</span>
                    </div>

                    {/* ── AI follow-up questions ── */}
                    <div>
                        <p className="text-xs text-fg-faint mb-2">
                            Or ask the AI assistant a question:
                        </p>
                        <div className="flex flex-wrap gap-2">
                            {AI_QUESTIONS.map((q) => (
                                <button
                                    key={q}
                                    onClick={() => onExampleClick?.(q)}
                                    className="px-3 py-1.5 bg-surface-sunken text-fg-muted text-xs rounded-full hover:bg-accent-soft hover:text-accent-fg transition-colors"
                                >
                                    {q}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    const getLastUserMessage = (index: number): string | undefined => {
        for (let i = index - 1; i >= 0; i--) {
            if (messages[i].role === 'user') return messages[i].content
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
                        <div className="w-8 h-8 rounded-full bg-accent-soft flex items-center justify-center flex-shrink-0">
                            <span className="text-accent-fg text-sm font-medium">AI</span>
                        </div>
                        <div className="max-w-[70%]">
                            <div className="bg-surface-sunken rounded-lg px-4 py-3">
                                <div className="text-sm text-fg-strong whitespace-pre-wrap">
                                    {streamingContent || (
                                        <div className="flex items-center gap-1">
                                            <div className="w-2 h-2 bg-fg-faint rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                            <div className="w-2 h-2 bg-fg-faint rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                            <div className="w-2 h-2 bg-fg-faint rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                        </div>
                                    )}
                                    {streamingContent && <span className="animate-pulse">&#9612;</span>}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {isLoading && !isStreaming && (
                    <div className="flex items-start gap-3">
                        <div className="w-8 h-8 rounded-full bg-accent-soft flex items-center justify-center">
                            <span className="text-accent-fg text-sm font-medium">AI</span>
                        </div>
                        <div className="bg-surface-sunken rounded-lg px-4 py-3">
                            <div className="flex items-center gap-1">
                                <div className="w-2 h-2 bg-fg-faint rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                <div className="w-2 h-2 bg-fg-faint rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                <div className="w-2 h-2 bg-fg-faint rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
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
