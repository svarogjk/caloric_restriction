import React from 'react'
import { Card, Button, StepHeader } from '../../ui'
import { WorkflowState, WorkflowStepId } from '../../../utils/caseWorkflow'

export interface NextStepCardProps {
    workflow: WorkflowState
    goalLabel: string | null
    /** Runs the step: opens its control, or triggers its computation. */
    onAdvance: (step: WorkflowStepId) => void
    /** Why the step's control can't run yet, beyond the workflow's own gating. */
    advanceDisabledReason?: string
    busy: boolean
}

/** The call to action for each step — a verb, not a step name. */
const CTA: Record<WorkflowStepId, string> = {
    case: 'Choose the cancer type',
    profile: 'Add the tumour profile',
    evidence: 'Build the evidence base',
    score: 'Score this patient',
    why: 'Show what drives it',
    options: 'Show treatment evidence',
}

/**
 * The one thing to do now, always at the bottom of the thread.
 *
 * The full pipeline lives in the side WorkflowMap for whoever wants the bigger
 * picture; this card deliberately shows a single step, because a clinician
 * mid-consultation needs the next action, not a plan. Everything it offers is a
 * real computation or data check — no step is satisfied by the model talking.
 */
const NextStepCard: React.FC<NextStepCardProps> = ({
    workflow, goalLabel, onAdvance, advanceDisabledReason, busy,
}) => {
    const step = workflow.steps.find((s) => s.id === workflow.current) ?? null

    if (!step) {
        return (
            <Card tone="muted" dense>
                <div className="flex items-start gap-2">
                    <span className="text-ok text-sm" aria-hidden>✓</span>
                    <div className="min-w-0">
                        <p className="text-sm text-fg">
                            {goalLabel
                                ? `Everything ${goalLabel.replace(/\?$/, '').toLowerCase()} needs has run.`
                                : 'Every step has run.'}
                        </p>
                        <p className="text-[11px] text-fg-faint mt-0.5">
                            Ask a follow-up below, or open the workflow panel to revisit a step.
                        </p>
                    </div>
                </div>
            </Card>
        )
    }

    const running = step.status === 'running'
    const blocked = step.status === 'blocked'

    return (
        <Card tone="clinical" dense>
            <StepHeader
                index={step.index}
                title={`Next — ${step.label}`}
                status={running ? 'active' : blocked ? 'todo' : 'active'}
                hint={`step ${workflow.currentIndex} of ${workflow.totalNeeded}`}
            />

            <p className="text-sm text-fg mt-2">{step.purpose}</p>

            {blocked && step.blockedReason && (
                <p className="text-[11px] text-fg-muted mt-1">{step.blockedReason}</p>
            )}

            {running ? (
                <p className="text-[11px] text-accent-fg mt-2">
                    Running — {step.detail ?? 'this takes a few minutes'}. You can keep asking questions meanwhile.
                </p>
            ) : (
                <div className="mt-2.5">
                    <Button
                        size="sm"
                        onClick={() => onAdvance(step.id)}
                        loading={busy}
                        disabled={busy || blocked || !!advanceDisabledReason}
                        disabledReason={blocked ? step.blockedReason ?? undefined : advanceDisabledReason}
                    >
                        {CTA[step.id]}
                    </Button>
                </div>
            )}

            {workflow.caveats.length > 0 && (
                <div className="mt-2.5 pt-2.5 border-t border-border">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-warn">
                        Applies to everything below
                    </p>
                    <ul className="mt-0.5 space-y-0.5">
                        {workflow.caveats.map((c) => (
                            <li key={c} className="text-[11px] text-warn leading-snug">· {c}</li>
                        ))}
                    </ul>
                </div>
            )}
        </Card>
    )
}

export default NextStepCard
