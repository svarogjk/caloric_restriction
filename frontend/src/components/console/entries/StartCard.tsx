import React, { useMemo, useState } from 'react'
import { Card, Button, Chip } from '../../ui'
import { SamplePatient, SAMPLE_PATIENTS } from '../../../utils/samplePatients'
import { parseCaseDescription, looksIdentifying } from '../../../utils/caseParser'
import {
    QUESTION_CATALOGUE, AnswerableQuestion, QuestionId, isTemplateReady,
} from '../../../utils/questionCatalogue'
import CaseCard from '../CaseCard'

export interface StartCardProps {
    /** Commits the typed case description — same path as the composer's. */
    onSubmitCase: (text: string) => void
    onLoadCase: (patient: SamplePatient) => void
    /** Sets the goal and sends the question. `vars` fills {gene}/{cancer}. */
    onChooseQuestion: (question: AnswerableQuestion, vars: { gene?: string; cancer?: string }) => void
    selectedGoal: QuestionId | null
}

const EXAMPLE_CASE = '64F ER+/PR+/HER2−, invasive ductal, pT2N0, Ki-67 ~10%'

const FIELD_LABEL: Record<string, string> = {
    cancer_type: 'cancer type',
    age: 'age',
    stage: 'stage',
    grade: 'grade',
    ki67: 'Ki-67',
}

/**
 * The opening move: one patient, one question.
 *
 * Both halves are here rather than split between the thread and the rail,
 * because the first thing the console used to say was "describe the case below,
 * or start the chart on the right" — two entry points for one action. The
 * question half is a catalogue, so what a clinician asks for is something the
 * app can actually compute rather than something the model will improvise.
 */
const StartCard: React.FC<StartCardProps> = ({ onSubmitCase, onLoadCase, onChooseQuestion, selectedGoal }) => {
    const [caseText, setCaseText] = useState('')
    const [showExamples, setShowExamples] = useState(false)
    const [expanded, setExpanded] = useState<QuestionId | null>(null)
    const [vars, setVars] = useState<{ gene?: string; cancer?: string }>({})

    const facts = useMemo(() => parseCaseDescription(caseText), [caseText])
    const identifying = caseText.trim().length > 0 && looksIdentifying(caseText)

    const chips: { key: string; label: string }[] = []
    if (facts.cancerTerm) chips.push({ key: 'cancer_type', label: `${FIELD_LABEL.cancer_type}: ${facts.cancerTerm}` })
    for (const [k, v] of Object.entries(facts.covariates)) {
        chips.push({ key: k, label: `${FIELD_LABEL[k] ?? k}: ${v}` })
    }

    const commitCase = () => {
        const text = caseText.trim()
        if (!text) return
        onSubmitCase(text)
        setCaseText('')
    }

    const chooseQuestion = (q: AnswerableQuestion) => {
        if (q.placeholders.length > 0) {
            setExpanded(expanded === q.id ? null : q.id)
            return
        }
        onChooseQuestion(q, {})
    }

    return (
        <Card tone="clinical">
            <p className="text-sm text-fg">
                Two things to start: <span className="font-medium">who the patient is</span>, and{' '}
                <span className="font-medium">what you want to get</span>.
            </p>

            {/* ---- 1. the patient ---- */}
            <div className="mt-3">
                <h3 className="text-[11px] font-semibold uppercase tracking-wide text-fg-faint">Your patient</h3>
                <div className="mt-1.5 flex gap-1.5">
                    <input
                        type="text"
                        value={caseText}
                        onChange={(e) => setCaseText(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                                e.preventDefault()
                                commitCase()
                            }
                        }}
                        placeholder={EXAMPLE_CASE}
                        className="flex-1 min-w-0 text-sm bg-surface border border-border-strong rounded-control px-2.5 py-1.5 text-fg placeholder:text-fg-faint focus:outline-none focus:ring-1 focus:ring-accent-ring"
                    />
                    <Button size="sm" onClick={commitCase} disabled={!caseText.trim()}>
                        Read in
                    </Button>
                </div>

                {chips.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap items-center gap-1">
                        <span className="text-[10px] text-fg-faint">will be read into the chart:</span>
                        {chips.map((c) => (
                            <Chip key={c.key} tone="confirmed">{c.label}</Chip>
                        ))}
                    </div>
                )}
                {identifying && (
                    <p className="mt-1.5 text-[10px] text-warn">
                        ⚠ That looks like it may contain an identifier — it won’t be sent as written.
                    </p>
                )}
                <p className="mt-1.5 text-[10px] text-fg-faint">
                    Parsed in your browser. Only a de-identified summary reaches the assistant — no names, MRNs, or
                    dates of birth.{' '}
                    <button
                        type="button"
                        onClick={() => setCaseText(EXAMPLE_CASE)}
                        className="text-accent-fg hover:underline"
                    >
                        Use the example
                    </button>
                    {' · '}
                    <button
                        type="button"
                        onClick={() => setShowExamples((s) => !s)}
                        className="text-accent-fg hover:underline"
                    >
                        {showExamples ? 'Hide' : 'Load'} a worked case
                    </button>
                </p>

                {showExamples && (
                    <div className="mt-2 grid sm:grid-cols-2 gap-2">
                        {SAMPLE_PATIENTS.slice(0, 4).map((p) => (
                            <CaseCard key={p.id} patient={p} onLoad={onLoadCase} />
                        ))}
                    </div>
                )}
            </div>

            {/* ---- 2. the question ---- */}
            <div className="mt-4 pt-3 border-t border-border">
                <h3 className="text-[11px] font-semibold uppercase tracking-wide text-fg-faint">
                    What do you want to get?
                </h3>
                <p className="text-[10px] text-fg-faint mt-0.5">
                    These are the questions this app computes an answer to. Anything else can still be typed below —
                    it will be matched to the closest one first.
                </p>

                <ul className="mt-2 space-y-1">
                    {QUESTION_CATALOGUE.map((q) => {
                        const isOpen = expanded === q.id
                        const ready = isTemplateReady(q, vars)
                        return (
                            <li key={q.id}>
                                <button
                                    type="button"
                                    onClick={() => chooseQuestion(q)}
                                    aria-expanded={q.placeholders.length > 0 ? isOpen : undefined}
                                    className={`w-full text-left rounded-control border px-2.5 py-1.5 transition-colors ${
                                        selectedGoal === q.id
                                            ? 'border-border-accent bg-accent-soft'
                                            : 'border-border bg-surface hover:border-border-accent hover:bg-surface-accent'
                                    }`}
                                >
                                    <span className="block text-xs font-medium text-fg-strong">{q.label}</span>
                                    <span className="block text-[10px] text-fg-muted leading-snug">{q.delivers}</span>
                                </button>

                                {isOpen && (
                                    <div className="mt-1 ml-2 flex flex-wrap items-end gap-1.5">
                                        {q.placeholders.includes('gene') && (
                                            <input
                                                type="text"
                                                value={vars.gene ?? ''}
                                                onChange={(e) => setVars((v) => ({ ...v, gene: e.target.value }))}
                                                placeholder="gene, e.g. MKI67"
                                                className="w-36 text-xs bg-surface border border-border-strong rounded-control px-2 py-1 focus:outline-none focus:ring-1 focus:ring-accent-ring"
                                            />
                                        )}
                                        {q.placeholders.includes('cancer') && (
                                            <input
                                                type="text"
                                                value={vars.cancer ?? ''}
                                                onChange={(e) => setVars((v) => ({ ...v, cancer: e.target.value }))}
                                                placeholder="cancer type, e.g. gastric cancer"
                                                className="w-52 text-xs bg-surface border border-border-strong rounded-control px-2 py-1 focus:outline-none focus:ring-1 focus:ring-accent-ring"
                                            />
                                        )}
                                        <Button
                                            size="sm"
                                            disabled={!ready}
                                            disabledReason={ready ? undefined : 'Fill in the highlighted fields first'}
                                            onClick={() => onChooseQuestion(q, vars)}
                                        >
                                            Ask
                                        </Button>
                                    </div>
                                )}
                            </li>
                        )
                    })}
                </ul>
            </div>
        </Card>
    )
}

export default StartCard
