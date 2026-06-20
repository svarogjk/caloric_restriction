import React from 'react'
import { PredictResponse } from '../../services/api'

interface PatientReportProps {
    cancerLabel: string
    modelId: string
    modelIsDemo: boolean
    prediction: PredictResponse
}

/**
 * One-page printable single-patient predictive report (Oncologist Mode variant
 * of F22). Hidden on screen via `.print-report`; shown only when printing.
 * Carries a prominent research-use-only / advisory banner.
 */
const PatientReport: React.FC<PatientReportProps> = ({ cancerLabel, modelId, modelIsDemo, prediction: result }) => {
    const generated = new Date().toLocaleString()
    const cell: React.CSSProperties = { border: '1px solid #999', padding: '3px 6px', fontSize: '9pt' }

    return (
        <div className="print-report">
            <div style={{ borderBottom: '2px solid #000', paddingBottom: 8, marginBottom: 12 }}>
                <h1 style={{ fontSize: '18pt', fontWeight: 700, margin: 0 }}>
                    Patient Predictive Report — {cancerLabel}
                </h1>
                <p style={{ margin: '2px 0', fontSize: '10pt' }}>
                    GEO Survival Analysis — combined clinical + expression risk model with advisory treatment context
                    {modelIsDemo ? ' (DEMO model — synthetic data)' : ''}
                </p>
            </div>

            <div style={{ border: '1.5px solid #000', padding: 8, marginBottom: 12, fontSize: '9pt', fontWeight: 600 }}>
                RESEARCH USE ONLY — NOT FOR CLINICAL DECISION-MAKING. This predicts an outcome risk group
                from tumour gene expression and clinical covariates, and lists treatments to CONSIDER and
                discuss, grounded in documented evidence and historical cohort outcomes. It is advisory and
                hypothesis-generating — not a prescription, not a guarantee of response, and not a clinical
                decision-making device. Single-sample estimates are uncertain; cross-platform normalization is approximate.
            </div>

            <table style={{ borderCollapse: 'collapse', marginBottom: 12 }}>
                <tbody>
                    <tr>
                        <td style={{ ...cell, fontWeight: 700 }}>Assigned risk group</td>
                        <td style={cell}>{result.risk_group.toUpperCase()}</td>
                        <td style={{ ...cell, fontWeight: 700 }}>Risk percentile</td>
                        <td style={cell}>{result.risk_percentile.toFixed(0)}th</td>
                    </tr>
                    <tr>
                        <td style={{ ...cell, fontWeight: 700 }}>Scored on</td>
                        <td style={cell}>{result.scored_on}</td>
                        <td style={{ ...cell, fontWeight: 700 }}>Signature genes matched</td>
                        <td style={cell}>{result.genes_used}/{result.genes_total}</td>
                    </tr>
                    <tr>
                        <td style={{ ...cell, fontWeight: 700 }}>Model C-index (combined)</td>
                        <td style={cell}>{(result.c_index_combined ?? result.pooled_c_index).toFixed(3)}</td>
                        <td style={{ ...cell, fontWeight: 700 }}>Δ over expression alone</td>
                        <td style={cell}>{result.delta_c_index != null ? result.delta_c_index.toFixed(3) : '—'}</td>
                    </tr>
                </tbody>
            </table>

            {result.predicted_survival.length > 0 && (
                <>
                    <h2 style={{ fontSize: '11pt', fontWeight: 700, margin: '0 0 4px' }}>
                        Predicted reference survival ({result.risk_group}-risk group)
                    </h2>
                    <table style={{ borderCollapse: 'collapse', marginBottom: 12 }}>
                        <tbody>
                            <tr>
                                {result.predicted_survival.map((s) => (
                                    <td key={s.horizon_label} style={{ ...cell, fontWeight: 700 }}>{s.horizon_label}</td>
                                ))}
                            </tr>
                            <tr>
                                {result.predicted_survival.map((s) => (
                                    <td key={s.horizon_label} style={cell}>
                                        {(s.survival_probability * 100).toFixed(0)}%
                                    </td>
                                ))}
                            </tr>
                        </tbody>
                    </table>
                </>
            )}

            {result.contributions.length > 0 && (
                <>
                    <h2 style={{ fontSize: '11pt', fontWeight: 700, margin: '0 0 4px' }}>Risk-score contributions</h2>
                    <table style={{ borderCollapse: 'collapse', marginBottom: 12 }}>
                        <tbody>
                            {result.contributions.map((c, i) => (
                                <tr key={i}>
                                    <td style={cell}>{c.label}</td>
                                    <td style={cell}>{c.contribution >= 0 ? '+' : ''}{c.contribution.toFixed(3)}</td>
                                    <td style={cell}>{c.contribution >= 0 ? 'increases risk' : 'protective'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </>
            )}

            <p style={{ fontSize: '8pt', color: '#333', marginTop: 16 }}>
                Generated {generated} · Model {modelId}. Predictive, advisory — research use only.
            </p>
        </div>
    )
}

export default PatientReport
