import React, { useState, useRef, useEffect } from 'react'

interface ChatInputProps {
    onSend: (message: string) => void
    disabled?: boolean
    placeholder?: string
}

const ChatInput: React.FC<ChatInputProps> = ({
    onSend,
    disabled = false,
    placeholder = 'Type a message...',
}) => {
    const [message, setMessage] = useState('')
    const textareaRef = useRef<HTMLTextAreaElement>(null)

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`
        }
    }, [message])

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        if (message.trim() && !disabled) {
            onSend(message.trim())
            setMessage('')
        }
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSubmit(e)
        }
    }

    return (
        <form onSubmit={handleSubmit} className="border-t border-gray-200 p-4">
            <div className="max-w-3xl mx-auto">
                <div className="flex items-end gap-2 bg-gray-100 rounded-lg p-2">
                    <textarea
                        ref={textareaRef}
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={placeholder}
                        disabled={disabled}
                        rows={1}
                        className="flex-1 bg-transparent resize-none outline-none text-gray-800 placeholder-gray-400 px-2 py-1 max-h-48"
                    />
                    <button
                        type="submit"
                        disabled={!message.trim() || disabled}
                        className={`p-2 rounded-lg transition-colors ${
                            message.trim() && !disabled
                                ? 'bg-blue-600 text-white hover:bg-blue-700'
                                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                        }`}
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                        </svg>
                    </button>
                </div>
                <p className="text-xs text-gray-400 mt-2 text-center">
                    Press Enter to send, Shift+Enter for new line
                </p>
            </div>
        </form>
    )
}

export default ChatInput
