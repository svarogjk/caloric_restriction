import React from 'react'
import { GalleryCancer, ClinicalCovariateSpec, PredictResponse } from '../../services/api'
import { SamplePatient } from '../../utils/samplePatients'
import { ExpressionFeedback } from '../../utils/expressionFeedback'
import { ChartSource } from './types'
import CaseLibrary from './CaseLibrary'
import IntakeCard from './entries/IntakeCard'
import RiskSummary from './RiskSummary'
import AnalysisSettings from './AnalysisSettings'

interface PatientRailProps {
    source: ChartSource
    cancerIcon: string | null
    cancers: GalleryCancer[]
    cancersLoading: boolean
    onSelectCancer: (cancer: GalleryCancer) => void
    onBuildOther: (query: string) => void
    onLoadCase: (patient: SamplePatient) => void
    onTryFormatExample: (text: string) => void
    onClear: () => void
    // Intake
    exprText: string
    onExprChange: (text: string) => void
    expressionFeedback: ExpressionFeedback
    covariates: ClinicalCovariateSpec[]
    clinical: Record<string, string>
    onClinicalChange: (name: string, value: string) => void
    onScore: () => void
    scoring: boolean
    scoreDisabledReason?: string
    fileError: string | null
    onFileError: (message: string) => void
    onLoadDemoProfile: () => void
    canLoadDemoProfile: boolean
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

const SOURCE_NOTE: Record<ChartSource['kind'], string> = {
    none: '',
    curated: 'curated model',
    pending: 'no model yet — build one to score',
    cohort: 'cohort model built from your query',
}

/**
 * The chart: everything that is patient STATE rather than conversation. It sits
 * beside the thread instead of inside it, because a scrolling log is the wrong
 * place for the values a clinician needs continuously in view — and because one
 * rail makes exactly one live intake form structurally guaranteed.
 */
const PatientRail: React.FC<PatientRailProps> = ({
    source, cancerIcon, cancers, cancersLoading, onSelectCancer, onBuildOther, onLoadCase, onTryFormatExample, onClear,
    exprText, onExprChange, expressionFeedback, covariates, clinical, onClinicalChange, onScore, scoring,
    scoreDisabledReason, fileError, onFileError, onLoadDemoProfile, canLoadDemoProfile,
    prediction, modelIsDemo, timeUnit, onOpenFullReadout, onAsk, onClose,
}) => {
    const hasChart = source.kind !== 'none'

    return (
        <aside className="h-full overflow-y-auto border-l border-border bg-canvas">
            <div className="p-3 space-y-3">
                <div className="flex items-center justify-between gap-2">
                    <h2 className="text-[11px] font-semibold uppercase tracking-wide text-fg-faint">
                        {hasChart ? 'Patient chart' : 'Start a patient chart'}
                    </h2>
                    <div className="flex items-center gap-3">
                        {hasChart && (
                            <button type="button" onClick={onClear} className="text-[11px] text-fg-faint hover:text-danger">
                                Clear chart
                            </button>
                        )}
                        <button
                            type="button"
                            onClick={onClose}
                            aria-label="Close chart"
                            className="lg:hidden text-[11px] text-fg-faint hover:text-accent-fg"
                        >
                            ✕ Close
                        </button>
                    </div>
                </div>

                {hasChart && (
                    <div className="rounded-card border border-border bg-surface px-3 py-2">
                        <div className="flex items-center gap-2 min-w-0">
                            {cancerIcon && <span aria-hidden>{cancerIcon}</span>}
                            <span className="text-sm font-medium text-fg-strong truncate">{source.label}</span>
                        </div>
                        <p className="text-[11px] text-fg-faint mt-0.5">
                            {SOURCE_NOTE[source.kind]}
                            {expressionFeedback.geneCount > 0 && ` · ${expressionFeedback.geneCount} genes`}
                        </p>
                    </div>
                )}

                {!hasChart ? (
                    <CaseLibrary
                        cancers={cancers}
                        cancersLoading={cancersLoading}
                        onSelectCancer={onSelectCancer}
                        onBuildOther={onBuildOther}
                        onLoadCase={onLoadCase}
                        onTryFormatExample={onTryFormatExample}
                    />
                ) : (
                    <>
                        <div id="live-intake">
                        <IntakeCard
                            exprText={exprText}
                            onExprChange={onExprChange}
                            feedback={expressionFeedback}
                            covariates={covariates}
                            clinical={clinical}
                            onClinicalChange={onClinicalChange}
                            onScore={onScore}
                            loading={scoring}
                            disabledReason={scoreDisabledReason}
                            fileError={fileError}
                            onFileError={onFileError}
                            onLoadDemoProfile={onLoadDemoProfile}
                            canLoadDemoProfile={canLoadDemoProfile}
                        />
                        </div>

                        {prediction && (
                            <RiskSummary
                                prediction={prediction}
                                modelIsDemo={modelIsDemo}
                                timeUnit={timeUnit}
                                onOpenFullReadout={onOpenFullReadout}
                                onAsk={onAsk}
                            />
                        )}

                        <details className="rounded-card border border-border bg-surface">
                            <summary className="px-3 py-2 text-[11px] text-fg-muted cursor-pointer select-none">
                                Change cancer type / load another example
                            </summary>
                            <div className="px-3 pb-3">
                                <CaseLibrary
                                    cancers={cancers}
                                    cancersLoading={cancersLoading}
                                    onSelectCancer={onSelectCancer}
                                    onBuildOther={onBuildOther}
                                    onLoadCase={onLoadCase}
                                    onTryFormatExample={onTryFormatExample}
                                    compact
                                />
                            </div>
                        </details>
                    </>
                )}

                {/* The knobs a chat-driven run actually uses. They already applied
                    to every console analysis; until now they had no UI outside
                    /research, so the console silently used settings nobody could see. */}
                <AnalysisSettings />
            </div>
        </aside>
    )
}

export default PatientRail
