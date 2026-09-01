import React, { useState } from 'react'
import { SamplePatient } from '../../utils/samplePatients'
import { Card, Chip } from '../ui'

interface CaseCardProps {
    patient: SamplePatient
    onLoad: (patient: SamplePatient) => void
}

/**
 * One tumour-board case card in the case library. One click loads the entire
 * chart — cancer type, expression, clinical covariates — and scores it
 * immediately when a curated model exists.
 */
const CaseCard: React.FC<CaseCardProps> = ({ patient, onLoad }) => {
    const [previewOpen, setPreviewOpen] = useState(false)
    const previewLines = patient.expression.split('\n').slice(0, 6)

    return (
        <Card dense className="flex flex-col gap-1.5">
            <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: patient.color }} />
                <span className="text-sm font-semibold text-fg-strong">{patient.name}</span>
            </div>
            <p className="text-xs text-fg-muted leading-relaxed">{patient.vignette}</p>
            <div className="flex flex-wrap gap-1">
                {patient.keyFindings.map((f) => <Chip key={f}>{f}</Chip>)}
            </div>
            <p className="text-[11px] text-fg-muted leading-relaxed line-clamp-2">{patient.explanation}</p>

            <button
                type="button"
                onClick={() => setPreviewOpen((o) => !o)}
                className="text-[11px] text-accent-fg hover:underline text-left"
            >
                {previewOpen ? '▾' : '▸'} Preview 50 expression values
            </button>
            {previewOpen && (
                <pre className="text-[10px] font-mono bg-surface-sunken border border-border rounded-control p-1.5 overflow-x-auto">
                    {previewLines.join('\n')}
                    {'\n…'}
                </pre>
            )}

            <p className="text-[10px] text-fg-faint italic">Synthetic teaching case — not a real patient.</p>

            <button
                type="button"
                onClick={() => onLoad(patient)}
                className="mt-1 text-xs font-medium text-accent-fg hover:underline text-right"
            >
                Load into chart →
            </button>
        </Card>
    )
}

export default CaseCard
