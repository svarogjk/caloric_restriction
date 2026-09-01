import React, { useEffect, useState } from 'react'
import { getTreatmentContext, TreatmentComparison } from '../../../services/api'
import KaplanMeierChart from '../../KaplanMeierChart'
import { GROUP_COLORS, timesToYears } from '../../../utils/signatureViz'
import { Card, RuoNotice } from '../../ui'

interface TreatmentContextCardProps {
    cancerType: string
    expression: Record<string, number>
    clinical: Record<string, string>
}

/**
 * F24 — outcomes across documented treatment cohorts for this cancer type.
 *
 * The curves are per RISK TERTILE inside a treatment-matched cohort — NOT
 * treated-vs-untreated arms. Comparing tertiles across treatments says how this
 * patient's risk stratifies within each documented regimen; it does not compare
 * the regimens to each other, and there is no untreated comparator here at all.
 */
const TreatmentContextCard: React.FC<TreatmentContextCardProps> = ({ cancerType, expression, clinical }) => {
    const [treatments, setTreatments] = useState<TreatmentComparison[] | null>(null)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        getTreatmentContext({ cancer_type: cancerType, expression, clinical })
            .then((r) => setTreatments(r.treatments))
            .catch((err) => {
                const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
                setError(detail ?? 'Could not load treatment-cohort outcomes.')
            })
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [cancerType])

    if (error) return <p className="text-xs text-danger">{error}</p>
    if (!treatments) return <p className="text-xs text-fg-faint">Loading treatment-cohort outcomes…</p>

    return (
        <div className="space-y-2">
            {treatments.map((t) => (
                <Card key={t.slug} dense>
                    <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-fg-strong">{t.name}</span>
                        {t.is_building ? (
                            <span className="text-[11px] text-warn">building ({t.build_stage ?? '…'}, ~2-5 min)</span>
                        ) : t.build_error ? (
                            <span className="text-[11px] text-danger">unavailable</span>
                        ) : (
                            <span className="text-[11px] text-fg-muted">
                                {t.n_cohorts} cohort{t.n_cohorts === 1 ? '' : 's'} · n={t.n_patients} · C-index {t.pooled_c_index?.toFixed(2) ?? '—'}
                            </span>
                        )}
                    </div>
                    {t.risk_group && (
                        <p className="text-[11px] text-fg-muted mt-1">
                            This patient scored {t.risk_group} risk against this cohort's model
                            {t.risk_percentile != null ? ` (${Math.round(t.risk_percentile)}th percentile)` : ''}.
                        </p>
                    )}
                    {t.predicted_survival && t.predicted_survival.length > 0 && (
                        <div className="flex gap-3 mt-1">
                            {t.predicted_survival.map((s) => (
                                <span key={s.horizon_label} className="text-[11px] text-fg-muted">
                                    {s.horizon_label}: {(s.survival_probability * 100).toFixed(0)}%
                                </span>
                            ))}
                        </div>
                    )}
                    {/* reference_km was already being fetched and thrown away. */}
                    {t.reference_km && t.reference_km.length > 0 && (
                        <div className="mt-2">
                            <KaplanMeierChart
                                curves={t.reference_km.map((c) => ({
                                    key: `${t.slug}-${c.group}`,
                                    label: `${c.group} risk (n=${c.n_samples})`,
                                    times: timesToYears(c.times, t.time_unit ?? 'days'),
                                    survival_probabilities: c.survival_probabilities,
                                    color: GROUP_COLORS[c.group] ?? GROUP_COLORS.intermediate,
                                    // The patient's own tertile is the one to read.
                                    strokeWidth: c.group === t.risk_group ? 3 : 1.5,
                                    strokeOpacity: !t.risk_group || c.group === t.risk_group ? 1 : 0.45,
                                }))}
                                timeUnit="years"
                                height={170}
                            />
                            <p className="text-[10px] text-fg-faint mt-0.5">
                                Risk tertiles within this treatment's cohort — not a comparison against
                                untreated patients, and not a comparison between treatments.
                            </p>
                        </div>
                    )}
                </Card>
            ))}
            {treatments[0] && <RuoNotice text={treatments[0].disclaimer} />}
        </div>
    )
}

export default TreatmentContextCard
