import React, { useEffect, useState } from 'react'
import { getSignatureModel, PrognosticModel } from '../../../services/api'
import NomogramSVG from '../../signature/NomogramSVG'
import ConcordanceBenchmark from '../../signature/ConcordanceBenchmark'
import { StatTile, RuoNotice } from '../../ui'

interface ModelCardProps {
    modelId: string
}

/**
 * "How good is this model?" — fetches the already-built model directly (no
 * rebuild) and reuses the existing F18 nomogram + F19 concordance benchmark.
 */
const ModelCard: React.FC<ModelCardProps> = ({ modelId }) => {
    const [model, setModel] = useState<PrognosticModel | null>(null)
    const [error, setError] = useState(false)

    useEffect(() => {
        getSignatureModel(modelId).then(setModel).catch(() => setError(true))
    }, [modelId])

    if (error) return <p className="text-xs text-danger">Could not load this model.</p>
    if (!model) return <p className="text-xs text-fg-faint">Loading model details…</p>

    return (
        <div className="space-y-3">
            <div className="grid grid-cols-3 gap-2">
                <StatTile label="Pooled C-index" value={model.pooled_c_index.toFixed(3)} />
                <StatTile label="Genes" value={model.genes.length} />
                <StatTile label="Training cohort" value={model.training_accession} />
            </div>
            {model.cohort_validations.length > 0 && (
                <div className="text-xs text-fg-muted">
                    <p className="font-medium mb-1">Validated on:</p>
                    <ul className="space-y-0.5">
                        {model.cohort_validations.map((cv) => (
                            <li key={cv.accession}>
                                {cv.accession} ({cv.role}) — n={cv.n_samples}, C-index {cv.c_index.toFixed(3)}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
            <NomogramSVG model={model} />
            <ConcordanceBenchmark model={model} />
            <RuoNotice text={model.disclaimer} />
        </div>
    )
}

export default ModelCard
