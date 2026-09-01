import React, { useState } from 'react'
import { ConsoleAction } from '../../../services/chatApi'
import { ActionStatus } from '../types'
import { Button } from '../../ui'

function describe(action: ConsoleAction): string {
    switch (action.action) {
        case 'set_cancer_type': return `set cancer type → ${action.cancer_key}`
        case 'request_expression': return 'request tumour expression profile'
        case 'load_case': return `load example case → ${action.case_id}`
        case 'score_patient': return 'score patient'
        case 'explain_for_clinician': return 'show plain-language summary'
        case 'show_model_quality': return 'show model quality'
        case 'show_treatment_evidence': return 'show treatment evidence'
        case 'show_treatment_context': return 'show treatment-cohort outcomes'
        case 'show_driver_biology': return 'show driver-gene biology'
        case 'reuse_previous_analysis': return `reuse saved analysis → ${action.result_id}`
        case 'run_analysis': return `run survival analysis → "${action.query}"`
        default: return String(action.action)
    }
}

/** What the browser re-checked before this step was offered or run — the agent
 *  proposes, useConsoleActions.ts decides. */
function precondition(action: ConsoleAction): string {
    switch (action.action) {
        case 'set_cancer_type': return 'The cancer key was checked against the models in GET /api/gallery.'
        case 'load_case': return 'The case id was checked against the built-in worked examples. It replaces the current chart, so it needs your confirmation.'
        case 'run_analysis': return 'This downloads and analyses GEO cohorts — a few minutes — so it always needs your confirmation. Query confidence was checked before it was offered.'
        case 'score_patient': return 'Scoring runs in the browser against the loaded model; the expression profile is never sent to the assistant.'
        default: return 'The chart already holds everything this step needs, so it ran without changing any patient data.'
    }
}

const STATUS_LABEL: Record<ActionStatus, string> = {
    proposed: 'proposed',
    applied: 'done',
    declined: 'declined',
    failed: 'failed',
}

const STATUS_CLASS: Record<ActionStatus, string> = {
    proposed: 'text-fg-faint',
    applied: 'text-ok',
    declined: 'text-fg-faint',
    failed: 'text-danger',
}

const STATUS_GLYPH: Record<ActionStatus, string> = {
    proposed: '⚙',
    applied: '✓',
    declined: '–',
    failed: '✕',
}

interface ActionRowProps {
    action: ConsoleAction
    status: ActionStatus
    detail?: string
    onConfirm?: () => void
    onDecline?: () => void
}

/** One workflow step the agent proposed — always visible, so the assistant can
 *  never silently mutate the chart. Actions that overwrite data or cost
 *  minutes (run_analysis, load_case over a non-empty chart) show a
 *  confirm/decline pair instead of auto-applying. */
const ActionRow: React.FC<ActionRowProps> = ({ action, status, detail, onConfirm, onDecline }) => {
    const [showWhy, setShowWhy] = useState(false)

    return (
        <div className="pl-1">
            <div className="flex items-center flex-wrap gap-2 text-[11px]">
                <span className={STATUS_CLASS[status]} aria-hidden>{STATUS_GLYPH[status]}</span>
                <span className="text-fg-muted font-medium">{describe(action)}</span>
                {status === 'proposed' && onConfirm ? (
                    <span className="flex items-center gap-1.5">
                        <Button size="sm" onClick={onConfirm}>Start</Button>
                        <Button size="sm" variant="secondary" onClick={onDecline}>Skip</Button>
                    </span>
                ) : (
                    <span className={STATUS_CLASS[status]}>→ {STATUS_LABEL[status]}</span>
                )}
                {detail && <span className="text-fg-faint">({detail})</span>}
                <button
                    type="button"
                    onClick={() => setShowWhy((s) => !s)}
                    className="text-fg-faint hover:text-accent-fg hover:underline"
                >
                    {showWhy ? '▾' : '▸'} why?
                </button>
            </div>
            {showWhy && (
                <p className="text-[11px] text-fg-faint mt-1 pl-5 max-w-prose">{precondition(action)}</p>
            )}
        </div>
    )
}

export default ActionRow
