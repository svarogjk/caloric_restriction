import React, { forwardRef, useLayoutEffect, useRef, useState } from 'react'
import { parseCaseDescription, looksIdentifying, ExtractedCaseFacts } from '../../utils/caseParser'
import PromptChips from './PromptChips'

const MAX_HEIGHT_PX = 200
const COUNTER_FROM = 1500

interface ConsoleComposerProps {
    /** A free-text case description was recognised — nothing is sent yet;
     *  the parent decides what (if anything, e.g. a residual question) to send. */
    onSubmitCase: (rawText: string, facts: ExtractedCaseFacts) => void
    /** An ordinary question, or a case's residual question — safe to send. */
    onSubmitQuestion: (text: string) => void
    chips: string[]
    disabled?: boolean
    /** One-line reminder of the de-identified chart snapshot the agent can see. */
    contextSummary?: string | null
}

/**
 * The single composer for the clinical console — describing a case and asking
 * a question both go through the same box. Every submission is parsed first
 * (caseParser.ts) so free text is read into the chart locally rather than
 * sent as a chat message; a second identifier check gates anything that IS
 * about to be sent. The while-typing hint below is advisory only — it warns
 * earlier, it does not replace that gate.
 */
const ConsoleComposer = forwardRef<HTMLTextAreaElement, ConsoleComposerProps>(
    ({ onSubmitCase, onSubmitQuestion, chips, disabled, contextSummary }, ref) => {
        const [value, setValue] = useState('')
        const [blockedText, setBlockedText] = useState<string | null>(null)
        const innerRef = useRef<HTMLTextAreaElement | null>(null)

        const setRefs = (el: HTMLTextAreaElement | null) => {
            innerRef.current = el
            if (typeof ref === 'function') ref(el)
            else if (ref) (ref as React.MutableRefObject<HTMLTextAreaElement | null>).current = el
        }

        useLayoutEffect(() => {
            const el = innerRef.current
            if (!el) return
            el.style.height = 'auto'
            el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT_PX)}px`
        }, [value])

        // Advisory: warns while typing. The hard gate still runs on submit.
        const typingLooksIdentifying = value.trim().length > 8 && looksIdentifying(value.trim())

        const trySubmit = (text: string, override = false) => {
            const trimmed = text.trim()
            if (!trimmed) return

            const facts = parseCaseDescription(trimmed)
            if (facts.looksLikeCase) {
                onSubmitCase(trimmed, facts)
                setValue('')
                setBlockedText(null)
                return
            }

            if (!override && looksIdentifying(trimmed)) {
                setBlockedText(trimmed)
                return
            }

            onSubmitQuestion(trimmed)
            setValue('')
            setBlockedText(null)
        }

        const handleKeyDown = (e: React.KeyboardEvent) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                trySubmit(value)
            }
        }

        return (
            <div className="border-t border-border bg-surface">
                {!disabled && <PromptChips prompts={chips} onSelect={(p) => trySubmit(p)} />}

                {contextSummary && (
                    <div className="px-3 pb-1 text-[10px] text-fg-faint">
                        <span className="text-fg-muted">{contextSummary}</span> — what the assistant can see
                    </div>
                )}

                {blockedText && (
                    <div className="mx-3 mb-1 px-2 py-1.5 bg-ruo-bg border border-ruo-border rounded-control text-[11px] text-ruo">
                        This looks like it might contain a patient identifier (a name, MRN, or date of birth) —
                        it won't be sent.{' '}
                        <button type="button" className="underline font-medium" onClick={() => trySubmit(blockedText, true)}>
                            Send anyway
                        </button>
                        {' · '}
                        <button type="button" className="underline" onClick={() => setBlockedText(null)}>
                            Edit
                        </button>
                    </div>
                )}

                {!blockedText && typingLooksIdentifying && (
                    <div className="mx-3 mb-1 text-[10px] text-warn">
                        ⚠ That looks like it may contain an identifier — it won't be sent as written.
                    </div>
                )}

                <div className="flex items-end gap-2 px-3 pb-2 pt-1">
                    <textarea
                        ref={setRefs}
                        value={value}
                        onChange={(e) => setValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={disabled}
                        rows={1}
                        placeholder="Describe the case, paste data, or ask… — no names or identifiers"
                        className="flex-1 bg-surface-sunken border border-border rounded-control px-3 py-2 text-sm text-fg resize-none outline-none focus:ring-1 focus:ring-accent-ring disabled:opacity-50"
                    />
                    <button
                        type="button"
                        onClick={() => trySubmit(value)}
                        disabled={disabled || !value.trim()}
                        aria-label="Send"
                        className="p-2 rounded-control bg-accent text-on-accent disabled:opacity-40 disabled:cursor-not-allowed hover:bg-accent-hover transition-colors"
                    >
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
                            <path d="M2 8h10M8 4l4 4-4 4" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                    </button>
                </div>

                <div className="flex items-center justify-between px-3 pb-2 text-[10px] text-fg-faint">
                    <span>Enter to send · Shift+Enter for a new line</span>
                    {value.length > COUNTER_FROM && <span>{value.length} characters</span>}
                </div>
            </div>
        )
    },
)

ConsoleComposer.displayName = 'ConsoleComposer'

export default ConsoleComposer
