import React, { useState } from 'react'
import { Link } from 'react-router-dom'

interface Section {
    id: string
    title: string
    content: React.ReactNode
}

const HelpPage: React.FC = () => {
    const [activeSection, setActiveSection] = useState('overview')

    const sections: Section[] = [
        {
            id: 'overview',
            title: 'Overview',
            content: (
                <div className="space-y-4">
                    <p className="text-gray-700">
                        <strong>GEO Survival Analysis</strong> finds genes whose expression level significantly
                        predicts patient survival, validated across multiple independent GEO datasets. No coding required.
                    </p>
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <p className="text-sm font-medium text-blue-800 mb-1">Free and open access</p>
                        <p className="text-sm text-blue-700">
                            This website is free and open to all users. No login required to run analyses.
                            Create an optional account to save your analysis history.
                        </p>
                    </div>
                    <h3 className="font-semibold text-gray-800 mt-4">How it works</h3>
                    <ol className="list-decimal list-inside space-y-2 text-gray-700 text-sm">
                        <li>You enter a cancer type and survival endpoint (e.g., <em>"lung adenocarcinoma overall survival"</em>)</li>
                        <li>The tool searches NCBI GEO for relevant microarray/RNA-seq expression datasets</li>
                        <li>For each dataset it maps probe IDs to gene symbols, splits patients at the expression median, and runs Cox proportional-hazards regression and log-rank test</li>
                        <li>Genes significant (p &lt; 0.05) in at least 2 independent datasets are returned, ranked by cross-cohort consistency</li>
                        <li>Results include Kaplan–Meier curves, forest plots, volcano plot, and a downloadable export</li>
                    </ol>
                    <h3 className="font-semibold text-gray-800 mt-4">Comparison with existing tools</h3>
                    <div className="overflow-x-auto">
                        <table className="text-sm w-full border-collapse">
                            <thead>
                                <tr className="bg-gray-100">
                                    <th className="text-left px-3 py-2 border border-gray-200">Tool</th>
                                    <th className="text-left px-3 py-2 border border-gray-200">Data source</th>
                                    <th className="text-center px-3 py-2 border border-gray-200">Cross-cohort meta-analysis</th>
                                    <th className="text-center px-3 py-2 border border-gray-200">Natural language input</th>
                                </tr>
                            </thead>
                            <tbody>
                                {[
                                    { tool: 'KMplot', source: 'TCGA + curated', meta: false, nl: false },
                                    { tool: 'GEPIA2', source: 'TCGA + GTEx', meta: false, nl: false },
                                    { tool: 'OncoLnc', source: 'TCGA only', meta: false, nl: false },
                                    { tool: 'GEO Survival Analysis', source: 'All of GEO', meta: true, nl: true },
                                ].map((row) => (
                                    <tr key={row.tool} className={row.tool === 'GEO Survival Analysis' ? 'bg-indigo-50 font-medium' : ''}>
                                        <td className="px-3 py-2 border border-gray-200">{row.tool}</td>
                                        <td className="px-3 py-2 border border-gray-200">{row.source}</td>
                                        <td className="text-center px-3 py-2 border border-gray-200">{row.meta ? '✓' : '✗'}</td>
                                        <td className="text-center px-3 py-2 border border-gray-200">{row.nl ? '✓' : '✗'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            ),
        },
        {
            id: 'quickstart',
            title: 'Quick start',
            content: (
                <div className="space-y-4 text-sm text-gray-700">
                    <h3 className="font-semibold text-gray-800 text-base">Running your first analysis</h3>
                    <div className="space-y-3">
                        <div className="flex gap-3">
                            <div className="w-7 h-7 rounded-full bg-indigo-600 text-white flex items-center justify-center flex-shrink-0 text-sm font-bold">1</div>
                            <div>
                                <p className="font-medium">Go to the <Link to="/" className="text-indigo-600 underline">home page</Link></p>
                                <p className="text-gray-500">Click one of the example buttons — e.g., <strong>"Lung adenocarcinoma OS"</strong> — to launch a pre-loaded analysis immediately. Results typically appear within 2–5 minutes.</p>
                            </div>
                        </div>
                        <div className="flex gap-3">
                            <div className="w-7 h-7 rounded-full bg-indigo-600 text-white flex items-center justify-center flex-shrink-0 text-sm font-bold">2</div>
                            <div>
                                <p className="font-medium">Or type a custom query</p>
                                <p className="text-gray-500">Use the text box at the bottom. Good queries include a cancer type and a survival endpoint, e.g.:<br />
                                    <code className="bg-gray-100 px-1 rounded">colorectal cancer overall survival</code><br />
                                    <code className="bg-gray-100 px-1 rounded">glioblastoma recurrence-free survival</code>
                                </p>
                            </div>
                        </div>
                        <div className="flex gap-3">
                            <div className="w-7 h-7 rounded-full bg-indigo-600 text-white flex items-center justify-center flex-shrink-0 text-sm font-bold">3</div>
                            <div>
                                <p className="font-medium">Watch real-time progress</p>
                                <p className="text-gray-500">A progress bar shows each stage: searching GEO, downloading datasets, mapping probes, running Cox regression.</p>
                            </div>
                        </div>
                        <div className="flex gap-3">
                            <div className="w-7 h-7 rounded-full bg-indigo-600 text-white flex items-center justify-center flex-shrink-0 text-sm font-bold">4</div>
                            <div>
                                <p className="font-medium">Explore results</p>
                                <p className="text-gray-500">The results panel shows a ranked gene table, interactive Kaplan–Meier curves, forest plots, and a volcano plot. Download gene table as CSV or all plots as a ZIP publication package.</p>
                            </div>
                        </div>
                    </div>

                    <h3 className="font-semibold text-gray-800 text-base mt-6">Sample output — lung adenocarcinoma OS</h3>
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 font-mono text-xs overflow-x-auto">
                        <p className="text-gray-500 mb-2"># Top genes (10 datasets analysed, 8 with survival data)</p>
                        <table className="w-full">
                            <thead>
                                <tr className="text-left text-gray-600">
                                    <th className="pr-4">Gene</th>
                                    <th className="pr-4">Datasets (sig)</th>
                                    <th className="pr-4">Avg HR</th>
                                    <th className="pr-4">Avg p (Cox)</th>
                                    <th>Direction</th>
                                </tr>
                            </thead>
                            <tbody className="text-gray-800">
                                {[
                                    ['SFTPC', '7/8', '0.41', '0.003', 'High = protective'],
                                    ['SPP1', '6/8', '2.31', '0.007', 'High = risk'],
                                    ['CXCL13', '5/8', '0.55', '0.012', 'High = protective'],
                                    ['MMP1', '5/8', '1.87', '0.014', 'High = risk'],
                                    ['VEGFA', '4/8', '1.64', '0.021', 'High = risk'],
                                ].map(([gene, ds, hr, p, dir]) => (
                                    <tr key={gene}>
                                        <td className="pr-4 text-indigo-700 font-bold">{gene}</td>
                                        <td className="pr-4">{ds}</td>
                                        <td className="pr-4">{hr}</td>
                                        <td className="pr-4">{p}</td>
                                        <td>{dir}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    <p className="text-xs text-gray-500">
                        SFTPC is a known alveolar marker whose high expression is associated with better prognosis in lung adenocarcinoma — consistent with literature. SPP1 (osteopontin) is a well-characterised oncogenic driver. These results illustrate the tool's ability to recover biologically interpretable signals from independent datasets.
                    </p>
                </div>
            ),
        },
        {
            id: 'results',
            title: 'Interpreting results',
            content: (
                <div className="space-y-4 text-sm text-gray-700">
                    <h3 className="font-semibold text-gray-800 text-base">Gene ranking table</h3>
                    <ul className="space-y-2">
                        <li><strong>Datasets (sig):</strong> Number of datasets where the gene was significant (p &lt; 0.05) out of datasets tested. A gene significant in 8/10 independent cohorts provides much stronger evidence than one from a single study.</li>
                        <li><strong>Hazard Ratio (HR):</strong> From Cox regression. HR &gt; 1 means high expression associates with worse survival ("high-risk"); HR &lt; 1 means high expression associates with better survival ("protective").</li>
                        <li><strong>p-value:</strong> Average Cox log-likelihood p-value across significant datasets.</li>
                        <li><strong>Risk direction consistency:</strong> Proportion of datasets where the risk direction agrees. 1.0 = perfectly consistent across cohorts.</li>
                    </ul>

                    <h3 className="font-semibold text-gray-800 text-base mt-4">Kaplan–Meier curves</h3>
                    <p>Patients are split at the per-dataset median expression of the selected gene into "high" and "low" groups. The y-axis shows survival probability; the x-axis shows time (days). Shaded bands are 95% confidence intervals. A large separation between curves indicates strong prognostic effect.</p>

                    <h3 className="font-semibold text-gray-800 text-base mt-4">Forest plot</h3>
                    <p>Each row is one GEO dataset. The point estimate shows the HR; error bars show 95% CI. The diamond at the bottom is the pooled random-effects estimate. I² (heterogeneity) &gt; 50% suggests between-study differences that may reflect biological or technical variability.</p>

                    <h3 className="font-semibold text-gray-800 text-base mt-4">Volcano plot</h3>
                    <p>All genes are plotted as log₂(average HR) vs −log₁₀(average p-value). Genes in the upper-right are high-risk with strong significance; upper-left are protective with strong significance. Click any dot to view that gene's KM curve and forest plot.</p>

                    <h3 className="font-semibold text-gray-800 text-base mt-4">Statistical methods</h3>
                    <ul className="space-y-1">
                        <li><strong>Cox proportional hazards:</strong> <code className="bg-gray-100 px-1 rounded">lifelines.CoxPHFitter</code> with expression group (high/low, split at median) as covariate.</li>
                        <li><strong>Log-rank test:</strong> Independent confirmation of group separation.</li>
                        <li><strong>Cross-cohort ranking:</strong> Genes ranked by (1) number of significant datasets, then (2) average p-value.</li>
                        <li><strong>Heterogeneity:</strong> Cochran Q statistic and I² computed for forest plots.</li>
                    </ul>
                </div>
            ),
        },
        {
            id: 'advanced',
            title: 'Advanced features',
            content: (
                <div className="space-y-4 text-sm text-gray-700">
                    <h3 className="font-semibold text-gray-800 text-base">Analysis settings</h3>
                    <p>Click the gear icon in the chat header to open the settings panel:</p>
                    <ul className="space-y-2">
                        <li><strong>Datasets:</strong> Number of GEO datasets to retrieve (10–1000). More datasets = broader coverage but longer runtime.</li>
                        <li><strong>Ranking multiplier:</strong> Weight applied to cross-cohort consistency when ranking genes. Higher values prioritise genes consistent across more datasets.</li>
                        <li><strong>Organism:</strong> Filter by Human, Mouse, or Any.</li>
                        <li><strong>Cancer genes only:</strong> Restrict analysis to ~600 COSMIC cancer driver genes.</li>
                    </ul>

                    <h3 className="font-semibold text-gray-800 text-base mt-4">Gene batch mode</h3>
                    <p>Paste up to 500 gene symbols (one per line or comma-separated) into the "Candidate Genes" text area. The analysis will be restricted to those genes only — useful when testing a pre-defined gene signature or pathway list.</p>

                    <h3 className="font-semibold text-gray-800 text-base mt-4">Shareable permalinks</h3>
                    <p>Every saved result has a public URL at <code className="bg-gray-100 px-1 rounded">/results/&lt;id&gt;</code> that can be shared without requiring the recipient to log in.</p>

                    <h3 className="font-semibold text-gray-800 text-base mt-4">Publication export</h3>
                    <p>The "Export" button downloads a ZIP containing: <code>genes.csv</code> (full gene table), per-dataset KM curves as PNG, and a pre-written Methods paragraph suitable for inclusion in a manuscript.</p>

                    <h3 className="font-semibold text-gray-800 text-base mt-4">AI chat assistant</h3>
                    <p>The chat interface can answer follow-up questions about your results, explain individual genes' biological roles, suggest improved queries, and compare findings across analyses.</p>
                </div>
            ),
        },
        {
            id: 'faq',
            title: 'FAQ',
            content: (
                <div className="space-y-4 text-sm text-gray-700">
                    {[
                        {
                            q: 'Do I need an account?',
                            a: 'No. All analysis features are available without registration. Create an optional account to save analysis history and access it across sessions.',
                        },
                        {
                            q: 'How long does an analysis take?',
                            a: 'Typically 2–5 minutes for 10 datasets. 50 datasets takes 10–20 minutes. Progress is shown in real time.',
                        },
                        {
                            q: 'What data sources are used?',
                            a: 'All data comes from NCBI GEO (Gene Expression Omnibus), a public repository of gene expression studies. The tool queries the GEO API for datasets matching your query, then downloads the expression matrices and clinical metadata from NCBI.',
                        },
                        {
                            q: 'What expression platforms are supported?',
                            a: 'Microarray platforms (Affymetrix, Agilent, Illumina) and RNA-seq count matrices available through GEO. The tool automatically maps probe IDs to gene symbols using GPL platform annotation files.',
                        },
                        {
                            q: 'How is the expression split performed?',
                            a: 'Patients are split at the per-dataset median expression value for each gene. This is a standard approach. The split is computed independently for each dataset to account for study-specific expression distributions.',
                        },
                        {
                            q: 'Can I use this for non-cancer data?',
                            a: 'Yes. Any GEO dataset with survival/time-to-event data works. Try queries like "Alzheimer disease survival", "heart failure overall survival", or "sepsis 28-day mortality".',
                        },
                        {
                            q: 'Is the source code available?',
                            a: 'Yes. The full source code is on GitHub and the tool is MIT licensed.',
                        },
                    ].map(({ q, a }) => (
                        <div key={q} className="border-b border-gray-100 pb-4">
                            <p className="font-medium text-gray-800">{q}</p>
                            <p className="text-gray-600 mt-1">{a}</p>
                        </div>
                    ))}
                </div>
            ),
        },
    ]

    return (
        <div className="h-full overflow-y-auto bg-gray-50">
            <div className="max-w-5xl mx-auto px-4 py-8">
                <div className="mb-6">
                    <h1 className="text-2xl font-bold text-gray-900">Help & Documentation</h1>
                    <p className="text-gray-500 text-sm mt-1">
                        GEO Survival Analysis — cross-cohort biomarker discovery from NCBI GEO
                    </p>
                </div>

                <div className="flex gap-6">
                    {/* Sidebar navigation */}
                    <nav className="w-44 flex-shrink-0">
                        <ul className="space-y-1 sticky top-4">
                            {sections.map((s) => (
                                <li key={s.id}>
                                    <button
                                        onClick={() => setActiveSection(s.id)}
                                        className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                                            activeSection === s.id
                                                ? 'bg-indigo-100 text-indigo-700 font-medium'
                                                : 'text-gray-600 hover:bg-gray-100'
                                        }`}
                                    >
                                        {s.title}
                                    </button>
                                </li>
                            ))}
                        </ul>
                    </nav>

                    {/* Content */}
                    <div className="flex-1 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                        {sections.find((s) => s.id === activeSection)?.content}
                    </div>
                </div>
            </div>
        </div>
    )
}

export default HelpPage
