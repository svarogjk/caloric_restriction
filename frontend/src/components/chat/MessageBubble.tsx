import React from 'react'
import { Message } from '../../store/chatSlice'

interface MessageBubbleProps {
    message: Message
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
    const isUser = message.role === 'user'
    const isSystem = message.role === 'system'

    if (isSystem) {
        return (
            <div className="flex justify-center my-2">
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-2 max-w-md">
                    <p className="text-sm text-yellow-700">{message.content}</p>
                </div>
            </div>
        )
    }

    return (
        <div className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
            {/* Avatar */}
            <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                isUser ? 'bg-blue-600' : 'bg-blue-100'
            }`}>
                <span className={`text-sm font-medium ${isUser ? 'text-white' : 'text-blue-600'}`}>
                    {isUser ? 'U' : 'AI'}
                </span>
            </div>

            {/* Message Content */}
            <div className={`max-w-[70%] ${isUser ? 'text-right' : ''}`}>
                <div className={`rounded-lg px-4 py-3 ${
                    isUser
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-800'
                }`}>
                    <div className="text-sm whitespace-pre-wrap">
                        {formatMessage(message.content)}
                    </div>
                </div>

                {/* Metadata */}
                <div className={`mt-1 flex items-center gap-2 text-xs text-gray-400 ${
                    isUser ? 'justify-end' : ''
                }`}>
                    <span>{formatTime(message.createdAt)}</span>
                    {message.modelUsed && (
                        <span className="text-gray-300">|</span>
                    )}
                    {message.modelUsed && (
                        <span>{message.modelUsed}</span>
                    )}
                </div>

                {/* Suggested Actions */}
                {message.suggestedActions && message.suggestedActions.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                        {message.suggestedActions.map((action, i) => (
                            <ActionButton key={i} action={action} />
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}

const ActionButton: React.FC<{ action: string }> = ({ action }) => {
    const actionLabels: Record<string, string> = {
        'run_analysis': 'Run Analysis',
        'modify_query': 'Modify Query',
        'use_improved_query': 'Use Improved Query',
    }

    return (
        <button className="px-3 py-1 text-xs bg-blue-50 text-blue-600 rounded-full hover:bg-blue-100 transition-colors">
            {actionLabels[action] || action}
        </button>
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
                <code key={i} className="px-1 py-0.5 bg-gray-200 rounded text-sm font-mono">
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
