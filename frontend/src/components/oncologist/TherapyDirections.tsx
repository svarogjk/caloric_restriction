import React, { useState } from 'react'
import { getTherapyRationale, TherapyRationaleResponse } from '../../services/api'

interface TherapyDirectionsProps {
    modelId: string
    riskGroup?: string | null
    genes?: string[]
}

/**
 * Grounded "therapeutic directions to discuss" (Oncologist Mode). On demand,
 * the AI writes hypotheses over REAL CIViC/DGIdb evidence for the risk-driving
 * genes — never a treatment recommendation. The cited associations are always
 * shown alongside the prose, and a prominent banner keeps the framing honest.
 */
const TherapyDirections: React.FC<TherapyDirectionsProps> = ({ modelId, riskGroup, genes }) => {
    const [data, setData] = useState<TherapyRationaleResponse | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const generate = async () => {
        setLoading(true)
        setError(null)
        try {
            const r = await getTherapyRationale({ modelId, riskGroup, genes })
            setData(r)
        } catch (err) {
            const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
            setError(detail ?? 'Could not generate therapeutic directions.')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="border border-purple-200 rounded-lg p-4 bg-purple-50/40">
            <div className="flex items-center justify-between gap-3 mb-2">
                <h3 className="font-semibold text-gray-800">Therapeutic directions to discuss</h3>
                <button
                    onClick={generate}
                    disabled={loading}
                    className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
                >
                    {loading ? 'Generating…' : data ? 'Regenerate' : 'Generate'}
                </button>
            </div>

            <div className="text-xs font-semibold text-purple-900 bg-purple-100 border border-purple-200 rounded p-2 mb-3">
                Hypothesis-generating only — NOT a treatment recommendation. These are documented
                biomarker associations from public knowledge bases for tumour-board discussion.
                Prognostic, research use only; this tool does not predict response to any therapy.
            </div>

            {error && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-2">{error}</div>
            )}

            {!data && !loading && !error && (
                <p className="text-sm text-gray-500">
                    Surface documented CIViC/DGIdb drug–biomarker associations for this patient's
                    risk-driving genes, with an AI-written summary framed as research hypotheses.
                </p>
            )}

            {data && (
                <div className="space-y-3">
                    <p className="text-sm text-gray-700 whitespace-pre-line">{data.rationale}</p>

                    {data.evidence.length > 0 && (
                        <div className="overflow-x-auto">
                            <table className="w-full text-xs border-collapse">
                                <thead>
                                    <tr className="text-left text-gray-500 border-b border-gray-200">
                                        <th className="py-1 pr-2">Gene</th>
                                        <th className="py-1 pr-2">Drug / therapy</th>
                                        <th className="py-1 pr-2">Evidence</th>
                                        <th className="py-1 pr-2">Source</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.evidence.map((e, i) => (
                                        <tr key={i} className="border-b border-gray-100">
                                            <td className="py-1 pr-2 font-medium text-gray-800">{e.gene}</td>
                                            <td className="py-1 pr-2">{e.drug}</td>
                                            <td className="py-1 pr-2 text-gray-600">
                                                {e.source === 'CIViC'
                                                    ? [e.evidence_type, e.significance, e.evidence_level && `level ${e.evidence_level}`]
                                                          .filter(Boolean)
                                                          .join(' · ')
                                                    : [e.interaction_type, e.approved ? 'approved' : 'investigational']
                                                          .filter(Boolean)
                                                          .join(' · ')}
                                            </td>
                                            <td className="py-1 pr-2">
                                                {e.url ? (
                                                    <a
                                                        href={e.url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="text-indigo-600 hover:underline"
                                                    >
                                                        {e.source}
                                                    </a>
                                                ) : (
                                                    <span className="text-gray-500">{e.source}{e.source_db ? ` (${e.source_db})` : ''}</span>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

export default TherapyDirections
