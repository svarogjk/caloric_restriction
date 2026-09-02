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
import StartCard, { StartCardProps } from './entries/StartCard'
import CaseSetupCard, { CaseSetupCardProps } from './entries/CaseSetupCard'
import IntakeCard, { IntakeCardProps } from './entries/IntakeCard'
import NextStepCard, { NextStepCardProps } from './entries/NextStepCard'

interface ConsoleThreadProps {
    entries: ConsoleEntry[]
    onConfirmAction: (entryId: string) => void
    onDeclineAction: (entryId: string) => void
    onDismissNoteFact: (entryId: string, key: string) => void
    /** Scrolls to the live form of a given kind — superseded steps link back to it. */
    onFocusChart: () => void
    onShowTreatmentEvidence: (modelId: string) => void
    onAsk: (question: string) => void
    /** Progress keyed by run, so several analyses in one thread don't share a bar. */
    progressByRun: Record<string, AnalysisProgressType | null>
    isStreaming: boolean
    streamingContent: string
    /** Nothing has happened yet — the greeting hugs the lifted composer instead
     *  of floating alone at the top of an empty column. */
    empty?: boolean
    // Live step forms. Bundled as the cards' own prop types rather than spread
    // across ~25 props, since the thread only forwards them.
    startProps: StartCardProps
    caseSetupProps: CaseSetupCardProps
    intakeProps: IntakeCardProps
    nextStepProps: NextStepCardProps
}

/**
 * The conversation log — turns, workflow steps, and the evidence cards those
 * steps produced — and now the steps' own controls.
 *
 * The intake forms used to live in the side rail, which meant the assistant
 * could ask for a cancer type but the answer had to be given somewhere else.
 * They render here instead; the rail reports chart state and nothing more.
 * Exactly one card of each kind is live: later duplicates of `case-setup` and
 * `intake` collapse to an IntakeSummaryRow, because every copy is bound to the
 * same underlying state.
 */
const ConsoleThread: React.FC<ConsoleThreadProps> = ({
    entries, onConfirmAction, onDeclineAction, onDismissNoteFact, onFocusChart,
    onShowTreatmentEvidence, onAsk, progressByRun, isStreaming, streamingContent, empty,
    startProps, caseSetupProps, intakeProps, nextStepProps,
}) => {
    const endRef = useRef<HTMLDivElement>(null)
    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [entries.length, streamingContent])

    const lastIdOfKind = (kind: ConsoleEntry['kind']): string | null => {
        for (let i = entries.length - 1; i >= 0; i--) {
            if (entries[i].kind === kind) return entries[i].id
        }
        return null
    }
    const liveCaseSetupId = lastIdOfKind('case-setup')
    const liveIntakeId = lastIdOfKind('intake')

    return (
        <div className={`flex-1 overflow-y-auto px-4 py-4 ${empty ? 'flex flex-col justify-end' : ''}`}>
            <div className="w-full max-w-3xl mx-auto space-y-3">
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
                            case 'start':
                                return <StartCard {...startProps} />
                            case 'case-setup':
                                return entry.id === liveCaseSetupId
                                    ? <CaseSetupCard {...caseSetupProps} />
                                    : <IntakeSummaryRow label="cancer type requested" onJumpToActive={onFocusChart} />
                            case 'intake':
                                return entry.id === liveIntakeId
                                    ? <IntakeCard {...intakeProps} />
                                    : <IntakeSummaryRow label="tumour expression profile requested" onJumpToActive={onFocusChart} />
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
                {/* Rendered outside the entry list, not appended to it: the next
                    step is derived from current state, so there must be exactly
                    one and it must always be last. Suppressed while the start
                    card is alone on screen — that card IS step 1, and saying so
                    twice reads as two different things to do. */}
                {!isStreaming && entries.length > 1 && (
                    <div id="next-step"><NextStepCard {...nextStepProps} /></div>
                )}
                <div ref={endRef} />
            </div>
        </div>
    )
}

export default ConsoleThread
