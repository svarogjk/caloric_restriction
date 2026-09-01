import React, { useEffect, useRef } from 'react'
import { ConsoleEntry } from './types'
import { AnalysisProgress as AnalysisProgressType } from '../../store/chatSlice'
import DoctorNoteEntry from './entries/DoctorNoteEntry'
import DoctorQuestionEntry from './entries/DoctorQuestionEntry'
import AssistantEntry from './entries/AssistantEntry'
import ActionRow from './entries/ActionRow'
import IntakeSummaryRow from './entries/IntakeSummaryRow'
import ReadoutCard from './entries/ReadoutCard'
import SummaryCard from './entries/SummaryCard'
import ModelCard from './entries/ModelCard'
import TreatmentEvidenceCard from './entries/TreatmentEvidenceCard'
import TreatmentContextCard from './entries/TreatmentContextCard'
import PathwayCard from './entries/PathwayCard'
import AnalysisProgressEntry from './entries/AnalysisProgressEntry'
import AnalysisResultCard from './entries/AnalysisResultCard'

interface ConsoleThreadProps {
    entries: ConsoleEntry[]
    onConfirmAction: (entryId: string) => void
    onDeclineAction: (entryId: string) => void
    onDismissNoteFact: (entryId: string, key: string) => void
    /** Focuses the chart rail — the single live intake form lives there now. */
    onFocusChart: () => void
    onShowTreatmentEvidence: (modelId: string) => void
    onAsk: (question: string) => void
    /** Progress keyed by run, so several analyses in one thread don't share a bar. */
    progressByRun: Record<string, AnalysisProgressType | null>
    isStreaming: boolean
    streamingContent: string
}

const EmptyThread: React.FC = () => (
    <div className="rounded-card border border-border bg-surface px-3.5 py-3">
        <div className="flex items-center gap-2 mb-1.5">
            <span className="w-5 h-5 rounded-full bg-accent-soft text-accent-fg text-[11px] flex items-center justify-center" aria-hidden>
                ✦
            </span>
            <span className="text-[11px] font-medium text-fg-muted">Assistant</span>
        </div>
        <p className="text-sm text-fg">
            Describe the case below, or start the chart on the right by picking a cancer type or loading a
            worked example.
        </p>
        <p className="text-[11px] text-fg-faint mt-1.5">
            Case details you type are parsed in your browser and read straight into the chart — only a
            de-identified summary is ever sent. No names, MRNs, or dates of birth.
        </p>
    </div>
)

/**
 * The conversation log: turns, the workflow steps the agent proposed, and the
 * evidence cards those steps produced. Chart STATE lives in PatientRail — the
 * thread only ever records that something happened.
 */
const ConsoleThread: React.FC<ConsoleThreadProps> = ({
    entries, onConfirmAction, onDeclineAction, onDismissNoteFact, onFocusChart,
    onShowTreatmentEvidence, onAsk, progressByRun, isStreaming, streamingContent,
}) => {
    const endRef = useRef<HTMLDivElement>(null)
    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [entries.length, streamingContent])

    return (
        <div className="flex-1 overflow-y-auto px-4 py-4">
            <div className="max-w-3xl mx-auto space-y-3">
                {entries.length === 0 && !isStreaming && <EmptyThread />}
                {entries.map((entry) => {
                    const content = (() => {
                        switch (entry.kind) {
                            case 'doctor-note':
                                return (
                                    <DoctorNoteEntry
                                        text={entry.text}
                                        extracted={entry.extracted}
                                        sentTurn={entry.sentTurn}
                                        timestamp={entry.timestamp}
                                        onDismissFact={(key) => onDismissNoteFact(entry.id, key)}
                                    />
                                )
                            case 'doctor-question':
                                return <DoctorQuestionEntry text={entry.text} timestamp={entry.timestamp} />
                            case 'assistant':
                                return (
                                    <AssistantEntry
                                        text={entry.text}
                                        domainScore={entry.domainScore}
                                        modelUsed={entry.modelUsed}
                                        timestamp={entry.timestamp}
                                        streaming={entry.streaming}
                                    />
                                )
                            case 'action':
                                return (
                                    <ActionRow
                                        action={entry.action}
                                        status={entry.status}
                                        detail={entry.detail}
                                        onConfirm={entry.status === 'proposed' ? () => onConfirmAction(entry.id) : undefined}
                                        onDecline={entry.status === 'proposed' ? () => onDeclineAction(entry.id) : undefined}
                                    />
                                )
                            case 'intake':
                                return <IntakeSummaryRow onJumpToActive={onFocusChart} />
                            case 'readout':
                                return (
                                    <ReadoutCard
                                        prediction={entry.prediction}
                                        modelId={entry.modelId}
                                        cancerLabel={entry.cancerLabel}
                                        modelIsDemo={entry.modelIsDemo}
                                        referenceCurves={entry.referenceCurves}
                                        timeUnit={entry.timeUnit}
                                        expression={entry.expression}
                                        clinical={entry.clinical}
                                    />
                                )
                            case 'summary':
                                return <SummaryCard resultId={entry.resultId} query={entry.query} />
                            case 'model-quality':
                                return <ModelCard modelId={entry.modelId} />
                            case 'treatment-evidence':
                                return (
                                    <TreatmentEvidenceCard
                                        modelId={entry.modelId}
                                        riskGroup={entry.riskGroup}
                                        genes={entry.genes}
                                        baselineCurve={entry.baselineCurve}
                                        expression={entry.expression}
                                        clinical={entry.clinical}
                                        timeUnit={entry.timeUnit}
                                    />
                                )
                            case 'treatment-context':
                                return (
                                    <TreatmentContextCard
                                        cancerType={entry.cancerType}
                                        expression={entry.expression}
                                        clinical={entry.clinical}
                                    />
                                )
                            case 'pathway':
                                return <PathwayCard geneSymbols={entry.geneSymbols} />
                            case 'analysis-progress':
                                return (
                                    <AnalysisProgressEntry
                                        query={entry.query}
                                        progress={progressByRun[entry.runId] ?? null}
                                        status={entry.status}
                                        error={entry.error}
                                    />
                                )
                            case 'analysis-result':
                                return (
                                    <AnalysisResultCard
                                        result={entry.result}
                                        resultId={entry.resultId}
                                        modelId={entry.modelId}
                                        focusGenes={entry.focusGenes}
                                        onShowTreatmentEvidence={() => entry.modelId && onShowTreatmentEvidence(entry.modelId)}
                                        onScorePatient={onFocusChart}
                                        onAsk={onAsk}
                                    />
                                )
                            default:
                                return null
                        }
                    })()
                    // id on the wrapper so "Full readout ↓" in the rail can scroll here.
                    return content ? <div key={entry.id} id={entry.id}>{content}</div> : null
                })}
                {isStreaming && <AssistantEntry text={streamingContent} streaming />}
                <div ref={endRef} />
            </div>
        </div>
    )
}

export default ConsoleThread
