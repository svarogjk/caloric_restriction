import React, { useState } from 'react'
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import {
    buildSignature, PrognosticModel,
} from '../../services/api'
import { GROUP_COLORS, buildKMChartData } from '../../utils/signatureViz'
import NomogramSVG from './NomogramSVG'
import ConcordanceBenchmark from './ConcordanceBenchmark'
import { RuoNotice } from '../ui'

interface SignaturePanelProps {
    resultId?: string | null
    query?: string
}

type SigTab = 'overview' | 'nomogram' | 'concordance'

/**
 * F17 centerpiece UI + F18/F19 consumers.
 * Builds a validated multi-gene risk signature and exposes the locked
 * model through an overview, a nomogram (F18), and a concordance benchmark (F19).
 * Single-patient scoring lives in the unified Patient tab (PatientPanel).
 */
const SignaturePanel: React.FC<SignaturePanelProps> = ({ resultId, query }) => {
    const [model, setModel] = useState<PrognosticModel | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [tab, setTab] = useState<SigTab>('overview')

    const handleBuild = async (demo: boolean) => {
        setLoading(true)
        setError(null)
        try {
            const m = await buildSignature({ result_id: demo ? null : resultId, query, demo })
            setModel(m)
            setTab('overview')
        } catch (err) {
            const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
            setError(detail ?? 'Failed to build signature. Cohort expression matrices may not be cached locally — try the demo.')
        } finally {
            setLoading(false)
        }
    }

    if (!model) {
        return (
            <div className="p-6 text-center space-y-4">
                <div>
                    <h4 className="font-semibold text-fg-strong">Risk Signature</h4>
                    <p className="text-sm text-fg-muted mt-1 max-w-lg mx-auto">
                        Build a validated multi-gene risk score (continuous Cox model) trained on one cohort and
                        validated on independent GEO cohorts with Harrell's C-index. Stratifies patients into
                        low / intermediate / high risk groups.
                    </p>
                    <RuoNotice variant="inline" className="max-w-lg mx-auto" />
                </div>
                {error && (
                    <div className="text-sm text-warn bg-warn-soft border border-warn-border rounded p-2 max-w-lg mx-auto">
                        {error}
                    </div>
                )}
                <div className="flex gap-2 justify-center">
                    <button
                        onClick={() => handleBuild(false)}
                        disabled={loading || !resultId}
                        className="px-4 py-2 text-sm bg-accent text-on-accent rounded hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed"
                        title={resultId ? 'Build from this analysis' : 'Save the analysis first to build from real cohorts'}
                    >
                        {loading ? 'Building…' : 'Build from this analysis'}
                    </button>
                    <button
                        onClick={() => handleBuild(true)}
                        disabled={loading}
                        className="px-4 py-2 text-sm bg-surface-sunken text-fg border border-border-strong rounded hover:bg-surface-hover disabled:opacity-50"
                    >
                        Try demo signature
                    </button>
                </div>
                {!resultId && (
                    <p className="text-xs text-fg-faint">
                        Save this analysis to enable building from real cohorts, or try the synthetic demo.
                    </p>
                )}
            </div>
        )
    }

    return (
        <div>
            {/* Sub-tabs */}
            <div className="flex border-b mb-3 text-sm">
                {([
                    ['overview', 'Overview'],
                    ['nomogram', 'Nomogram'],
                    ['concordance', 'Concordance'],
                ] as [SigTab, string][]).map(([key, label]) => (
                    <button
                        key={key}
                        onClick={() => setTab(key)}
                        className={`px-3 py-1.5 font-medium ${
                            tab === key
                                ? 'text-accent-fg border-b-2 border-accent'
                                : 'text-fg-muted hover:text-fg'
                        }`}
                    >
                        {label}
                    </button>
                ))}
                <div className="ml-auto flex items-center pr-2">
                    <button
                        onClick={() => setModel(null)}
                        className="text-xs text-fg-faint hover:text-fg-muted"
                    >
                        ↺ Rebuild
                    </button>
                </div>
            </div>

            {model.is_demo && (
                <div className="mb-3 text-xs text-warn bg-warn-soft border border-warn-border rounded px-2 py-1">
                    Synthetic demo signature — illustrative only, not derived from real GEO data.
                </div>
            )}

            {tab === 'overview' && <SignatureOverview model={model} />}
            {tab === 'nomogram' && <NomogramSVG model={model} />}
            {tab === 'concordance' && <ConcordanceBenchmark model={model} />}

            <p className="text-[11px] text-fg-faint mt-4 border-t pt-2">{model.disclaimer}</p>
        </div>
    )
}

// ---------- F17 overview: validation + risk-tertile reference KM ----------

const SignatureOverview: React.FC<{ model: PrognosticModel }> = ({ model }) => {
    const kmData = buildKMChartData(model.reference_km)
    return (
        <div className="space-y-4">
            <div className="grid grid-cols-3 gap-2">
                <Stat label="Signature genes" value={String(model.genes.length)} color="text-alt" />
                <Stat label="Pooled C-index" value={model.pooled_c_index.toFixed(3)} color="text-accent-fg" />
                <Stat
                    label="Validation cohorts"
                    value={String(model.cohort_validations.filter((c) => c.role === 'validation').length)}
                    color="text-ok"
                />
            </div>

            <div>
                <h5 className="text-sm font-medium text-fg mb-1">Cross-cohort validation (Harrell's C-index)</h5>
                <table className="w-full text-xs border border-border rounded">
                    <thead className="bg-surface-sunken text-fg-muted text-left">
                        <tr>
                            <th className="px-2 py-1 font-medium">Cohort</th>
                            <th className="px-2 py-1 font-medium">Role</th>
                            <th className="px-2 py-1 font-medium">n</th>
                            <th className="px-2 py-1 font-medium">Events</th>
                            <th className="px-2 py-1 font-medium">C-index</th>
                        </tr>
                    </thead>
                    <tbody>
                        {model.cohort_validations.map((c) => (
                            <tr key={c.accession + c.role} className="border-t border-border">
                                <td className="px-2 py-1 font-medium text-fg">{c.accession}</td>
                                <td className="px-2 py-1">
                                    <span className={c.role === 'training' ? 'text-fg-muted' : 'text-accent-fg'}>
                                        {c.role}
                                    </span>
                                </td>
                                <td className="px-2 py-1 text-fg-muted">{c.n_samples}</td>
                                <td className="px-2 py-1 text-fg-muted">{c.n_events}</td>
                                <td className="px-2 py-1 font-medium">
                                    {Number.isFinite(c.c_index) ? c.c_index.toFixed(3) : '—'}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
                <p className="text-[11px] text-fg-faint mt-1">
                    C-index 0.5 = chance; higher = better discrimination. Trained on {model.training_accession}.
                </p>
            </div>

            {kmData.length > 0 && (
                <div>
                    <h5 className="text-sm font-medium text-fg mb-1">Reference survival by risk group (training cohort)</h5>
                    <div className="h-60">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={kmData} margin={{ top: 5, right: 10, bottom: 20, left: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" opacity={0.4} />
                                <XAxis
                                    dataKey="time"
                                    type="number"
                                    fontSize={11}
                                    label={{ value: `Time (${model.time_unit})`, position: 'insideBottom', offset: -10, fontSize: 11 }}
                                />
                                <YAxis domain={[0, 1]} fontSize={11} tickFormatter={(v) => v.toFixed(1)} />
                                <Tooltip formatter={(v: number) => v.toFixed(3)} />
                                <Legend />
                                {(['low', 'intermediate', 'high'] as const).map((grp) => (
                                    <Line
                                        key={grp}
                                        type="stepAfter"
                                        dataKey={grp}
                                        stroke={GROUP_COLORS[grp]}
                                        dot={false}
                                        strokeWidth={2}
                                        connectNulls
                                        name={`${grp} risk`}
                                    />
                                ))}
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            )}
        </div>
    )
}

// ---------- helpers ----------

const Stat: React.FC<{ label: string; value: string; color: string }> = ({ label, value, color }) => (
    <div className="text-center bg-surface-sunken rounded p-2">
        <p className={`text-2xl font-bold ${color}`}>{value}</p>
        <p className="text-xs text-fg-muted">{label}</p>
    </div>
)

export default SignaturePanel
