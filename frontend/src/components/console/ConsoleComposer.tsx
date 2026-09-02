import React, { forwardRef, useLayoutEffect, useRef, useState } from 'react'
import { parseCaseDescription, looksIdentifying, ExtractedCaseFacts } from '../../utils/caseParser'
import { matchQuestion, QuestionId, QuestionMatch } from '../../utils/questionCatalogue'
import PromptChips from './PromptChips'

const MAX_HEIGHT_PX = 200
const COUNTER_FROM = 1500

interface ConsoleComposerProps {
    /** A free-text case description was recognised — nothing is sent yet;
     *  the parent decides what (if anything, e.g. a residual question) to send. */
    onSubmitCase: (rawText: string, facts: ExtractedCaseFacts) => void
    /** An ordinary question, or a case's residual question — safe to send.
     *  `goal` is set when the text was mapped onto a catalogue question. */
    onSubmitQuestion: (text: string, goal?: QuestionId) => void
    chips: string[]
    disabled?: boolean
    /** One-line reminder of the de-identified chart snapshot the agent can see. */
    contextSummary?: string | null
    /** No conversation yet — the composer lifts toward the middle of the column
     *  instead of docking just above the bottom edge. */
    lifted?: boolean
    /** No goal chosen yet, so the FIRST question is mapped onto the catalogue
     *  before it is sent. Follow-ups pass through untouched — gating every turn
     *  would put a confirmation in front of "what does HR mean?". */
    requireGoal?: boolean
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
    ({ onSubmitCase, onSubmitQuestion, chips, disabled, contextSummary, lifted, requireGoal }, ref) => {
        const [value, setValue] = useState('')
        const [blockedText, setBlockedText] = useState<string | null>(null)
        /** A first question held back until the clinician confirms what it maps to. */
        const [pending, setPending] = useState<{ text: string; match: QuestionMatch | null } | null>(null)
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

        const send = (text: string, goal?: QuestionId) => {
            onSubmitQuestion(text, goal)
            setValue('')
            setBlockedText(null)
            setPending(null)
        }

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

            // The opening question is shown the pipeline it will run before it
            // runs — the app should never quietly answer a question it has no
            // computation for, and it must never rewrite what was asked either.
            if (requireGoal && !pending) {
                setPending({ text: trimmed, match: matchQuestion(trimmed) })
                return
            }

            send(trimmed)
        }

        const handleKeyDown = (e: React.KeyboardEvent) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                trySubmit(value)
            }
        }

        return (
            // Floating card, never flush with the viewport edge. While the thread is
            // empty the bottom pad lifts it toward the middle of the column, so the
            // greeting card + chips + input read as one "start here" cluster; the
            // first message drops it back to the docked gap.
            <div
                className={`bg-canvas px-4 pt-2 transition-[padding] duration-300 motion-reduce:transition-none ${
                    lifted ? 'pb-[16vh] [@media(max-height:700px)]:pb-6' : 'pb-3'
                }`}
            >
                {/* Same measure as the thread, so input and messages line up. */}
                <div className="mx-auto w-full max-w-3xl">
                    {contextSummary && (
                        <div className="mb-1.5 text-[10px] text-fg-faint">
                            <span className="text-fg-muted">{contextSummary}</span> — what the assistant can see
                        </div>
                    )}

                    {pending && (
                        <div className="mb-1.5 px-2.5 py-2 bg-surface border border-border-accent rounded-control">
                            {pending.match ? (
                                <>
                                    <p className="text-[11px] text-fg">
                                        This maps to{' '}
                                        <span className="font-medium text-fg-strong">{pending.match.question.label}</span>
                                    </p>
                                    <p className="text-[10px] text-fg-muted mt-0.5">{pending.match.question.delivers}</p>
                                    <p className="text-[10px] text-fg-faint mt-0.5">
                                        Runs: {pending.match.question.steps.join(' → ')}
                                    </p>
                                    <div className="flex items-center gap-2 mt-1.5 text-[11px]">
                                        <button
                                            type="button"
                                            className="font-medium text-accent-fg underline"
                                            onClick={() => send(pending.text, pending.match!.question.id)}
                                        >
                                            Use this
                                        </button>
                                        <button type="button" className="text-fg-muted underline" onClick={() => send(pending.text)}>
                                            Ask as written
                                        </button>
                                        <button type="button" className="text-fg-faint underline" onClick={() => setPending(null)}>
                                            Edit
                                        </button>
                                    </div>
                                </>
                            ) : (
                                <>
                                    <p className="text-[11px] text-fg">
                                        No pipeline matches this question, so there is nothing for the app to compute —
                                        it will be answered from the tools and whatever is already on screen.
                                    </p>
                                    <p className="text-[10px] text-fg-faint mt-0.5">
                                        The questions this app computes answers to are listed at the top of the thread.
                                    </p>
                                    <div className="flex items-center gap-2 mt-1.5 text-[11px]">
                                        <button type="button" className="font-medium text-accent-fg underline" onClick={() => send(pending.text)}>
                                            Ask anyway
                                        </button>
                                        <button type="button" className="text-fg-faint underline" onClick={() => setPending(null)}>
                                            Edit
                                        </button>
                                    </div>
                                </>
                            )}
                        </div>
                    )}

                    {blockedText && (
                        <div className="mb-1.5 px-2 py-1.5 bg-ruo-bg border border-ruo-border rounded-control text-[11px] text-ruo">
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
                        <div className="mb-1.5 text-[10px] text-warn">
                            ⚠ That looks like it may contain an identifier — it won't be sent as written.
                        </div>
                    )}

                    {/* One fixed-height row for chips + hint: the card below never
                        shifts when the chips disappear mid-stream. */}
                    <div className="flex items-center gap-2 h-7 mb-1.5">
                        <div className="flex-1 min-w-0">
                            {!disabled && <PromptChips prompts={chips} onSelect={(p) => trySubmit(p)} />}
                        </div>
                        <span className="flex-shrink-0 hidden sm:block text-[10px] text-fg-faint">
                            {value.length > COUNTER_FROM
                                ? `${value.length} characters`
                                : 'Enter to send · Shift+Enter for a new line'}
                        </span>
                    </div>

                    <div className="flex items-end gap-1.5 px-2 py-1.5 bg-surface border border-border rounded-card shadow-card transition-colors focus-within:border-border-accent focus-within:ring-1 focus-within:ring-accent-ring">
                        <textarea
                            ref={setRefs}
                            value={value}
                            onChange={(e) => setValue(e.target.value)}
                            onKeyDown={handleKeyDown}
                            disabled={disabled}
                            rows={1}
                            placeholder="Describe the case, paste data, or ask… — no names or identifiers"
                            className="flex-1 min-w-0 bg-transparent border-0 px-1.5 py-1 text-sm text-fg placeholder:text-fg-faint resize-none outline-none disabled:opacity-50"
                        />
                        <button
                            type="button"
                            onClick={() => trySubmit(value)}
                            disabled={disabled || !value.trim()}
                            aria-label="Send"
                            className="flex-shrink-0 w-8 h-8 grid place-items-center rounded-control bg-accent text-on-accent disabled:opacity-40 disabled:cursor-not-allowed hover:bg-accent-hover transition-colors"
                        >
                            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
                                <path d="M2 8h10M8 4l4 4-4 4" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        )
    },
)

ConsoleComposer.displayName = 'ConsoleComposer'

export default ConsoleComposer
