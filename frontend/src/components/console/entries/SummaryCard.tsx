import React, { useEffect, useState } from 'react'
import ClinicianSummary from '../../ClinicianSummary'
import { getAnalysisResult } from '../../../services/api'
import { AnalysisResult } from '../../../store/chatSlice'
import { EmptyState } from '../../ui'

interface SummaryCardProps {
    resultId: string | null
    query: string
}

/**
 * "Explain this in plain language" — the existing F21 ClinicianSummary needs a
 * real cross-cohort AnalysisResult (per-gene HRs/p-values/GSE citations) to
 * summarise; a curated model scored via /api/personalize alone doesn't carry
 * that. When the cancer type has a cached cohort analysis (most non-demo
 * curated models do), fetch and use it. Otherwise, say so honestly rather
 * than fabricating a summary — "how good is this model" (ModelCard) or "what
 * is this based on" (get_signature_model_evidence) still work either way.
 */
const SummaryCard: React.FC<SummaryCardProps> = ({ resultId, query }) => {
    const [result, setResult] = useState<AnalysisResult | null>(null)
    const [error, setError] = useState(false)
    const [loading, setLoading] = useState(!!resultId)

    useEffect(() => {
        if (!resultId) return
        setLoading(true)
        getAnalysisResult(resultId)
            .then((r) => setResult(r))
            .catch(() => setError(true))
            .finally(() => setLoading(false))
    }, [resultId])

    if (!resultId) {
        return (
            <EmptyState
                title="No AI summary available for this model"
                body={`A plain-language summary needs a saved cross-cohort analysis for "${query}", and this curated model doesn't have one on record. Ask what the model is based on for its real cohort provenance instead.`}
            />
        )
    }
    if (loading) return <p className="text-xs text-fg-faint">Loading the underlying analysis…</p>
    if (error || !result) {
        return <EmptyState title="Could not load the underlying analysis" body="Try again, or ask about the model's cohort provenance instead." />
    }
    return <ClinicianSummary results={result} />
}

export default SummaryCard
