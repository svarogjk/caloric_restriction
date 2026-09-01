import React, { useState } from 'react'
import { ExpressionFeedback } from '../../utils/expressionFeedback'

interface ExpressionFeedbackViewProps {
    feedback: ExpressionFeedback
}

const Row: React.FC<{ ok: boolean; children: React.ReactNode }> = ({ ok, children }) => (
    <div className={`flex items-start gap-1.5 text-[11px] ${ok ? 'text-ok' : 'text-warn'}`}>
        <span>{ok ? '✓' : '⚠'}</span>
        <span>{children}</span>
    </div>
)

/**
 * Live diagnostics for the pasted expression profile — genes recognised,
 * quantile-normalization readiness, signature coverage, and why any lines
 * were skipped. Everything here updates as the doctor types, instead of only
 * surfacing errors after they hit Score.
 */
const ExpressionFeedbackView: React.FC<ExpressionFeedbackViewProps> = ({ feedback }) => {
    const [showSkipped, setShowSkipped] = useState(false)

    if (feedback.geneCount === 0 && feedback.skipped.length === 0) return null

    return (
        <div className="space-y-1 mt-2">
            <Row ok={feedback.geneCount > 0}>
                {feedback.geneCount} gene{feedback.geneCount === 1 ? '' : 's'} recognised
            </Row>
            <Row ok={feedback.qnReady}>
                {feedback.qnReady
                    ? 'Quantile normalization ready (≥40 genes)'
                    : 'Per-gene ranking fallback — assumes a comparable scale. Paste the full profile for cross-platform normalization.'}
            </Row>
            {feedback.signatureTotal > 0 && (
                <Row ok={!feedback.lowCoverage}>
                    {feedback.signatureMatched} of {feedback.signatureTotal} signature genes matched
                    {' '}({Math.round(feedback.coverageFrac * 100)}%)
                    {feedback.lowCoverage && ' — below 60%, the score will carry a low-coverage warning'}
                </Row>
            )}
            {feedback.scaleHint === 'possibly-raw-counts' && feedback.valueRange && (
                <Row ok={false}>
                    Values up to {Math.round(feedback.valueRange[1]).toLocaleString()} — these look like raw counts.
                    Log2-transform before scoring.
                </Row>
            )}
            {feedback.multiColumn && (
                <Row ok={false}>Multi-sample matrix detected — only the first value column is used.</Row>
            )}
            {feedback.duplicates.length > 0 && (
                <Row ok={false}>
                    {feedback.duplicates.length} duplicate gene{feedback.duplicates.length === 1 ? '' : 's'}
                    {' '}({feedback.duplicates.slice(0, 5).join(', ')}) — last value used
                </Row>
            )}
            {feedback.skipped.length > 0 && (
                <div>
                    <button
                        type="button"
                        onClick={() => setShowSkipped((s) => !s)}
                        className="text-[11px] text-warn hover:underline"
                    >
                        {showSkipped ? '▾' : '▸'} {feedback.skipped.length} line{feedback.skipped.length === 1 ? '' : 's'} skipped
                    </button>
                    {showSkipped && (
                        <ul className="mt-1 space-y-0.5 pl-3 border-l border-border">
                            {feedback.skipped.map((s) => (
                                <li key={s.lineNumber} className="text-[11px] text-fg-muted font-mono">
                                    line {s.lineNumber}: "{s.text}" — {s.reason.replace(/-/g, ' ')}
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            )}
        </div>
    )
}

export default ExpressionFeedbackView
