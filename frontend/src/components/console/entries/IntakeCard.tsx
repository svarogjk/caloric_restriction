import React, { useState } from 'react'
import { Card, Button } from '../../ui'
import ExpressionInput from '../ExpressionInput'
import ExpressionFeedbackView from '../ExpressionFeedbackView'
import ExpressionFormatCard from '../ExpressionFormatCard'
import ClinicalCovariateFields from '../../oncologist/ClinicalCovariateFields'
import { ClinicalCovariateSpec } from '../../../services/api'
import { ExpressionFeedback } from '../../../utils/expressionFeedback'

export interface IntakeCardProps {
    exprText: string
    onExprChange: (text: string) => void
    feedback: ExpressionFeedback
    covariates: ClinicalCovariateSpec[]
    clinical: Record<string, string>
    onClinicalChange: (name: string, value: string) => void
    onScore: () => void
    loading: boolean
    disabledReason?: string
    fileError: string | null
    onFileError: (message: string) => void
    /** Fetches a synthetic profile for the current model, so the doctor can see
     *  what a scoreable input looks like without hunting for a file. */
    onLoadDemoProfile: () => void
    canLoadDemoProfile: boolean
}

const SectionLabel: React.FC<{ step: number; title: string; badge: string; badgeTone: 'required' | 'optional' }> = ({
    step, title, badge, badgeTone,
}) => (
    <div className="flex items-center gap-2">
        <span className="flex-shrink-0 w-4 h-4 rounded-full bg-surface-hover text-fg-muted text-[10px] flex items-center justify-center">
            {step}
        </span>
        <span className="text-sm font-medium text-fg">{title}</span>
        <span
            className={`text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded-full ${
                badgeTone === 'required' ? 'bg-warn-soft text-warn' : 'bg-surface-sunken text-fg-faint'
            }`}
        >
            {badge}
        </span>
    </div>
)

/**
 * Step 2/3 of the chart, surfaced as a card in the thread when the agent (or
 * a case load) calls request_tumour_profile.
 *
 * Expression comes FIRST and is marked required, with the covariate grid folded
 * away until something parses. /api/predict rejects an empty profile outright
 * (signature_routes.py) — covariates only ever refine an expression score, they
 * are never a substitute — but the old layout made the covariate grid the
 * visually dominant control, so people filled it in and then found Score
 * permanently greyed out with the reason in an 11px caption.
 */
const IntakeCard: React.FC<IntakeCardProps> = ({
    exprText, onExprChange, feedback, covariates, clinical, onClinicalChange, onScore, loading, disabledReason,
    fileError, onFileError, onLoadDemoProfile, canLoadDemoProfile,
}) => {
    const [showFormat, setShowFormat] = useState(false)
    const hasGenes = feedback.geneCount > 0
    const [showCovariates, setShowCovariates] = useState(false)

    const inputState = fileError ? 'error' : hasGenes ? 'ok' : 'empty'
    const filledCovariates = Object.values(clinical).filter((v) => v !== '').length

    return (
        <Card tone="clinical">
            <SectionLabel step={1} title="Tumour expression profile" badge="required" badgeTone="required" />

            {!hasGenes && (
                <div className="mt-2 px-2 py-1.5 rounded-control bg-warn-soft border border-warn-border text-[11px] text-warn">
                    ⚠ A tumour expression profile is needed before this patient can be scored — clinical
                    covariates alone cannot produce a risk score.
                </div>
            )}

            <div className="mt-2">
                <ExpressionInput value={exprText} onChange={onExprChange} onFileError={onFileError} state={inputState} />
            </div>
            {fileError && <p className="text-[11px] text-danger mt-1">{fileError}</p>}
            <ExpressionFeedbackView feedback={feedback} />

            <div className="flex items-center gap-3 mt-2">
                <button
                    type="button"
                    onClick={() => setShowFormat((s) => !s)}
                    className="text-[11px] text-accent-fg hover:underline"
                >
                    {showFormat ? '▾' : '▸'} Format & examples
                </button>
                <button
                    type="button"
                    onClick={onLoadDemoProfile}
                    disabled={!canLoadDemoProfile}
                    title={canLoadDemoProfile ? undefined : 'Pick a cancer type first'}
                    className="text-[11px] text-accent-fg hover:underline disabled:text-fg-faint disabled:no-underline disabled:cursor-not-allowed"
                >
                    ⚡ Load a demo profile
                </button>
            </div>
            {showFormat && <div className="mt-2"><ExpressionFormatCard onTryExample={onExprChange} compact /></div>}

            {covariates.length > 0 && (
                <div className="mt-3 pt-3 border-t border-border">
                    {/* Folded until expression parses: optional refinement should never
                        outrank the input the score actually depends on. */}
                    {hasGenes || showCovariates ? (
                        <>
                            <SectionLabel step={2} title="Clinical covariates" badge="optional" badgeTone="optional" />
                            <div className="mt-2">
                                <ClinicalCovariateFields
                                    covariates={covariates}
                                    values={clinical}
                                    onChange={onClinicalChange}
                                    columns={3}
                                />
                            </div>
                        </>
                    ) : (
                        <button
                            type="button"
                            onClick={() => setShowCovariates(true)}
                            className="text-[11px] text-fg-faint hover:text-accent-fg"
                        >
                            ▸ Clinical covariates (optional)
                            {filledCovariates > 0 ? ` — ${filledCovariates} filled in` : ''} — they refine a score, they can't replace the profile
                        </button>
                    )}
                </div>
            )}

            <div className="mt-3 pt-3 border-t border-border">
                <Button onClick={onScore} disabled={loading || !!disabledReason} loading={loading} disabledReason={disabledReason}>
                    Score patient
                </Button>
            </div>
        </Card>
    )
}

export default IntakeCard
