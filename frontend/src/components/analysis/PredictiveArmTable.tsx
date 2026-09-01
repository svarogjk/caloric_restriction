import React from 'react'
import InfoTooltip from '../InfoTooltip'
import { GeneSurvivalResponse } from '../../services/api'

interface PredictiveArmTableProps {
    gene: GeneSurvivalResponse
}

const formatP = (p: number | null | undefined): string => {
    if (p == null) return '—'
    return p < 0.001 ? p.toExponential(1) : p.toFixed(3)
}

/**
 * F16b — the per-treatment-arm hazard ratios behind a predictive
 * (treatment-effect-modifying) call.
 *
 * This is the ONLY treatment content that belongs on a default screen. It rides
 * along /api/search for free, needs no patient data and no model, and its claim
 * is deliberately narrow: this gene's prognostic effect DIFFERS by arm. It is
 * not a treated-vs-control survival comparison and must never be presented as
 * evidence that a treatment works — that would need randomisation these
 * observational cohorts do not have.
 *
 * Shared by AnalysisResultsDisplay (/research, /results/:id) and the console's
 * AnalysisResultCard so the two can't drift.
 */
const PredictiveArmTable: React.FC<PredictiveArmTableProps> = ({ gene }) => {
    const predictive = (gene.per_dataset_results ?? []).filter(
        (d) => d.is_predictive && d.treatment_arms && d.treatment_arms.length >= 2,
    )
    if (predictive.length === 0) return null

    return (
        <div className="mt-3 pt-3 border-t border-dashed border-warn-border">
            <div className="flex items-center gap-1 mb-1">
                <h5 className="text-xs font-semibold text-warn">
                    Predictive (treatment-effect-modifying)
                </h5>
                <InfoTooltip text="This gene's association with survival DIFFERS by treatment arm (significant expression × treatment interaction). Per-arm hazard ratios are shown below. Predictive biomarker signal is hypothesis-generating — validate prospectively; research use only." />
            </div>
            {predictive.map((d) => (
                <div key={d.dataset_id} className="mb-2">
                    <div className="text-[11px] text-fg-muted">
                        {d.dataset_id} · interaction p={formatP(d.interaction_p_value)}
                    </div>
                    <table className="w-full text-xs mt-0.5">
                        <thead>
                            <tr className="text-fg-faint text-left">
                                <th className="font-medium pr-2">Arm</th>
                                <th className="font-medium pr-2">HR (expression)</th>
                                <th className="font-medium">n (events)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {(d.treatment_arms ?? []).map((arm) => (
                                <tr key={arm.name} className="text-fg-muted">
                                    <td className="pr-2 py-0.5">{arm.name}</td>
                                    <td className={`pr-2 py-0.5 font-medium ${arm.hazard_ratio > 1 ? 'text-danger' : 'text-accent-fg'}`}>
                                        {arm.hazard_ratio.toFixed(2)} ({arm.ci_lower.toFixed(2)}–{arm.ci_upper.toFixed(2)})
                                    </td>
                                    <td className="py-0.5">{arm.n_samples} ({arm.n_events})</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ))}
            <p className="text-[10px] text-warn/80 mt-1">
                Hypothesis-generating; interaction tests are underpowered in small arms. Research use only.
            </p>
        </div>
    )
}

export default PredictiveArmTable
