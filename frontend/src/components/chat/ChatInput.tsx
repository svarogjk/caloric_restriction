import React, { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react'

interface ChatInputProps {
    onSend: (message: string) => void
    disabled?: boolean
    placeholder?: string
    value?: string
    onChange?: (value: string) => void
}

const ChatInput = forwardRef<HTMLTextAreaElement, ChatInputProps>(({
    onSend,
    disabled = false,
    placeholder = 'Type a message...',
    value,
    onChange,
}, forwardedRef) => {
    const [internalMessage, setInternalMessage] = useState('')

    // Support both controlled and uncontrolled modes
    const message = value !== undefined ? value : internalMessage
    const setMessage = onChange !== undefined ? onChange : setInternalMessage
    const textareaRef = useRef<HTMLTextAreaElement>(null)
    useImperativeHandle(forwardedRef, () => textareaRef.current as HTMLTextAreaElement)

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
        <form onSubmit={handleSubmit} className="border-t border-border p-4">
            <div className="max-w-3xl mx-auto">
                <div className="flex items-end gap-2 bg-surface-sunken rounded-lg p-2">
                    <textarea
                        ref={textareaRef}
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={placeholder}
                        disabled={disabled}
                        rows={1}
                        className="flex-1 bg-transparent resize-none outline-none text-fg-strong placeholder-fg-faint px-2 py-1 max-h-48"
                    />
                    <button
                        type="submit"
                        disabled={!message.trim() || disabled}
                        className={`p-2 rounded-lg transition-colors ${
                            message.trim() && !disabled
                                ? 'bg-accent text-on-accent hover:bg-accent-hover'
                                : 'bg-surface-hover text-fg-muted cursor-not-allowed'
                        }`}
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                        </svg>
                    </button>
                </div>
                <p className="text-xs text-fg-faint mt-2 text-center">
                    Press Enter to send, Shift+Enter for new line
                </p>
            </div>
        </form>
    )
})

ChatInput.displayName = 'ChatInput'

export default ChatInput
