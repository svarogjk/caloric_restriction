import React from 'react'
import { Message } from '../../store/chatSlice'

interface MessageBubbleProps {
    message: Message
    onRunAnalysis?: (query: string) => void
    onModifyQuery?: (query: string) => void
    previousUserMessage?: string
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, onRunAnalysis, onModifyQuery, previousUserMessage }) => {
    const isUser = message.role === 'user'
    const isSystem = message.role === 'system'

    // Extract suggested query from AI response (e.g., quoted text like "breast cancer survival")
    const extractSuggestedQuery = (content: string): string | undefined => {
        // Look for quoted text that looks like a query suggestion
        const quotedMatches = content.match(/"([^"]{10,100})"/g)
        if (quotedMatches && quotedMatches.length > 0) {
            // Return the first quoted string that looks like a query
            for (const match of quotedMatches) {
                const unquoted = match.slice(1, -1)
                // Check if it looks like a search query (contains cancer/survival/gene terms)
                if (/survival|cancer|prognosis|gene|expression/i.test(unquoted)) {
                    return unquoted
                }
            }
        }
        return undefined
    }

    // Build the query with fallbacks
    const getActionQuery = (): string | undefined => {
        // Priority: 1. improved query from estimation, 2. extracted from AI text, 3. geo preview search query, 4. previous user message
        return (
            message.estimation?.improvedQuery ||
            extractSuggestedQuery(message.content) ||
            message.estimation?.geoPreview?.searchQuery ||
            previousUserMessage
        )
    }

    const actionQuery = !isUser && !isSystem ? getActionQuery() : undefined

    if (isSystem) {
        return (
            <div className="flex justify-center my-2">
                <div className="bg-warn-soft border border-warn-border rounded-lg px-4 py-2 max-w-md">
                    <p className="text-sm text-warn">{message.content}</p>
                </div>
            </div>
        )
    }

    return (
        <div className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
            {/* Avatar */}
            <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                isUser ? 'bg-accent' : 'bg-accent-soft'
            }`}>
                <span className={`text-sm font-medium ${isUser ? 'text-on-accent' : 'text-accent-fg'}`}>
                    {isUser ? 'U' : 'AI'}
                </span>
            </div>

            {/* Message Content */}
            <div className={`max-w-[70%] ${isUser ? 'text-right' : ''}`}>
                <div className={`rounded-lg px-4 py-3 ${
                    isUser
                        ? 'bg-accent text-on-accent'
                        : 'bg-surface-sunken text-fg-strong'
                }`}>
                    <div className="text-sm whitespace-pre-wrap">
                        {formatMessage(message.content)}
                    </div>
                </div>

                {/* Metadata */}
                <div className={`mt-1 flex items-center gap-2 text-xs text-fg-faint ${
                    isUser ? 'justify-end' : ''
                }`}>
                    <span>{formatTime(message.createdAt)}</span>
                    {message.modelUsed && (
                        <span className="text-fg-faint">|</span>
                    )}
                    {message.modelUsed && (
                        <span>{message.modelUsed}</span>
                    )}
                    {!isUser && message.domainScore !== undefined && message.domainScore !== null && (
                        <DomainScoreBadge score={message.domainScore} />
                    )}
                </div>

                {/* Suggested Actions */}
                {message.suggestedActions && message.suggestedActions.length > 0 && actionQuery && (
                    <div className="mt-2 flex flex-wrap gap-2">
                        {message.suggestedActions.map((action, i) => (
                            <ActionButton
                                key={i}
                                action={action}
                                onRunAnalysis={onRunAnalysis}
                                onModifyQuery={onModifyQuery}
                                query={actionQuery}
                            />
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}

interface ActionButtonProps {
    action: string
    onRunAnalysis?: (query: string) => void
    onModifyQuery?: (query: string) => void
    query?: string
}

const ActionButton: React.FC<ActionButtonProps> = ({ action, onRunAnalysis, onModifyQuery, query }) => {
    const actionLabels: Record<string, string> = {
        'run_analysis': 'Run Analysis',
        'modify_query': 'Modify Query',
        'use_improved_query': 'Use Improved Query',
    }

    const handleClick = () => {
        if (action === 'run_analysis' && onRunAnalysis && query) {
            onRunAnalysis(query)
        } else if ((action === 'modify_query' || action === 'use_improved_query') && onModifyQuery && query) {
            onModifyQuery(query)
        }
    }

    const isDisabled = (action === 'run_analysis' && (!onRunAnalysis || !query)) ||
        ((action === 'modify_query' || action === 'use_improved_query') && (!onModifyQuery || !query))

    return (
        <button
            onClick={handleClick}
            disabled={isDisabled}
            className={`px-3 py-1 text-xs rounded-full transition-colors ${
                isDisabled
                    ? 'bg-surface-sunken text-fg-faint cursor-not-allowed'
                    : 'bg-accent-soft text-accent-fg hover:bg-accent-soft'
            }`}
        >
            {actionLabels[action] || action}
        </button>
    )
}

interface DomainScoreBadgeProps {
    score: number
}

const DomainScoreBadge: React.FC<DomainScoreBadgeProps> = ({ score }) => {
    const colorClass =
        score >= 70 ? 'bg-ok-soft text-ok' :
        score >= 40 ? 'bg-warn-soft text-warn' :
                      'bg-surface-sunken text-fg-muted'

    return (
        <span
            className={`px-1.5 py-0.5 rounded text-xs font-medium cursor-help ${colorClass}`}
            title="Domain Score: measures how much of this answer came from real GEO data vs. general AI knowledge. 100 = fully grounded in your datasets."
        >
            DS {score}
        </span>
    )
}

function formatMessage(content: string): React.ReactNode {
    // Simple markdown-like formatting
    // Bold: **text**
    // Code: `code`
    // Lists: - item

    const parts = content.split(/(\*\*[^*]+\*\*|`[^`]+`)/g)

    return parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
            return <strong key={i}>{part.slice(2, -2)}</strong>
        }
        if (part.startsWith('`') && part.endsWith('`')) {
            return (
                <code key={i} className="px-1 py-0.5 bg-surface-hover rounded text-sm font-mono">
                    {part.slice(1, -1)}
                </code>
            )
        }
        return part
    })
}

function formatTime(isoString: string): string {
    const date = new Date(isoString)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default MessageBubble
