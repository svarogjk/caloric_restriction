import React from 'react'
import { PredictResponse } from '../../services/api'
import { WorkflowState, WorkflowStep } from '../../utils/caseWorkflow'
import { ChartSource } from './types'
import ChartSummary from './ChartSummary'
import WorkflowMap from './WorkflowMap'
import RiskSummary from './RiskSummary'
import AnalysisSettings from './AnalysisSettings'

interface PatientRailProps {
    source: ChartSource
    cancerIcon: string | null
    geneCount: number
    covariateCount: number
    onClear: () => void
    /** Scrolls the thread to the live form — all editing happens there. */
    onEditInThread: () => void
    // Workflow
    workflow: WorkflowState
    goalLabel: string | null
    onGoToStep: (step: WorkflowStep) => void
    onClearGoal: () => void
    // Readout
    prediction: PredictResponse | null
    modelIsDemo: boolean
    timeUnit: string
    onOpenFullReadout: () => void
    onAsk: (question: string) => void
    /** Below lg the rail is a full-height sheet that covers the strip that
     *  opened it, so it has to carry its own way out. */
    onClose: () => void
}

/**
 * The side panel: where you are, and what is on the chart.
 *
 * It used to own the intake forms too, which split one workflow across two
 * surfaces — the assistant asked for a cancer type in the thread and the only
 * control to answer with was over here. Data entry now lives in the
 * conversation; this panel is read-only, and its job is the optional bigger
 * picture (WorkflowMap) that the in-thread next-step card deliberately omits.
 */
const PatientRail: React.FC<PatientRailProps> = ({
    source, cancerIcon, geneCount, covariateCount, onClear, onEditInThread,
    workflow, goalLabel, onGoToStep, onClearGoal,
    prediction, modelIsDemo, timeUnit, onOpenFullReadout, onAsk, onClose,
}) => (
    <aside className="h-full overflow-y-auto border-l border-border bg-canvas">
        <div className="p-3 space-y-3">
            <div className="flex items-center justify-between gap-2">
                <h2 className="text-[11px] font-semibold uppercase tracking-wide text-fg-faint">Where you are</h2>
                <button
                    type="button"
                    onClick={onClose}
                    aria-label="Close panel"
                    className="lg:hidden text-[11px] text-fg-faint hover:text-accent-fg"
                >
                    ✕ Close
                </button>
            </div>

            <WorkflowMap
                workflow={workflow}
                goalLabel={goalLabel}
                onGoToStep={onGoToStep}
                onClearGoal={onClearGoal}
            />

            <ChartSummary
                source={source}
                cancerIcon={cancerIcon}
                geneCount={geneCount}
                covariateCount={covariateCount}
                prediction={prediction}
                modelIsDemo={modelIsDemo}
                onClear={onClear}
                onEdit={onEditInThread}
            />

            {prediction && (
                <RiskSummary
                    prediction={prediction}
                    modelIsDemo={modelIsDemo}
                    timeUnit={timeUnit}
                    onOpenFullReadout={onOpenFullReadout}
                    onAsk={onAsk}
                />
            )}

            {/* The knobs a chat-driven run actually uses. They already applied
                to every console analysis; until now they had no UI outside
                /research, so the console silently used settings nobody could see. */}
            <AnalysisSettings />
        </div>
    </aside>
)

export default PatientRail
