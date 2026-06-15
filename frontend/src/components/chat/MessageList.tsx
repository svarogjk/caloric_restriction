import React, { useEffect, useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Link } from 'react-router-dom'
import MessageBubble from './MessageBubble'
import { RootState, AppDispatch } from '../../store/store'
import { Message, setPersonalizeEnabled, setPatientExpression } from '../../store/chatSlice'
import {
    SAMPLE_PATIENTS,
    RESEARCH_EXAMPLES,
    type SamplePatient,
    type ResearchExample,
} from '../../utils/samplePatients'

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
    const editPanelRef = useRef<HTMLDivElement>(null)
    const dispatch = useDispatch<AppDispatch>()
    const personalizeEnabled = useSelector((s: RootState) => s.chat.personalizeEnabled)
    const patientExpression = useSelector((s: RootState) => s.chat.patientExpression)
    const [activeProfileId, setActiveProfileId] = useState<string | null>(null)
    const [toastMsg, setToastMsg] = useState<string | null>(null)
    const activeProfile = SAMPLE_PATIENTS.find((p) => p.id === activeProfileId) ?? null

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages, streamingContent])

    const showToast = (msg: string) => {
        setToastMsg(msg)
        setTimeout(() => setToastMsg(null), 2500)
    }

    // Focus + move cursor to the end of the chat input (reused by research clicks).
    const focusChatInput = () => {
        setTimeout(() => {
            const input = document.querySelector<HTMLTextAreaElement>('textarea[placeholder*="survival"]')
            if (input) { input.focus(); input.setSelectionRange(input.value.length, input.value.length) }
        }, 50)
    }

    // Clinical case: one click loads the patient's data + the matching query, turns on
    // personalization, and reveals the editable patient panel so the user can swap in
    // their own values before running.
    const handleClinicalSelect = (p: SamplePatient) => {
        dispatch(setPersonalizeEnabled(true)) // reducer also flips autoSave on
        dispatch(setPatientExpression(p.expression))
        onModifyQuery?.(p.query)
        setActiveProfileId(p.id)
        showToast(`${p.name} loaded — edit the values or click "Run prognostic analysis".`)
        setTimeout(() => editPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 60)
    }

    // "Use my own patient": personalize with an empty textarea to paste into.
    const handleUseOwnPatient = () => {
        dispatch(setPersonalizeEnabled(true))
        dispatch(setPatientExpression(''))
        setActiveProfileId(null)
        onModifyQuery?.('breast cancer overall survival')
        showToast('Paste your patient\'s expression, set the cancer query, then run.')
        setTimeout(() => editPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 60)
    }

    // Explicit run for the clinical column — personalize + expression are already set,
    // so the analysis result auto-scores the patient downstream (Patient tab).
    const handleRunClinical = () => {
        const input = document.querySelector<HTMLTextAreaElement>('textarea[placeholder*="survival"]')
        const query = (activeProfile?.query ?? input?.value ?? '').trim()
        if (!query) return
        onRunAnalysis?.(query)
    }

    // Research example: pure discovery — make sure no stale patient lingers, then pre-fill.
    const handleResearchSelect = (ex: ResearchExample) => {
        dispatch(setPersonalizeEnabled(false))
        setActiveProfileId(null)
        onModifyQuery?.(ex.text)
        focusChatInput()
    }

    if (messages.length === 0 && !isLoading) {
        return (
            <div className={`${className} flex items-start justify-center overflow-y-auto`}>
                <div className="px-4 max-w-4xl w-full py-6 space-y-6">

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
                        <p className="text-xs text-gray-400 mt-2">
                            Choose how you want to start:
                        </p>
                    </div>

                    {/* ── Two ways in: Clinical | Research ── */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">

                        {/* ─── Clinical column ─── */}
                        <section className="rounded-2xl border border-violet-200 bg-violet-50/30 p-4 space-y-3">
                            <header>
                                <h4 className="flex items-center gap-2 text-sm font-semibold text-violet-800">
                                    🩺 I have a patient
                                </h4>
                                <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                                    Pick a case to load its tumour expression and get a prognostic risk-group
                                    estimate grounded in independent GEO cohorts. <strong>Research use only</strong> —
                                    prognostic, not predictive; not a treatment-selection device.
                                </p>
                            </header>

                            <div className="space-y-2">
                                {SAMPLE_PATIENTS.map((p) => {
                                    const isActive = activeProfileId === p.id
                                    return (
                                        <button
                                            key={p.id}
                                            onClick={() => handleClinicalSelect(p)}
                                            className={`w-full flex items-start gap-3 p-3 rounded-xl border text-left transition-all ${
                                                isActive
                                                    ? 'border-violet-400 bg-white ring-1 ring-violet-300'
                                                    : 'border-violet-200 bg-white hover:border-violet-300 hover:bg-violet-50/60'
                                            }`}
                                        >
                                            <span
                                                className="w-2.5 h-2.5 rounded-full mt-1.5 flex-shrink-0"
                                                style={{ backgroundColor: p.color }}
                                            />
                                            <div className="min-w-0 flex-1">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className="text-sm font-semibold text-gray-800">
                                                        {p.name}
                                                    </span>
                                                    <span className="text-[11px] text-violet-700 font-medium bg-violet-50 border border-violet-100 rounded px-1.5 py-0.5">
                                                        {p.cancerHint}
                                                    </span>
                                                </div>
                                                <p className="text-xs text-gray-600 mt-1 font-medium">
                                                    {p.vignette}
                                                </p>
                                                <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">
                                                    {p.explanation}
                                                </p>
                                            </div>
                                        </button>
                                    )
                                })}
                            </div>

                            <button
                                onClick={handleUseOwnPatient}
                                className="w-full text-left px-3 py-2 rounded-lg border border-dashed border-violet-300 text-xs text-violet-700 hover:bg-violet-50 transition-colors"
                            >
                                + Use my own patient — paste your patient's expression values
                            </button>

                            {/* Shared editable patient panel (one Redux patientExpression) */}
                            {personalizeEnabled && (
                                <div ref={editPanelRef} className="rounded-xl border border-violet-300 bg-white p-3 space-y-2">
                                    <label className="block text-xs font-semibold text-gray-700">
                                        Patient expression{activeProfile ? ` — ${activeProfile.name}` : ''}
                                    </label>
                                    <p className="text-[11px] text-gray-500">
                                        Edit or replace with your patient's values — "GENE value" per line.
                                    </p>
                                    <textarea
                                        value={patientExpression}
                                        onChange={(e) => dispatch(setPatientExpression(e.target.value))}
                                        rows={5}
                                        placeholder={'TP53 9.1\nMKI67 11.6\nESR1 5.2\n…'}
                                        className="w-full text-xs font-mono border border-gray-300 rounded-lg p-2 focus:outline-none focus:ring-1 focus:ring-violet-500 resize-y"
                                    />
                                    {activeProfile?.direction && (
                                        <p className="text-xs text-violet-600 font-medium leading-relaxed">
                                            {activeProfile.direction}
                                        </p>
                                    )}
                                    <button
                                        onClick={handleRunClinical}
                                        disabled={!patientExpression.trim()}
                                        className="w-full px-3 py-2 rounded-lg bg-violet-600 text-white text-sm font-medium hover:bg-violet-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                                    >
                                        Run prognostic analysis →
                                    </button>
                                    <p className="text-[11px] text-gray-400">
                                        When the analysis finishes, your patient is scored automatically in the{' '}
                                        <strong>Patient</strong> tab.
                                    </p>
                                </div>
                            )}
                        </section>

                        {/* ─── Research column ─── */}
                        <section className="rounded-2xl border border-blue-200 bg-blue-50/30 p-4 space-y-3">
                            <header>
                                <h4 className="flex items-center gap-2 text-sm font-semibold text-blue-800">
                                    🔬 I'm exploring biomarkers
                                </h4>
                                <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                                    Discover, validate, or compare prognostic genes across independent GEO
                                    cohorts. No patient needed.
                                </p>
                            </header>

                            <div className="space-y-2">
                                {RESEARCH_EXAMPLES.map((ex, i) => (
                                    <button
                                        key={i}
                                        onClick={() => handleResearchSelect(ex)}
                                        className="w-full group flex items-start gap-3 px-4 py-3 rounded-xl border border-blue-200 bg-white hover:border-blue-300 hover:bg-blue-50/60 transition-all text-left"
                                    >
                                        <span className="flex-1 text-sm text-gray-700 leading-relaxed group-hover:text-gray-900">
                                            {ex.text}
                                        </span>
                                        <svg
                                            className="w-4 h-4 mt-0.5 flex-shrink-0 text-gray-300 group-hover:text-blue-500 transition-colors"
                                            fill="none" stroke="currentColor" viewBox="0 0 24 24"
                                        >
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                                d="M3 12h18m-6-6l6 6-6 6" />
                                        </svg>
                                    </button>
                                ))}
                            </div>

                            <p className="text-[11px] text-gray-400">
                                Clicking pre-fills the input — press Enter to run, or edit it first. Or type your
                                own query below: any cancer type, any survival endpoint.
                            </p>
                        </section>
                    </div>

                    {/* Oncologist Mode link */}
                    <div className="text-center text-xs">
                        <Link to="/oncologist" className="text-indigo-600 font-medium hover:underline">
                            Prefer ready-made models? Try Oncologist Mode →
                        </Link>
                        <span className="text-gray-400"> — curated signatures with a built-in demo patient.</span>
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
