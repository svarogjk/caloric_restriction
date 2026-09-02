import React from 'react'

interface IntakeSummaryRowProps {
    /** What this superseded step was asking for. */
    label: string
    /** Scrolls the thread to the one live form of this kind. */
    onJumpToActive: () => void
}

/**
 * A superseded workflow step. Only the newest entry of each kind renders a live
 * form — every card is bound to the SAME exprText/clinical/source state, so
 * rendering more than one produced mirrored forms that looked like independent
 * patients. The earlier steps stay in the thread as this row so the workflow log
 * keeps its ordering.
 */
const IntakeSummaryRow: React.FC<IntakeSummaryRowProps> = ({ label, onJumpToActive }) => (
    <div className="flex items-center gap-2 text-[11px] pl-1 text-fg-faint">
        <span aria-hidden>⚙</span>
        <span>{label}</span>
        <button type="button" onClick={onJumpToActive} className="text-accent-fg hover:underline">
            ↓ go to the active form
        </button>
    </div>
)

export default IntakeSummaryRow
