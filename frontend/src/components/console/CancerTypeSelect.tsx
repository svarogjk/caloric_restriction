import React, { useState } from 'react'
import { GalleryCancer } from '../../services/api'
import { Button, Field } from '../ui'

interface CancerTypeSelectProps {
    cancers: GalleryCancer[]
    loading: boolean
    onSelect: (cancer: GalleryCancer) => void
    onBuildOther: (query: string) => void
}

/**
 * Step 1 of the chart: pick one of the 6 curated, cross-cohort-validated
 * cancer types (scores in seconds), or fall through to building a fresh
 * model from live GEO cohorts for anything else (~2-5 min).
 */
const CancerTypeSelect: React.FC<CancerTypeSelectProps> = ({ cancers, loading, onSelect, onBuildOther }) => {
    const [otherQuery, setOtherQuery] = useState('')

    return (
        <div className="space-y-2">
            {loading && <p className="text-xs text-fg-faint">Loading cancer types…</p>}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {cancers.map((c) => {
                    const ready = !!c.model_id
                    return (
                        <button
                            key={c.key}
                            type="button"
                            disabled={!ready}
                            onClick={() => onSelect(c)}
                            className={`text-left rounded-card border p-2.5 transition-colors ${
                                ready
                                    ? 'border-border bg-surface hover:border-border-accent hover:bg-surface-accent'
                                    : 'border-clinical-100 opacity-60 cursor-not-allowed'
                            }`}
                        >
                            <div className="flex items-center gap-1.5 text-sm font-medium text-fg-strong">
                                <span>{c.icon}</span> {c.label}
                            </div>
                            {ready ? (
                                <p className="text-[11px] text-fg-muted mt-0.5">
                                    Ready — scores in seconds · C-index {(c.pooled_c_index ?? 0).toFixed(2)}
                                    {c.n_genes ? ` · ${c.n_genes} genes` : ''}
                                    {c.model_is_demo && ' · demo model'}
                                </p>
                            ) : (
                                <p className="text-[11px] text-fg-faint mt-0.5">Preparing model…</p>
                            )}
                        </button>
                    )
                })}
            </div>

            <Field
                label="Other cancer type"
                hint="Builds a fresh model from live GEO cohorts (~2-5 min) instead of scoring instantly."
                className="pt-1"
            >
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={otherQuery}
                        onChange={(e) => setOtherQuery(e.target.value)}
                        placeholder="e.g. prostate cancer overall survival"
                        className="flex-1 text-sm border border-border-strong rounded-control px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-accent-ring"
                    />
                    <Button
                        variant="secondary"
                        size="sm"
                        disabled={!otherQuery.trim()}
                        onClick={() => onBuildOther(otherQuery.trim())}
                    >
                        Build (~2-5 min)
                    </Button>
                </div>
            </Field>
        </div>
    )
}

export default CancerTypeSelect
