import React from 'react'
import { useDispatch } from 'react-redux'
import { AppDispatch } from '../../store/store'
import { deleteConversation } from '../../store/chatSlice'
import { ConversationListItem } from '../../services/chatApi'

interface ConversationListProps {
    conversations: ConversationListItem[]
    activeConversationId: string | null
    onSelectConversation: (id: string) => void
    onNewConversation: () => void
    className?: string
}

const ConversationList: React.FC<ConversationListProps> = ({
    conversations,
    activeConversationId,
    onSelectConversation,
    onNewConversation,
    className = '',
}) => {
    const dispatch = useDispatch<AppDispatch>()

    const handleDelete = (e: React.MouseEvent, id: string) => {
        e.stopPropagation()
        if (window.confirm('Delete this conversation?')) {
            dispatch(deleteConversation(id))
        }
    }

    const formatDate = (isoString: string) => {
        const date = new Date(isoString)
        const now = new Date()
        const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))

        if (diffDays === 0) return 'Today'
        if (diffDays === 1) return 'Yesterday'
        if (diffDays < 7) return `${diffDays} days ago`
        return date.toLocaleDateString()
    }

    return (
        <div className={`${className} bg-gray-900 text-white flex flex-col`}>
            {/* Header */}
            <div className="p-4 border-b border-gray-700">
                <button
                    onClick={onNewConversation}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
                >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    <span>New Chat</span>
                </button>
            </div>

            {/* Conversation List */}
            <div className="flex-1 overflow-y-auto">
                {conversations.length === 0 ? (
                    <div className="p-4 text-center text-gray-400 text-sm">
                        No conversations yet
                    </div>
                ) : (
                    <div className="p-2 space-y-1">
                        {conversations.map((conversation) => (
                            <div
                                key={conversation.id}
                                onClick={() => onSelectConversation(conversation.id)}
                                className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                                    activeConversationId === conversation.id
                                        ? 'bg-gray-700'
                                        : 'hover:bg-gray-800'
                                }`}
                            >
                                <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                                </svg>

                                <div className="flex-1 min-w-0">
                                    <p className="text-sm truncate">
                                        {conversation.title || 'New Conversation'}
                                    </p>
                                    <p className="text-xs text-gray-500">
                                        {formatDate(conversation.updatedAt)}
                                    </p>
                                </div>

                                <button
                                    onClick={(e) => handleDelete(e, conversation.id)}
                                    className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-400 transition-opacity"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                    </svg>
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-gray-700">
                <p className="text-xs text-gray-500 text-center">
                    Powered by LangChain
                </p>
            </div>
        </div>
    )
}

export default ConversationList
