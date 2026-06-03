import React, { useState } from 'react'
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import {
    buildSignature, getDemoPatient, predictSingleSample,
    PrognosticModel, PredictResponse, ReferenceKMCurve,
} from '../../services/api'
import NomogramSVG from './NomogramSVG'
import ConcordanceBenchmark from './ConcordanceBenchmark'

interface SignaturePanelProps {
    resultId?: string | null
    query?: string
}

const GROUP_COLORS: Record<string, string> = {
    low: '#22c55e',
    intermediate: '#f59e0b',
    high: '#ef4444',
}

type SigTab = 'overview' | 'nomogram' | 'concordance' | 'predict'

/**
 * F17 centerpiece UI + F18/F19/F23 consumers.
 * Builds a validated multi-gene prognostic signature and exposes the locked
 * model through a nomogram (F18), a concordance benchmark (F19), and a
 * single-sample risk calculator (F23, research use only).
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
                    <h4 className="font-semibold text-gray-800">Prognostic Signature</h4>
                    <p className="text-sm text-gray-500 mt-1 max-w-lg mx-auto">
                        Build a validated multi-gene risk score (continuous Cox model) trained on one cohort and
                        validated on independent GEO cohorts with Harrell's C-index. Stratifies patients into
                        low / intermediate / high risk groups. <span className="font-medium">Prognostic, research use only.</span>
                    </p>
                </div>
                {error && (
                    <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded p-2 max-w-lg mx-auto">
                        {error}
                    </div>
                )}
                <div className="flex gap-2 justify-center">
                    <button
                        onClick={() => handleBuild(false)}
                        disabled={loading || !resultId}
                        className="px-4 py-2 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        title={resultId ? 'Build from this analysis' : 'Save the analysis first to build from real cohorts'}
                    >
                        {loading ? 'Building…' : 'Build from this analysis'}
                    </button>
                    <button
                        onClick={() => handleBuild(true)}
                        disabled={loading}
                        className="px-4 py-2 text-sm bg-gray-100 text-gray-700 border border-gray-300 rounded hover:bg-gray-200 disabled:opacity-50"
                    >
                        Try demo signature
                    </button>
                </div>
                {!resultId && (
                    <p className="text-xs text-gray-400">
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
                    ['predict', 'Patient score'],
                ] as [SigTab, string][]).map(([key, label]) => (
                    <button
                        key={key}
                        onClick={() => setTab(key)}
                        className={`px-3 py-1.5 font-medium ${
                            tab === key
                                ? 'text-indigo-600 border-b-2 border-indigo-600'
                                : 'text-gray-500 hover:text-gray-700'
                        }`}
                    >
                        {label}
                    </button>
                ))}
                <div className="ml-auto flex items-center pr-2">
                    <button
                        onClick={() => setModel(null)}
                        className="text-xs text-gray-400 hover:text-gray-600"
                    >
                        ↺ Rebuild
                    </button>
                </div>
            </div>

            {model.is_demo && (
                <div className="mb-3 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                    Synthetic demo signature — illustrative only, not derived from real GEO data.
                </div>
            )}

            {tab === 'overview' && <SignatureOverview model={model} />}
            {tab === 'nomogram' && <NomogramSVG model={model} />}
            {tab === 'concordance' && <ConcordanceBenchmark model={model} />}
            {tab === 'predict' && <PatientScore model={model} />}

            <p className="text-[11px] text-gray-400 mt-4 border-t pt-2">{model.disclaimer}</p>
        </div>
    )
}

// ---------- F17 overview: validation + risk-tertile reference KM ----------

const SignatureOverview: React.FC<{ model: PrognosticModel }> = ({ model }) => {
    const kmData = buildKMChartData(model.reference_km)
    return (
        <div className="space-y-4">
            <div className="grid grid-cols-3 gap-2">
                <Stat label="Signature genes" value={String(model.genes.length)} color="text-purple-600" />
                <Stat label="Pooled C-index" value={model.pooled_c_index.toFixed(3)} color="text-indigo-600" />
                <Stat
                    label="Validation cohorts"
                    value={String(model.cohort_validations.filter((c) => c.role === 'validation').length)}
                    color="text-green-600"
                />
            </div>

            <div>
                <h5 className="text-sm font-medium text-gray-700 mb-1">Cross-cohort validation (Harrell's C-index)</h5>
                <table className="w-full text-xs border border-gray-200 rounded">
                    <thead className="bg-gray-50 text-gray-500 text-left">
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
                            <tr key={c.accession + c.role} className="border-t border-gray-100">
                                <td className="px-2 py-1 font-medium text-gray-700">{c.accession}</td>
                                <td className="px-2 py-1">
                                    <span className={c.role === 'training' ? 'text-gray-500' : 'text-indigo-600'}>
                                        {c.role}
                                    </span>
                                </td>
                                <td className="px-2 py-1 text-gray-600">{c.n_samples}</td>
                                <td className="px-2 py-1 text-gray-600">{c.n_events}</td>
                                <td className="px-2 py-1 font-medium">
                                    {Number.isFinite(c.c_index) ? c.c_index.toFixed(3) : '—'}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
                <p className="text-[11px] text-gray-400 mt-1">
                    C-index 0.5 = chance; higher = better discrimination. Trained on {model.training_accession}.
                </p>
            </div>

            {kmData.length > 0 && (
                <div>
                    <h5 className="text-sm font-medium text-gray-700 mb-1">Reference survival by risk group (training cohort)</h5>
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

// ---------- F23 single-sample scoring ----------

const PatientScore: React.FC<{ model: PrognosticModel }> = ({ model }) => {
    const [pasted, setPasted] = useState('')
    const [result, setResult] = useState<PredictResponse | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const runPredict = async (expression: Record<string, number>) => {
        setLoading(true)
        setError(null)
        try {
            const r = await predictSingleSample(model.model_id, expression)
            setResult(r)
        } catch (err) {
            const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
            setError(detail ?? 'Scoring failed.')
        } finally {
            setLoading(false)
        }
    }

    const handleDemoPatient = async () => {
        setLoading(true)
        setError(null)
        try {
            const expr = await getDemoPatient(model.model_id)
            await runPredict(expr)
        } catch {
            setError('Could not load demo patient.')
            setLoading(false)
        }
    }

    const handlePasted = () => {
        const expr = parsePastedExpression(pasted)
        if (Object.keys(expr).length === 0) {
            setError('Could not parse any "GENE value" pairs. Use one per line, e.g. "TP53 8.2".')
            return
        }
        void runPredict(expr)
    }

    return (
        <div className="space-y-3">
            <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
                <strong>Research use only.</strong> Provide one tumour's expression profile to estimate its
                <em> prognostic risk group</em> against this locked model. This does not predict response to any
                therapy. Pasted values are scored in your browser session and never stored.
            </div>

            <div className="flex flex-wrap gap-2 items-start">
                <textarea
                    value={pasted}
                    onChange={(e) => setPasted(e.target.value)}
                    rows={4}
                    placeholder={'Paste "GENE value" per line:\nTP53 8.2\nMKI67 11.4\n…'}
                    className="flex-1 min-w-[220px] text-xs font-mono border border-gray-300 rounded p-2 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <div className="flex flex-col gap-2">
                    <button
                        onClick={handlePasted}
                        disabled={loading || !pasted.trim()}
                        className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
                    >
                        {loading ? 'Scoring…' : 'Score patient'}
                    </button>
                    <button
                        onClick={handleDemoPatient}
                        disabled={loading}
                        className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 border border-gray-300 rounded hover:bg-gray-200 disabled:opacity-50"
                    >
                        Use demo patient
                    </button>
                </div>
            </div>

            {error && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-2">{error}</div>}

            {result && (
                <div className="border border-gray-200 rounded p-3 space-y-3">
                    <div className="flex items-center gap-3">
                        <span
                            className="px-3 py-1 rounded-full text-sm font-semibold text-white"
                            style={{ backgroundColor: GROUP_COLORS[result.risk_group] ?? '#6b7280' }}
                        >
                            {result.risk_group.toUpperCase()} RISK
                        </span>
                        <span className="text-sm text-gray-600">
                            {result.risk_percentile.toFixed(0)}th percentile vs reference
                        </span>
                        <span className="text-xs text-gray-400 ml-auto">
                            {result.genes_used}/{result.genes_total} signature genes matched
                        </span>
                    </div>

                    {result.predicted_survival.length > 0 && (
                        <div className="grid grid-cols-3 gap-2">
                            {result.predicted_survival.map((s) => (
                                <div key={s.horizon_label} className="text-center bg-gray-50 rounded p-2">
                                    <div className="text-lg font-bold text-gray-800">
                                        {(s.survival_probability * 100).toFixed(0)}%
                                    </div>
                                    <div className="text-xs text-gray-500">{s.horizon_label} survival</div>
                                </div>
                            ))}
                        </div>
                    )}

                    <p className="text-[11px] text-gray-400">
                        Estimated {result.risk_group}-risk group reference survival; discrimination C-index{' '}
                        {result.pooled_c_index.toFixed(3)}. Single-sample estimates are uncertain and
                        cross-platform normalization is approximate — interpret as investigational.
                    </p>
                </div>
            )}
        </div>
    )
}

// ---------- helpers ----------

const Stat: React.FC<{ label: string; value: string; color: string }> = ({ label, value, color }) => (
    <div className="text-center bg-gray-50 rounded p-2">
        <p className={`text-2xl font-bold ${color}`}>{value}</p>
        <p className="text-xs text-gray-500">{label}</p>
    </div>
)

function buildKMChartData(curves: ReferenceKMCurve[]): Array<Record<string, number>> {
    // Merge the three step curves onto a shared sorted time axis.
    const allTimes = new Set<number>()
    for (const c of curves) for (const t of c.times) allTimes.add(t)
    const sorted = Array.from(allTimes).sort((a, b) => a - b)
    if (sorted.length === 0) return []

    const stepValue = (curve: ReferenceKMCurve, time: number): number | undefined => {
        if (curve.times.length === 0) return undefined
        let val = 1.0
        for (let i = 0; i < curve.times.length; i++) {
            if (curve.times[i] <= time) val = curve.survival_probabilities[i]
            else break
        }
        return val
    }

    return sorted.map((time) => {
        const row: Record<string, number> = { time }
        for (const c of curves) {
            const v = stepValue(c, time)
            if (v !== undefined) row[c.group] = v
        }
        return row
    })
}

function parsePastedExpression(text: string): Record<string, number> {
    const out: Record<string, number> = {}
    for (const line of text.split('\n')) {
        const m = line.trim().match(/^([A-Za-z0-9_.-]+)[\s,:\t]+(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)/)
        if (m) {
            out[m[1].toUpperCase()] = parseFloat(m[2])
        }
    }
    return out
}

export default SignaturePanel
