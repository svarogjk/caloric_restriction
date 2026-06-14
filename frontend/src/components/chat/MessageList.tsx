import React, { useEffect, useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Link } from 'react-router-dom'
import MessageBubble from './MessageBubble'
import { RootState, AppDispatch } from '../../store/store'
import { Message, setPersonalizeEnabled, setPatientExpression } from '../../store/chatSlice'
import { SAMPLE_PATIENTS } from '../../utils/samplePatients'

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

// Full natural-language questions — exactly what a researcher or clinician would type.
// Clicking fills the input so the user sees what they're about to submit (and can edit it).
const SUGGESTED_QUESTIONS: {
    text: string        // shown in UI and pre-filled into the input
    query: string       // what is actually passed to the analysis pipeline
    role: 'researcher' | 'clinician'
}[] = [
    {
        role: 'researcher',
        text: 'What genes predict overall survival in lung adenocarcinoma across independent GEO cohorts?',
        query: 'lung adenocarcinoma overall survival',
    },
    {
        role: 'clinician',
        text: 'My breast cancer patient — which expression markers are most prognostic in GEO data?',
        query: 'breast cancer overall survival',
    },
    {
        role: 'researcher',
        text: 'Find colorectal cancer biomarkers consistently prognostic across multiple independent studies',
        query: 'colorectal cancer overall survival prognosis',
    },
    {
        role: 'clinician',
        text: 'Stage III ovarian cancer patient — what does the GEO literature say about survival markers?',
        query: 'ovarian cancer overall survival',
    },
    {
        role: 'researcher',
        text: 'Compare EGFR and KRAS as survival predictors in lung adenocarcinoma across GEO datasets',
        query: 'EGFR KRAS lung adenocarcinoma survival',
    },
    {
        role: 'clinician',
        text: 'Colorectal cancer patient — analyze prognostic expression patterns from independent cohorts',
        query: 'colorectal cancer stage III overall survival',
    },
]

// Conversational follow-up questions (go through the AI chat, not the analysis pipeline)
const AI_QUESTIONS = [
    'What does a C-index of 0.7 mean in practice?',
    'How is my patient\'s risk group assigned from expression data?',
    'How do I interpret a hazard ratio above 2.0?',
    'What is the difference between prognostic and predictive biomarkers?',
]

const MessageList: React.FC<MessageListProps> = ({
    messages, isLoading, isStreaming = false, streamingContent = '',
    className = '', onRunAnalysis, onModifyQuery, onExampleClick,
}) => {
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const dispatch = useDispatch<AppDispatch>()
    const personalizeEnabled = useSelector((s: RootState) => s.chat.personalizeEnabled)
    const patientExpression = useSelector((s: RootState) => s.chat.patientExpression)
    const [activeProfileId, setActiveProfileId] = useState<string | null>(null)
    const [toastMsg, setToastMsg] = useState<string | null>(null)

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages, streamingContent])

    const handleLoadProfile = (profileId: string, expression: string) => {
        dispatch(setPatientExpression(expression))
        setActiveProfileId(profileId)
        setToastMsg('Profile loaded — run an analysis above to score this patient.')
        setTimeout(() => setToastMsg(null), 2500)
    }

    // Clicking a suggested question: fills the chat input so the user sees exactly
    // what they're about to submit, then can press Enter (or edit it first).
    const handleSuggestionClick = (text: string, _query: string) => {
        onModifyQuery?.(text)
        // Scroll/focus the input area so the pre-filled text is obvious.
        setTimeout(() => {
            const input = document.querySelector<HTMLTextAreaElement>('textarea[placeholder*="survival"]')
            if (input) { input.focus(); input.setSelectionRange(input.value.length, input.value.length) }
        }, 50)
    }

    if (messages.length === 0 && !isLoading) {
        return (
            <div className={`${className} flex items-center justify-center`}>
                <div className="px-4 max-w-2xl w-full py-6 space-y-6">

                    {/* Free access statement — NAR requirement */}
                    <div className="px-4 py-2 bg-green-50 border border-green-200 rounded-lg text-xs text-green-700 text-center">
                        This website is free and open to all users and there is no login requirement.
                    </div>

                    {/* Hero */}
                    <div className="text-center">
                        <h3 className="text-lg font-semibold text-gray-800">
                            Cross-cohort survival biomarker discovery
                        </h3>
                        <p className="text-sm text-gray-500 mt-1">
                            Ask a question in plain English — the app searches GEO, runs Cox regression across
                            independent cohorts, and returns Kaplan-Meier curves, forest plots, and hazard ratios.
                        </p>
                    </div>

                    {/* ── Suggested questions ── */}
                    <div>
                        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
                            Try asking — click to pre-fill, then press Enter
                        </p>

                        <div className="space-y-2">
                            {SUGGESTED_QUESTIONS.map((q, i) => {
                                const isResearcher = q.role === 'researcher'
                                return (
                                    <button
                                        key={i}
                                        onClick={() => handleSuggestionClick(q.text, q.query)}
                                        className="w-full group flex items-start gap-3 px-4 py-3 rounded-xl border border-gray-200 bg-white hover:border-indigo-300 hover:bg-indigo-50/40 transition-all text-left"
                                    >
                                        {/* Category badge */}
                                        <span className={`mt-0.5 flex-shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide ${
                                            isResearcher
                                                ? 'bg-blue-100 text-blue-700'
                                                : 'bg-violet-100 text-violet-700'
                                        }`}>
                                            {isResearcher ? '🔬' : '🩺'}
                                            {isResearcher ? 'Research' : 'Clinical'}
                                        </span>

                                        {/* Question text — looks like what you'd type */}
                                        <span className="flex-1 text-sm text-gray-700 leading-relaxed group-hover:text-gray-900">
                                            {q.text}
                                        </span>

                                        {/* Arrow hint */}
                                        <svg
                                            className="w-4 h-4 mt-0.5 flex-shrink-0 text-gray-300 group-hover:text-indigo-500 transition-colors"
                                            fill="none" stroke="currentColor" viewBox="0 0 24 24"
                                        >
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                                d="M3 12h18m-6-6l6 6-6 6" />
                                        </svg>
                                    </button>
                                )
                            })}
                        </div>

                        <p className="text-[11px] text-gray-400 mt-3 text-center">
                            Or type your own query below — any cancer type, any survival endpoint.
                        </p>
                    </div>

                    {/* ── Patient personalisation ── */}
                    <div className="text-left bg-slate-50 border border-slate-200 rounded-xl p-4">
                        <label className="flex items-start gap-3 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={personalizeEnabled}
                                onChange={(e) => dispatch(setPersonalizeEnabled(e.target.checked))}
                                className="mt-0.5 h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                            />
                            <span>
                                <span className="block text-sm font-semibold text-gray-800">
                                    Add patient data — personalize results
                                </span>
                                <span className="block text-xs text-gray-500 mt-0.5">
                                    <strong>Off:</strong> standard cross-cohort GEO biomarker analysis.{' '}
                                    <strong>On:</strong> the same analysis <em>plus</em> a personalized prognostic
                                    estimate for your patient (risk group, predicted survival).{' '}
                                    Research use only — not a treatment-selection device.
                                </span>
                            </span>
                        </label>

                        {personalizeEnabled && (
                            <div className="mt-4 space-y-3">
                                <textarea
                                    value={patientExpression}
                                    onChange={(e) => dispatch(setPatientExpression(e.target.value))}
                                    rows={4}
                                    placeholder={'Paste the patient\'s tumour expression — "GENE value" per line:\nTP53 9.1\nMKI67 11.6\n…'}
                                    className="w-full text-xs font-mono border border-gray-300 rounded-lg p-2 focus:outline-none focus:ring-1 focus:ring-indigo-500 resize-none"
                                />

                                {/* Named example profiles */}
                                <div>
                                    <p className="text-xs font-medium text-gray-500 mb-2">
                                        Or load an example profile — select a cancer type to explore:
                                    </p>
                                    <div className="space-y-2">
                                        {SAMPLE_PATIENTS.map((profile) => {
                                            const isActive = activeProfileId === profile.id
                                            return (
                                                <button
                                                    key={profile.id}
                                                    onClick={() => handleLoadProfile(profile.id, profile.expression)}
                                                    className={`w-full flex items-start gap-3 p-3 rounded-lg border text-left transition-all ${
                                                        isActive
                                                            ? 'border-indigo-400 bg-indigo-50 ring-1 ring-indigo-300'
                                                            : 'border-gray-200 bg-white hover:border-indigo-300 hover:bg-indigo-50/40'
                                                    }`}
                                                >
                                                    <span
                                                        className="w-2.5 h-2.5 rounded-full mt-1.5 flex-shrink-0"
                                                        style={{ backgroundColor: profile.color }}
                                                    />
                                                    <div className="min-w-0">
                                                        <div className="flex items-center gap-2 flex-wrap">
                                                            <span className="text-sm font-semibold text-gray-800">
                                                                {profile.name}
                                                            </span>
                                                            <span className="text-[11px] text-indigo-600 font-medium bg-indigo-50 border border-indigo-100 rounded px-1.5 py-0.5">
                                                                {profile.cancerHint}
                                                            </span>
                                                        </div>
                                                        <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">
                                                            {profile.explanation}
                                                        </p>
                                                        <p className="text-xs text-indigo-600 mt-1 font-medium">
                                                            {profile.direction}
                                                        </p>
                                                    </div>
                                                </button>
                                            )
                                        })}
                                    </div>
                                </div>

                                <p className="text-[11px] text-gray-400">
                                    Run an analysis above — when it finishes, your patient is scored automatically in the{' '}
                                    <strong>Patient</strong> tab.
                                </p>
                            </div>
                        )}

                        <div className="mt-3 pt-2 border-t border-slate-200 text-xs">
                            <Link to="/oncologist" className="text-indigo-600 font-medium hover:underline">
                                Prefer ready-made models? Try Oncologist Mode →
                            </Link>
                            <span className="text-gray-400"> — curated signatures with a built-in demo patient.</span>
                        </div>
                    </div>

                    {/* ── AI follow-up questions ── */}
                    <div>
                        <p className="text-xs text-gray-400 mb-2">
                            Or ask the AI assistant a question:
                        </p>
                        <div className="flex flex-wrap gap-2">
                            {AI_QUESTIONS.map((q) => (
                                <button
                                    key={q}
                                    onClick={() => onExampleClick?.(q)}
                                    className="px-3 py-1.5 bg-gray-100 text-gray-600 text-xs rounded-full hover:bg-indigo-100 hover:text-indigo-700 transition-colors"
                                >
                                    {q}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Toast */}
                {toastMsg && (
                    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 px-4 py-2 bg-gray-800 text-white text-xs rounded-lg shadow-lg pointer-events-none">
                        {toastMsg}
                    </div>
                )}
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
                                    {streamingContent && <span className="animate-pulse">&#9612;</span>}
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
