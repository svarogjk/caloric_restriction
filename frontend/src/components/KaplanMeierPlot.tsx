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
import { GeneSurvival } from '../store/searchSlice'

interface KaplanMeierPlotProps {
  gene: GeneSurvival
  onClose: () => void
}

/**
 * Kaplan-Meier survival curve visualization with per-dataset meta-analysis support
 * Shows actual KM curves from each dataset when available, or generates illustrative curves
 */
const KaplanMeierPlot: React.FC<KaplanMeierPlotProps> = ({ gene, onClose }) => {
  const [selectedDataset, setSelectedDataset] = React.useState<string | null>(null)

  // Get datasets that have KM curve data
  const displayDatasets = React.useMemo(() => {
    if (!gene.per_dataset_results || gene.per_dataset_results.length === 0) {
      return []
    }
    return gene.per_dataset_results.filter(
      ds => ds.km_curve_high && ds.km_curve_low
    )
  }, [gene.per_dataset_results])

  const currentDataset = React.useMemo(() => {
    if (displayDatasets.length === 0) return null
    if (selectedDataset) {
      return displayDatasets.find(ds => ds.dataset_id === selectedDataset) || displayDatasets[0]
    }
    return displayDatasets[0]
  }, [displayDatasets, selectedDataset])

  // Transform KM data for the selected dataset
  const kmChartData = React.useMemo(() => {
    if (!currentDataset?.km_curve_high || !currentDataset?.km_curve_low) {
      return null
    }

    const high = currentDataset.km_curve_high
    const low = currentDataset.km_curve_low
    
    // Combine time points from both curves
    const allTimes = [...new Set([...high.times, ...low.times])].sort((a, b) => a - b)
    
    // Create step function data
    return allTimes.map(time => {
      const highIdx = high.times.findIndex((_t, i) => 
        i === high.times.length - 1 || high.times[i + 1] > time
      )
      const lowIdx = low.times.findIndex((_t, i) => 
        i === low.times.length - 1 || low.times[i + 1] > time
      )
      
      return {
        time,
        highExpression: high.survival_probabilities[Math.max(0, highIdx)] * 100,
        lowExpression: low.survival_probabilities[Math.max(0, lowIdx)] * 100,
      }
    })
  }, [currentDataset])

  // Generate mock data if no real KM data available
  const mockKMData = React.useMemo(() => {
    const timePoints = [0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60]
    const hr = gene.avg_hazard_ratio
    const baseLambda = 0.015

    return timePoints.map((time) => ({
      time,
      highExpression: Math.exp(-baseLambda * hr * time) * 100,
      lowExpression: Math.exp(-baseLambda * time) * 100,
    }))
  }, [gene.avg_hazard_ratio])

  const chartData = kmChartData || mockKMData
  const hasRealData = kmChartData !== null

  const CustomTooltip: React.FC<any> = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-gray-300 rounded shadow-lg">
          <p className="font-semibold text-gray-800">Time: {label} months</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ color: entry.color }} className="text-sm">
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
      return {
        text: 'Strong association with poor survival',
        color: 'text-red-600',
        bgColor: 'bg-red-50',
      }
    } else if (hr > 1.5) {
      return {
        text: 'Moderate association with poor survival',
        color: 'text-orange-600',
        bgColor: 'bg-orange-50',
      }
    } else if (hr > 1) {
      return {
        text: 'Slight association with poor survival',
        color: 'text-yellow-600',
        bgColor: 'bg-yellow-50',
      }
    } else if (hr > 0.67) {
      return {
        text: 'Slight association with better survival',
        color: 'text-green-600',
        bgColor: 'bg-green-50',
      }
    } else if (hr > 0.5) {
      return {
        text: 'Moderate association with better survival',
        color: 'text-green-600',
        bgColor: 'bg-green-50',
      }
    } else {
      return {
        text: 'Strong association with better survival',
        color: 'text-green-700',
        bgColor: 'bg-green-100',
      }
    }
  }

  const interpretation = getRiskInterpretation()

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-2xl font-bold text-gray-800">
              Kaplan-Meier Survival Curves
            </h2>
            <p className="text-gray-600 mt-1">
              {gene.gene_symbol || gene.gene_id}
              {gene.gene_symbol && gene.gene_symbol !== gene.gene_id && (
                <span className="text-gray-400 ml-2">({gene.gene_id})</span>
              )}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition p-2 hover:bg-gray-100 rounded-full"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Stats summary */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-gray-600 text-sm font-medium">Avg Hazard Ratio</p>
              <p className={`text-2xl font-bold ${gene.avg_hazard_ratio > 1 ? 'text-red-600' : 'text-blue-600'}`}>
                {gene.avg_hazard_ratio.toFixed(2)}
              </p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-gray-600 text-sm font-medium">Avg P-value</p>
              <p className="text-2xl font-bold text-gray-800">
                {gene.avg_log_rank_p_value < 0.001
                  ? gene.avg_log_rank_p_value.toExponential(2)
                  : gene.avg_log_rank_p_value.toFixed(4)}
              </p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-gray-600 text-sm font-medium">Datasets</p>
              <p className="text-2xl font-bold text-purple-600">{gene.n_datasets}</p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-gray-600 text-sm font-medium">Direction Consistency</p>
              <p className="text-2xl font-bold text-green-600">
                {(gene.risk_direction_consistency * 100).toFixed(0)}%
              </p>
            </div>
          </div>

          {/* Interpretation */}
          <div className={`${interpretation.bgColor} border rounded-lg p-4 mb-6`}>
            <p className={`${interpretation.color} font-medium`}>
              {interpretation.text}
            </p>
            <p className="text-gray-600 text-sm mt-1">
              {gene.predominant_risk === 'high_risk'
                ? 'Higher expression of this gene is associated with worse survival outcomes.'
                : 'Higher expression of this gene is associated with better survival outcomes.'}
            </p>
          </div>

          {/* Dataset selector */}
          {displayDatasets.length > 0 && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Dataset for KM Curve:
              </label>
              <div className="flex flex-wrap gap-2">
                {displayDatasets.map((ds, idx) => (
                  <button
                    key={ds.dataset_id}
                    onClick={() => setSelectedDataset(ds.dataset_id)}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition ${
                      (selectedDataset === ds.dataset_id || (!selectedDataset && idx === 0))
                        ? 'bg-indigo-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {ds.dataset_id}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Current dataset info */}
          {currentDataset && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <p className="font-medium text-blue-800">{currentDataset.dataset_id}</p>
              <p className="text-blue-600 text-sm">{currentDataset.dataset_title}</p>
              <div className="flex gap-4 mt-2 text-sm flex-wrap">
                <span>HR: <b>{currentDataset.hazard_ratio.toFixed(2)}</b></span>
                <span>95% CI: [{currentDataset.hazard_ratio_ci_lower.toFixed(2)} - {currentDataset.hazard_ratio_ci_upper.toFixed(2)}]</span>
                <span>p: <b>{currentDataset.log_rank_p_value < 0.001 ? currentDataset.log_rank_p_value.toExponential(2) : currentDataset.log_rank_p_value.toFixed(4)}</b></span>
                <span>n={currentDataset.n_samples}</span>
              </div>
            </div>
          )}

          {/* Kaplan-Meier Plot */}
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={chartData}
                margin={{ top: 20, right: 30, bottom: 20, left: 20 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="time"
                  label={{
                    value: hasRealData ? 'Time' : 'Time (months)',
                    position: 'insideBottomRight',
                    offset: -5,
                  }}
                />
                <YAxis
                  domain={[0, 100]}
                  label={{
                    value: 'Survival Probability (%)',
                    angle: -90,
                    position: 'insideLeft',
                  }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                <ReferenceLine y={50} stroke="#9ca3af" strokeDasharray="5 5" />
                <Line
                  type="stepAfter"
                  dataKey="highExpression"
                  name="High Expression"
                  stroke="#ef4444"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="stepAfter"
                  dataKey="lowExpression"
                  name="Low Expression"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Note about data source */}
          <p className="text-gray-500 text-sm mt-4 text-center italic">
            {hasRealData 
              ? `Showing actual survival data from ${currentDataset?.dataset_id}. Select different datasets above to compare.`
              : 'Note: This is an illustrative representation based on the average hazard ratio. No raw KM data available.'}
          </p>

          {/* Per-dataset results table */}
          {gene.per_dataset_results && gene.per_dataset_results.length > 0 && (
            <div className="mt-6 pt-4 border-t border-gray-200">
              <h3 className="font-semibold text-gray-800 mb-3">Meta-Analysis: Per-Study Results</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Dataset</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">HR (95% CI)</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">P-value</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">N</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Risk</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {gene.per_dataset_results.map((ds) => (
                      <tr 
                        key={ds.dataset_id}
                        className={`cursor-pointer hover:bg-gray-50 ${
                          currentDataset?.dataset_id === ds.dataset_id ? 'bg-indigo-50' : ''
                        }`}
                        onClick={() => ds.km_curve_high && setSelectedDataset(ds.dataset_id)}
                      >
                        <td className="px-4 py-2">
                          <div className="text-sm font-medium text-gray-900">{ds.dataset_id}</div>
                          <div className="text-xs text-gray-500 truncate max-w-xs">{ds.dataset_title}</div>
                        </td>
                        <td className="px-4 py-2 text-sm">
                          <span className={ds.hazard_ratio > 1 ? 'text-red-600' : 'text-blue-600'}>
                            {ds.hazard_ratio.toFixed(2)}
                          </span>
                          <span className="text-gray-400 text-xs ml-1">
                            [{ds.hazard_ratio_ci_lower.toFixed(2)}-{ds.hazard_ratio_ci_upper.toFixed(2)}]
                          </span>
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-700">
                          {ds.log_rank_p_value < 0.001 
                            ? ds.log_rank_p_value.toExponential(2) 
                            : ds.log_rank_p_value.toFixed(4)}
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-700">{ds.n_samples}</td>
                        <td className="px-4 py-2">
                          <span className={`inline-flex px-2 py-1 text-xs rounded-full ${
                            ds.risk_direction === 'high_risk' 
                              ? 'bg-red-100 text-red-800' 
                              : 'bg-blue-100 text-blue-800'
                          }`}>
                            {ds.risk_direction === 'high_risk' ? '↑ Risk' : '↓ Protective'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-gray-400 mt-2">
                Click on a row to view its Kaplan-Meier curve (if available)
              </p>
            </div>
          )}

          {/* Datasets list (fallback when no per-dataset results) */}
          {(!gene.per_dataset_results || gene.per_dataset_results.length === 0) && (
            <div className="mt-6 pt-4 border-t border-gray-200">
              <h3 className="font-semibold text-gray-800 mb-3">Found in Datasets</h3>
              <div className="flex flex-wrap gap-2">
                {gene.datasets.map((dataset) => (
                  <span
                    key={dataset}
                    className="bg-indigo-100 text-indigo-800 text-sm px-3 py-1 rounded-full"
                  >
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
