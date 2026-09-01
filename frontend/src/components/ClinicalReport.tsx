import React from 'react'
import { AnalysisResult } from '../store/chatSlice'

interface ClinicalReportProps {
    results: AnalysisResult
}

/**
 * F22 — one-page printable clinical evidence report. Always rendered but hidden
 * on screen (`.print-report`), shown only when the browser prints. Pure CSS
 * `@media print`, no backend dependency. Carries a prominent RUO disclaimer.
 */
const ClinicalReport: React.FC<ClinicalReportProps> = ({ results }) => {
    const topGenes = [...results.common_genes]
        .sort((a, b) => b.n_datasets - a.n_datasets || a.avg_cox_p_value - b.avg_cox_p_value)
        .slice(0, 15)

    const generated = new Date().toLocaleString()

    return (
        <div className="print-report" data-theme="light">
            <div style={{ borderBottom: '2px solid #000', paddingBottom: 8, marginBottom: 12 }}>
                <h1 style={{ fontSize: '18pt', fontWeight: 700, margin: 0 }}>
                    Predictive Evidence Report
                </h1>
                <p style={{ margin: '2px 0', fontSize: '10pt' }}>
                    GEO Survival Analysis — cross-cohort biomarker evidence
                </p>
            </div>

            {/* RUO banner */}
            <div
                style={{
                    border: '1.5px solid #000',
                    padding: 8,
                    marginBottom: 12,
                    fontSize: '9pt',
                    fontWeight: 600,
                }}
            >
                RESEARCH USE ONLY — NOT FOR CLINICAL DECISION-MAKING. This report describes gene-expression
                biomarker evidence aggregated from public GEO cohorts, including predictive (treatment-effect-
                modifying) signal where treatment data was available. It is advisory and hypothesis-generating —
                not a prescription, and must not be used on its own to direct patient treatment.
            </div>

            <table style={{ width: '100%', fontSize: '10pt', marginBottom: 12 }}>
                <tbody>
                    <tr>
                        <td style={{ fontWeight: 600, width: '30%' }}>Query</td>
                        <td>{results.query}</td>
                    </tr>
                    <tr>
                        <td style={{ fontWeight: 600 }}>Datasets analysed</td>
                        <td>{results.n_datasets_analyzed}</td>
                    </tr>
                    <tr>
                        <td style={{ fontWeight: 600 }}>Cohorts with survival data</td>
                        <td>{results.n_datasets_with_survival}</td>
                    </tr>
                    <tr>
                        <td style={{ fontWeight: 600 }}>Biomarker genes identified</td>
                        <td>{results.common_genes.length}</td>
                    </tr>
                    <tr>
                        <td style={{ fontWeight: 600 }}>Report generated</td>
                        <td>{generated}</td>
                    </tr>
                </tbody>
            </table>

            <h2 style={{ fontSize: '12pt', fontWeight: 700, margin: '8px 0 4px' }}>
                Top biomarker genes
            </h2>
            <table
                style={{
                    width: '100%',
                    fontSize: '9.5pt',
                    borderCollapse: 'collapse',
                }}
            >
                <thead>
                    <tr style={{ borderBottom: '1px solid #000', textAlign: 'left' }}>
                        <th style={{ padding: '2px 4px' }}>Gene</th>
                        <th style={{ padding: '2px 4px' }}>Avg HR</th>
                        <th style={{ padding: '2px 4px' }}>Avg p</th>
                        <th style={{ padding: '2px 4px' }}>Cohorts</th>
                        <th style={{ padding: '2px 4px' }}>Direction</th>
                        <th style={{ padding: '2px 4px' }}>Consistency</th>
                    </tr>
                </thead>
                <tbody>
                    {topGenes.map((g) => (
                        <tr key={g.gene_id} style={{ borderBottom: '0.5px solid #ccc' }}>
                            <td style={{ padding: '2px 4px', fontWeight: 600 }}>
                                {g.gene_symbol || g.gene_id}
                            </td>
                            <td style={{ padding: '2px 4px' }}>{g.avg_hazard_ratio.toFixed(2)}</td>
                            <td style={{ padding: '2px 4px' }}>
                                {g.avg_cox_p_value < 0.001
                                    ? g.avg_cox_p_value.toExponential(2)
                                    : g.avg_cox_p_value.toFixed(4)}
                            </td>
                            <td style={{ padding: '2px 4px' }}>{g.n_datasets}</td>
                            <td style={{ padding: '2px 4px' }}>
                                {g.predominant_risk === 'high_risk' ? 'Risk (HR>1)' : 'Protective (HR<1)'}
                            </td>
                            <td style={{ padding: '2px 4px' }}>
                                {(g.risk_direction_consistency * 100).toFixed(0)}%
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>

            <h2 style={{ fontSize: '11pt', fontWeight: 700, margin: '12px 0 4px' }}>
                Interpretation guide
            </h2>
            <p style={{ fontSize: '9.5pt', margin: '2px 0' }}>
                Hazard ratio (HR) &gt; 1: higher expression is associated with shorter survival (worse
                outcome). HR &lt; 1: higher expression is associated with longer survival (better outcome).
                Genes significant across more independent cohorts carry stronger evidence. A predictive
                (treatment-effect-modifying) biomarker is one whose HR differs by treatment arm.
            </p>

            <div
                style={{
                    marginTop: 16,
                    paddingTop: 8,
                    borderTop: '1px solid #000',
                    fontSize: '8pt',
                    color: '#333',
                }}
            >
                Generated by GEO Survival Analysis. Predictive biomarker evidence — advisory, research-use-only.
                Methods and per-cohort statistics are available in the publication export package.
                {results.result_id && <> Result ID: {results.result_id}.</>}
            </div>
        </div>
    )
}

export default ClinicalReport
