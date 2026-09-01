import React from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { GeneSurvival } from '../store/chatSlice'
import { ForestPlot } from './ForestPlot'

interface KaplanMeierPlotProps {
  gene: GeneSurvival
  onClose: () => void
}

const DATASET_COLORS = [
  '#ef4444', '#3b82f6', '#22c55e', '#f59e0b',
  '#8b5cf6', '#ec4899', '#14b8a6', '#f97316',
]

/**
 * Kaplan-Meier survival curve visualization with per-dataset meta-analysis support
 * Shows all KM curves simultaneously, with toggles to hide individual datasets
 */
const KaplanMeierPlot: React.FC<KaplanMeierPlotProps> = ({ gene, onClose }) => {
  // Get datasets that have KM curve data
  const displayDatasets = React.useMemo(() => {
    if (!gene.per_dataset_results || gene.per_dataset_results.length === 0) {
      return []
    }
    return gene.per_dataset_results.filter(
      ds => ds.km_curve_high && ds.km_curve_low
    )
  }, [gene.per_dataset_results])

  // All datasets visible by default
  const [visibleDatasets, setVisibleDatasets] = React.useState<Set<string>>(() =>
    new Set(displayDatasets.map(ds => ds.dataset_id))
  )

  // Tab selection: 'km' | 'forest'
  type PlotTab = 'km' | 'forest'
  const [activeTab, setActiveTab] = React.useState<PlotTab>('km')

  // Forest plot: datasets that have valid HR and CI data (need at least 2)
  const forestDatasets = React.useMemo(() => {
    if (!gene.per_dataset_results) return []
    return gene.per_dataset_results.filter(
      ds =>
        Number.isFinite(ds.hazard_ratio) &&
        Number.isFinite(ds.hazard_ratio_ci_lower) &&
        Number.isFinite(ds.hazard_ratio_ci_upper)
    )
  }, [gene.per_dataset_results])

  const showForestTab = forestDatasets.length >= 2

  const toggleDataset = (datasetId: string) => {
    setVisibleDatasets(prev => {
      const next = new Set(prev)
      if (next.has(datasetId)) {
        next.delete(datasetId)
      } else {
        next.add(datasetId)
      }
      return next
    })
  }

  // Build combined chart data for all visible datasets
  const allKmChartData = React.useMemo(() => {
    const visible = displayDatasets.filter(ds => visibleDatasets.has(ds.dataset_id))
    if (visible.length === 0) return null

    const allTimes = [...new Set(
      visible.flatMap(ds => [...ds.km_curve_high!.times, ...ds.km_curve_low!.times])
    )].sort((a, b) => a - b)

    return allTimes.map(time => {
      const row: Record<string, number> = { time }
      visible.forEach(ds => {
        const high = ds.km_curve_high!
        const low = ds.km_curve_low!

        const highIdx = high.times.findIndex((_t, i) =>
          i === high.times.length - 1 || high.times[i + 1] > time
        )
        const lowIdx = low.times.findIndex((_t, i) =>
          i === low.times.length - 1 || low.times[i + 1] > time
        )

        const safeHighIdx = Math.max(0, highIdx)
        const safeLowIdx = Math.max(0, lowIdx)

        row[`${ds.dataset_id}_high`] = high.survival_probabilities[safeHighIdx] * 100
        row[`${ds.dataset_id}_low`] = low.survival_probabilities[safeLowIdx] * 100

        if (high.ci_lower && high.ci_lower.length > 0) {
          row[`${ds.dataset_id}_high_ci_lower`] = high.ci_lower[safeHighIdx] * 100
        }
        if (high.ci_upper && high.ci_upper.length > 0) {
          row[`${ds.dataset_id}_high_ci_upper`] = high.ci_upper[safeHighIdx] * 100
        }
        if (low.ci_lower && low.ci_lower.length > 0) {
          row[`${ds.dataset_id}_low_ci_lower`] = low.ci_lower[safeLowIdx] * 100
        }
        if (low.ci_upper && low.ci_upper.length > 0) {
          row[`${ds.dataset_id}_low_ci_upper`] = low.ci_upper[safeLowIdx] * 100
        }
      })
      return row
    })
  }, [displayDatasets, visibleDatasets])

  const visibleList = displayDatasets.filter(ds => visibleDatasets.has(ds.dataset_id))

  const CustomTooltip: React.FC<any> = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-surface p-3 border border-border-strong rounded shadow-lg max-w-xs">
          <p className="font-semibold text-fg-strong mb-1">Time: {label} months</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ color: entry.color }} className="text-xs">
              {entry.name}: {entry.value.toFixed(1)}%
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  const getRiskInterpretation = () => {
    const hr = gene.avg_hazard_ratio
    if (hr > 2) {
      return { text: 'Strong association with poor survival', color: 'text-danger', bgColor: 'bg-danger-soft' }
    } else if (hr > 1.5) {
      return { text: 'Moderate association with poor survival', color: 'text-warn', bgColor: 'bg-warn-soft' }
    } else if (hr > 1) {
      return { text: 'Slight association with poor survival', color: 'text-warn', bgColor: 'bg-warn-soft' }
    } else if (hr > 0.67) {
      return { text: 'Slight association with better survival', color: 'text-ok', bgColor: 'bg-ok-soft' }
    } else if (hr > 0.5) {
      return { text: 'Moderate association with better survival', color: 'text-ok', bgColor: 'bg-ok-soft' }
    } else {
      return { text: 'Strong association with better survival', color: 'text-ok', bgColor: 'bg-ok-soft' }
    }
  }

  const interpretation = getRiskInterpretation()

  // F04: KM CSV export
  const exportKMCSV = () => {
    if (!allKmChartData || allKmChartData.length === 0) return
    const visibleIds = visibleList.map(ds => ds.dataset_id)
    const headers = ['Time', ...visibleIds.flatMap(id => [`${id}_High`, `${id}_Low`])]
    const rows = allKmChartData.map(row => [
      row.time,
      ...visibleIds.flatMap(id => [
        row[`${id}_high`] != null ? (row[`${id}_high`] as number).toFixed(2) : '',
        row[`${id}_low`] != null ? (row[`${id}_low`] as number).toFixed(2) : '',
      ])
    ])
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `km_curves_${gene.gene_symbol || gene.gene_id}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-surface rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border">
          <div>
            <h2 className="text-2xl font-bold text-fg-strong">
              Kaplan-Meier Survival Curves
            </h2>
            <p className="text-fg-muted mt-1">
              {gene.gene_symbol || gene.gene_id}
              {gene.gene_symbol && gene.gene_symbol !== gene.gene_id && (
                <span className="text-fg-faint ml-2">({gene.gene_id})</span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {allKmChartData && allKmChartData.length > 0 && (
              <button
                onClick={exportKMCSV}
                className="text-xs px-3 py-1.5 border border-border-strong rounded hover:bg-surface-sunken text-fg-muted"
              >
                Export CSV
              </button>
            )}
            <button
              onClick={onClose}
              className="text-fg-faint hover:text-fg-muted transition p-2 hover:bg-surface-sunken rounded-full"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Stats summary */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-surface-sunken p-4 rounded-lg">
              <p className="text-fg-muted text-sm font-medium">Avg Hazard Ratio</p>
              <p className={`text-2xl font-bold ${gene.avg_hazard_ratio > 1 ? 'text-danger' : 'text-accent-fg'}`}>
                {gene.avg_hazard_ratio.toFixed(2)}
              </p>
            </div>
            <div className="bg-surface-sunken p-4 rounded-lg">
              <p className="text-fg-muted text-sm font-medium">Avg P-value</p>
              <p className="text-2xl font-bold text-fg-strong">
                {gene.avg_log_rank_p_value < 0.001
                  ? gene.avg_log_rank_p_value.toExponential(2)
                  : gene.avg_log_rank_p_value.toFixed(4)}
              </p>
            </div>
            <div className="bg-surface-sunken p-4 rounded-lg">
              <p className="text-fg-muted text-sm font-medium">Datasets</p>
              <p className="text-2xl font-bold text-alt">{gene.n_datasets}</p>
            </div>
            <div className="bg-surface-sunken p-4 rounded-lg">
              <p className="text-fg-muted text-sm font-medium">Direction Consistency</p>
              <p className="text-2xl font-bold text-ok">
                {(gene.risk_direction_consistency * 100).toFixed(0)}%
              </p>
            </div>
          </div>

          {/* Interpretation */}
          <div className={`${interpretation.bgColor} border rounded-lg p-4 mb-6`}>
            <p className={`${interpretation.color} font-medium`}>{interpretation.text}</p>
            <p className="text-fg-muted text-sm mt-1">
              {gene.predominant_risk === 'high_risk'
                ? 'Higher expression of this gene is associated with worse survival outcomes.'
                : 'Higher expression of this gene is associated with better survival outcomes.'}
            </p>
          </div>

          {/* Tab toggle: KM Curves | Forest Plot */}
          {showForestTab && (
            <div className="flex border-b border-border mb-4">
              <button
                onClick={() => setActiveTab('km')}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                  activeTab === 'km'
                    ? 'border-accent text-accent-fg'
                    : 'border-transparent text-fg-muted hover:text-fg hover:border-border-strong'
                }`}
              >
                KM Curves
              </button>
              <button
                onClick={() => setActiveTab('forest')}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                  activeTab === 'forest'
                    ? 'border-accent text-accent-fg'
                    : 'border-transparent text-fg-muted hover:text-fg hover:border-border-strong'
                }`}
              >
                Forest Plot
              </button>
            </div>
          )}

          {/* Forest Plot panel */}
          {activeTab === 'forest' && showForestTab ? (
            <ForestPlot
              geneName={gene.gene_symbol || gene.gene_id}
              datasets={forestDatasets.map(ds => ({
                dataset_id: ds.dataset_id,
                dataset_title: ds.dataset_title,
                hazard_ratio: ds.hazard_ratio,
                hazard_ratio_ci_lower: ds.hazard_ratio_ci_lower,
                hazard_ratio_ci_upper: ds.hazard_ratio_ci_upper,
                n_samples: ds.n_samples,
                cox_p_value: ds.cox_p_value,
              }))}
              pooledHR={gene.avg_hazard_ratio}
              heterogeneityStats={gene.heterogeneity_stats}
            />
          ) : (
            <>
              {/* Dataset visibility toggles (KM tab only) */}
              {displayDatasets.length > 0 && (
                <div className="mb-4">
                  <label className="block text-sm font-medium text-fg mb-2">
                    Toggle datasets (solid = high expression, dashed = low expression):
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {displayDatasets.map((ds, idx) => {
                      const color = DATASET_COLORS[idx % DATASET_COLORS.length]
                      const isVisible = visibleDatasets.has(ds.dataset_id)
                      return (
                        <button
                          key={ds.dataset_id}
                          onClick={() => toggleDataset(ds.dataset_id)}
                          style={{
                            borderColor: color,
                            backgroundColor: isVisible ? color : 'transparent',
                            color: isVisible ? 'white' : color,
                          }}
                          className="px-3 py-1.5 rounded-lg text-sm font-medium transition border-2"
                        >
                          {ds.dataset_id}
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Kaplan-Meier Plot */}
              {allKmChartData !== null ? (
                <>
                  <div className="h-96 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={allKmChartData} margin={{ top: 20, right: 30, bottom: 20, left: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis
                          dataKey="time"
                          label={{ value: 'Time (months)', position: 'insideBottomRight', offset: -5 }}
                        />
                        <YAxis
                          domain={[0, 100]}
                          label={{ value: 'Survival Probability (%)', angle: -90, position: 'insideLeft' }}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend />
                        <ReferenceLine y={50} stroke="var(--color-chart-label)" strokeDasharray="5 5" />
                        {visibleList.map((ds, idx) => {
                          const color = DATASET_COLORS[idx % DATASET_COLORS.length]
                          const hasHighCI = !!(ds.km_curve_high?.ci_lower?.length && ds.km_curve_high?.ci_upper?.length)
                          const hasLowCI = !!(ds.km_curve_low?.ci_lower?.length && ds.km_curve_low?.ci_upper?.length)
                          return [
                            <Line
                              key={`${ds.dataset_id}_high`}
                              type="stepAfter"
                              dataKey={`${ds.dataset_id}_high`}
                              name={`${ds.dataset_id} High`}
                              stroke={color}
                              strokeWidth={2}
                              dot={false}
                              connectNulls
                            />,
                            <Line
                              key={`${ds.dataset_id}_low`}
                              type="stepAfter"
                              dataKey={`${ds.dataset_id}_low`}
                              name={`${ds.dataset_id} Low`}
                              stroke={color}
                              strokeWidth={2}
                              strokeDasharray="5 5"
                              dot={false}
                              connectNulls
                            />,
                            ...(hasHighCI ? [
                              <Line
                                key={`${ds.dataset_id}_high_ci_lower`}
                                type="stepAfter"
                                dataKey={`${ds.dataset_id}_high_ci_lower`}
                                stroke={color}
                                strokeOpacity={0.3}
                                strokeWidth={1}
                                strokeDasharray="3 3"
                                legendType="none"
                                dot={false}
                                connectNulls
                              />,
                              <Line
                                key={`${ds.dataset_id}_high_ci_upper`}
                                type="stepAfter"
                                dataKey={`${ds.dataset_id}_high_ci_upper`}
                                stroke={color}
                                strokeOpacity={0.3}
                                strokeWidth={1}
                                strokeDasharray="3 3"
                                legendType="none"
                                dot={false}
                                connectNulls
                              />,
                            ] : []),
                            ...(hasLowCI ? [
                              <Line
                                key={`${ds.dataset_id}_low_ci_lower`}
                                type="stepAfter"
                                dataKey={`${ds.dataset_id}_low_ci_lower`}
                                stroke={color}
                                strokeOpacity={0.3}
                                strokeWidth={1}
                                strokeDasharray="3 3"
                                legendType="none"
                                dot={false}
                                connectNulls
                              />,
                              <Line
                                key={`${ds.dataset_id}_low_ci_upper`}
                                type="stepAfter"
                                dataKey={`${ds.dataset_id}_low_ci_upper`}
                                stroke={color}
                                strokeOpacity={0.3}
                                strokeWidth={1}
                                strokeDasharray="3 3"
                                legendType="none"
                                dot={false}
                                connectNulls
                              />,
                            ] : []),
                          ]
                        }).flat()}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                  <p className="text-fg-muted text-sm mt-4 text-center italic">
                    Showing {visibleList.length} of {displayDatasets.length} dataset(s). Click toggles above to show/hide individual datasets.
                  </p>
                </>
              ) : (
                <div className="h-48 w-full flex flex-col items-center justify-center bg-surface-sunken rounded-lg border border-border">
                  <svg className="w-10 h-10 text-fg-faint mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  <p className="text-fg-muted font-medium">No survival curve data available for this gene</p>
                  <p className="text-fg-faint text-sm mt-1">The per-study statistics below are still valid.</p>
                </div>
              )}
            </>
          )}

          {/* Per-dataset results table */}
          {gene.per_dataset_results && gene.per_dataset_results.length > 0 && (
            <div className="mt-6 pt-4 border-t border-border">
              <h3 className="font-semibold text-fg-strong mb-3">Meta-Analysis: Per-Study Results</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-border">
                  <thead className="bg-surface-sunken">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-fg-muted uppercase">Dataset</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-fg-muted uppercase">HR (95% CI)</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-fg-muted uppercase">P-value</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-fg-muted uppercase">N</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-fg-muted uppercase">Risk</th>
                    </tr>
                  </thead>
                  <tbody className="bg-surface divide-y divide-border">
                    {gene.per_dataset_results.map((ds) => {
                      const hasKm = !!(ds.km_curve_high && ds.km_curve_low)
                      const color = hasKm ? DATASET_COLORS[displayDatasets.findIndex(d => d.dataset_id === ds.dataset_id) % DATASET_COLORS.length] : undefined
                      const isVisible = visibleDatasets.has(ds.dataset_id)
                      return (
                        <tr
                          key={ds.dataset_id}
                          className={`transition ${hasKm ? 'cursor-pointer hover:bg-surface-sunken' : ''} ${hasKm && !isVisible ? 'opacity-40' : ''}`}
                          onClick={() => hasKm && toggleDataset(ds.dataset_id)}
                        >
                          <td className="px-4 py-2">
                            <div className="flex items-center gap-2">
                              {color && (
                                <span
                                  className="inline-block w-3 h-3 rounded-full flex-shrink-0"
                                  style={{ backgroundColor: color }}
                                />
                              )}
                              <div>
                                <div className="text-sm font-medium text-fg-strong">{ds.dataset_id}</div>
                                <div className="text-xs text-fg-muted truncate max-w-xs">{ds.dataset_title}</div>
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-2 text-sm">
                            <span className={ds.hazard_ratio > 1 ? 'text-danger' : 'text-accent-fg'}>
                              {ds.hazard_ratio.toFixed(2)}
                            </span>
                            <span className="text-fg-faint text-xs ml-1">
                              [{ds.hazard_ratio_ci_lower.toFixed(2)}-{ds.hazard_ratio_ci_upper.toFixed(2)}]
                            </span>
                          </td>
                          <td className="px-4 py-2 text-sm text-fg">
                            {ds.log_rank_p_value < 0.001
                              ? ds.log_rank_p_value.toExponential(2)
                              : ds.log_rank_p_value.toFixed(4)}
                          </td>
                          <td className="px-4 py-2 text-sm text-fg">{ds.n_samples}</td>
                          <td className="px-4 py-2">
                            <span className={`inline-flex px-2 py-1 text-xs rounded-full ${
                              ds.risk_direction === 'high_risk'
                                ? 'bg-danger-soft text-danger'
                                : 'bg-accent-soft text-accent-fg'
                            }`}>
                              {ds.risk_direction === 'high_risk' ? '↑ Risk' : '↓ Protective'}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-fg-faint mt-2">
                Click a row to toggle its curves on/off (rows without KM data are not clickable)
              </p>
            </div>
          )}

          {/* Datasets list (fallback when no per-dataset results) */}
          {(!gene.per_dataset_results || gene.per_dataset_results.length === 0) && (
            <div className="mt-6 pt-4 border-t border-border">
              <h3 className="font-semibold text-fg-strong mb-3">Found in Datasets</h3>
              <div className="flex flex-wrap gap-2">
                {gene.datasets.map((dataset) => (
                  <span key={dataset} className="bg-accent-soft text-accent-fg text-sm px-3 py-1 rounded-full">
                    {dataset}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default KaplanMeierPlot
