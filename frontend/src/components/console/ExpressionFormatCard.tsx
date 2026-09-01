import React from 'react'
import { Card } from '../ui'

const EXAMPLE_LINES = [
    ['ESR1', '12.1'],
    ['PGR', '11.4'],
    ['MKI67', '5.8'],
    ['ERBB2', '7.2'],
    ['TP53', '7.4'],
    ['GATA3', '11.8'],
]

interface ExpressionFormatCardProps {
    onTryExample: (text: string) => void
    compact?: boolean
}

/**
 * Always-visible, annotated example of the "GENE value" paste format — the
 * doctor-facing example the user explicitly asked for, not a hidden help link.
 */
const ExpressionFormatCard: React.FC<ExpressionFormatCardProps> = ({ onTryExample, compact = false }) => {
    const exampleText = EXAMPLE_LINES.map(([g, v]) => `${g} ${v}`).join('\n')
    const copy = async () => {
        try {
            await navigator.clipboard.writeText(exampleText)
        } catch {
            // Clipboard access can be denied — the "Try these lines" button still works.
        }
    }

    return (
        <Card tone="muted" dense={compact}>
            <p className="text-xs font-semibold text-fg mb-2">How to enter tumour expression</p>
            <div className="font-mono text-xs bg-surface border border-border rounded-control p-2 space-y-0.5">
                {EXAMPLE_LINES.map(([g, v]) => (
                    <div key={g} className="flex items-center gap-3">
                        <span className="text-accent-fg w-16">{g}</span>
                        <span className="text-fg-muted">{v}</span>
                        <span className="text-fg-faint text-[10px]">← gene symbol, value (log2 expression)</span>
                    </div>
                ))}
            </div>
            <ul className="text-[11px] text-fg-muted mt-2 space-y-0.5 list-disc list-inside">
                <li>Separator: space, tab, comma, or colon all work</li>
                <li>Paste the full profile (all measured genes, ≥40) — enables cross-platform normalization</li>
                <li>Log2-scale values; transform raw counts before pasting</li>
            </ul>
            <div className="flex gap-2 mt-2">
                <button
                    type="button"
                    onClick={copy}
                    className="text-[11px] px-2 py-1 rounded-control border border-border-strong text-fg-muted hover:bg-surface-sunken"
                >
                    Copy example
                </button>
                <button
                    type="button"
                    onClick={() => onTryExample(exampleText)}
                    className="text-[11px] px-2 py-1 rounded-control border border-border-accent text-accent-fg hover:bg-accent-soft"
                >
                    Try these 6 lines →
                </button>
            </div>
        </Card>
    )
}

export default ExpressionFormatCard
