import React, { useState } from 'react'
import { WorkflowState, WorkflowStep, StepStatus } from '../../utils/caseWorkflow'

interface WorkflowMapProps {
    workflow: WorkflowState
    /** Label of the question being pursued, when one has been chosen. */
    goalLabel: string | null
    /** Jump to the card this step produced, or open the control that satisfies it. */
    onGoToStep: (step: WorkflowStep) => void
    onClearGoal?: () => void
}

const GLYPH: Record<StepStatus, string> = {
    done: '✓',
    'done-with-caveat': '✓',
    active: '→',
    blocked: '○',
    running: '⋯',
    'not-needed': '·',
}

const GLYPH_CLASS: Record<StepStatus, string> = {
    done: 'bg-ok-soft text-ok border-ok-border',
    'done-with-caveat': 'bg-warn-soft text-warn border-warn-border',
    active: 'bg-accent text-on-accent border-accent',
    blocked: 'bg-surface-sunken text-fg-faint border-border',
    running: 'bg-accent-soft text-accent-fg border-border-accent animate-pulse',
    'not-needed': 'bg-transparent text-fg-faint border-transparent',
}

const StepRow: React.FC<{ step: WorkflowStep; onGo: () => void }> = ({ step, onGo }) => {
    const dim = step.status === 'not-needed'
    const clickable = step.status !== 'not-needed' && step.status !== 'blocked'

    return (
        <li>
            <button
                type="button"
                onClick={clickable ? onGo : undefined}
                disabled={!clickable}
                aria-current={step.status === 'active' ? 'step' : undefined}
                className={`w-full text-left flex items-start gap-2 rounded-control px-1.5 py-1 transition-colors ${
                    clickable ? 'hover:bg-surface-hover cursor-pointer' : 'cursor-default'
                } ${dim ? 'opacity-45' : ''}`}
            >
                <span
                    className={`flex-shrink-0 mt-0.5 w-5 h-5 rounded-full border grid place-items-center text-[11px] font-semibold ${GLYPH_CLASS[step.status]}`}
                    aria-hidden
                >
                    {step.status === 'blocked' || step.status === 'not-needed' ? step.index : GLYPH[step.status]}
                </span>
                <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-1.5">
                        <span className={`text-xs font-medium ${dim ? 'text-fg-faint' : 'text-fg'}`}>{step.label}</span>
                        {step.status === 'not-needed' && (
                            <span className="text-[10px] text-fg-faint">not needed here</span>
                        )}
                        {step.caveats.length > 0 && (
                            <span className="text-[10px] text-warn" title={step.caveats.join(' ')} aria-label="caveat">
                                ⚠
                            </span>
                        )}
                    </span>
                    {step.detail && <span className="block text-[10px] text-fg-muted truncate">{step.detail}</span>}
                    {step.status === 'active' && !step.detail && (
                        <span className="block text-[10px] text-accent-fg">{step.purpose}</span>
                    )}
                    {step.blockedReason && (
                        <span className="block text-[10px] text-fg-faint">{step.blockedReason}</span>
                    )}
                </span>
            </button>
        </li>
    )
}

/**
 * The optional "bigger picture": the whole six-step pipeline, collapsed by
 * default to a single "Step 3 of 6" line.
 *
 * The step a clinician has to act on is always in the thread (NextStepCard) —
 * this exists so they can see where that step sits, what has already been
 * established, and which scientific caveats are in force, without having to
 * scroll the conversation back.
 */
const WorkflowMap: React.FC<WorkflowMapProps> = ({ workflow, goalLabel, onGoToStep, onClearGoal }) => {
    const [open, setOpen] = useState(false)
    const current = workflow.steps.find((s) => s.id === workflow.current) ?? null
    const caveatCount = workflow.caveats.length

    return (
        <div className="rounded-card border border-border bg-surface">
            <button
                type="button"
                onClick={() => setOpen((o) => !o)}
                aria-expanded={open}
                className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-surface-hover rounded-card transition-colors"
            >
                <span className="flex-1 min-w-0">
                    <span className="block text-[11px] font-semibold uppercase tracking-wide text-fg-faint">
                        {current
                            ? `Step ${workflow.currentIndex} of ${workflow.totalNeeded}`
                            : `${workflow.doneIds.length} of ${workflow.totalNeeded} done`}
                    </span>
                    <span className="block text-sm font-medium text-fg-strong truncate">
                        {current ? current.label : 'Workflow complete'}
                    </span>
                </span>
                {caveatCount > 0 && (
                    <span className="flex-shrink-0 text-[10px] text-warn" title={workflow.caveats.join(' ')}>
                        ⚠ {caveatCount}
                    </span>
                )}
                <span className="flex-shrink-0 text-[11px] text-fg-faint" aria-hidden>
                    {open ? '▾' : '▸'}
                </span>
            </button>

            {open && (
                <div className="px-1.5 pb-2">
                    {goalLabel && (
                        <div className="flex items-start gap-1.5 px-1.5 pb-1.5">
                            <span className="text-[10px] text-fg-faint flex-1">
                                Goal: <span className="text-fg-muted">{goalLabel}</span>
                            </span>
                            {onClearGoal && (
                                <button
                                    type="button"
                                    onClick={onClearGoal}
                                    className="flex-shrink-0 text-[10px] text-fg-faint hover:text-accent-fg underline"
                                >
                                    change
                                </button>
                            )}
                        </div>
                    )}
                    <ol className="space-y-0.5">
                        {workflow.steps.map((step) => (
                            <StepRow key={step.id} step={step} onGo={() => onGoToStep(step)} />
                        ))}
                    </ol>
                    {caveatCount > 0 && (
                        <div className="mt-2 mx-1.5 px-2 py-1.5 rounded-control bg-warn-soft border border-warn-border">
                            <p className="text-[10px] font-semibold uppercase tracking-wide text-warn mb-0.5">
                                Limits in force
                            </p>
                            <ul className="space-y-0.5">
                                {workflow.caveats.map((c) => (
                                    <li key={c} className="text-[10px] text-warn leading-snug">
                                        · {c}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

export default WorkflowMap
