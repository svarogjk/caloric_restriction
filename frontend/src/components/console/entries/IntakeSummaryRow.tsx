import React from 'react'

interface IntakeSummaryRowProps {
    /** Scrolls the thread to the one live intake form. */
    onJumpToActive: () => void
}

/**
 * A superseded "tumour profile requested" step. Only the newest intake entry
 * renders a live IntakeCard — every card is bound to the SAME exprText/clinical
 * state, so rendering more than one produced mirrored forms that looked like
 * independent patients. The earlier steps stay in the thread as this row so the
 * workflow log keeps its ordering.
 */
const IntakeSummaryRow: React.FC<IntakeSummaryRowProps> = ({ onJumpToActive }) => (
    <div className="flex items-center gap-2 text-[11px] pl-1 text-fg-faint">
        <span>⚙</span>
        <span>tumour expression profile requested</span>
        <button type="button" onClick={onJumpToActive} className="text-accent-fg hover:underline">
            ↓ go to the active form
        </button>
    </div>
)

export default IntakeSummaryRow
