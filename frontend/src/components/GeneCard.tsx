import React from 'react'
import { GeneSurvival } from '../store/searchSlice'

interface GeneCardProps {
  gene: GeneSurvival
  isExpanded: boolean
  onToggle: () => void
}

const GeneCard: React.FC<GeneCardProps> = ({ gene, isExpanded, onToggle }) => {
  const getRiskColor = (risk: string) => {
    if (risk === 'high_risk') return 'text-red-600 bg-red-50'
    return 'text-green-600 bg-green-50'
  }

  const getConsistencyColor = (consistency: number) => {
    if (consistency > 0.7) return 'text-green-600'
    if (consistency > 0.5) return 'text-yellow-600'
    return 'text-orange-600'
  }

  const getHazardRatioColor = (hr: number) => {
    if (hr > 1.5) return 'text-red-600'
    if (hr < 0.67) return 'text-blue-600'
    return 'text-gray-600'
  }

  const formatPValue = (p: number) => {
    if (p < 0.001) return p.toExponential(2)
    return p.toFixed(4)
  }

  return (
    <div className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow">
      <button
        onClick={onToggle}
        className="w-full text-left px-6 py-4 hover:bg-gray-50 transition"
      >
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-800">
                  {gene.gene_symbol || gene.gene_id}
                </h3>
                {gene.gene_symbol && gene.gene_symbol !== gene.gene_id && (
                  <p className="text-gray-500 text-xs">{gene.gene_id}</p>
                )}
                <p className="text-gray-600 text-sm mt-1">
                  Found in {gene.n_datasets} dataset{gene.n_datasets !== 1 ? 's' : ''}
                </p>
              </div>
              <div className="flex gap-6 ml-4">
                <div className="text-center">
                  <p className="text-gray-600 text-xs font-medium">Hazard Ratio</p>
                  <p className={`text-lg font-bold ${getHazardRatioColor(gene.avg_hazard_ratio)}`}>
                    {gene.avg_hazard_ratio.toFixed(2)}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-gray-600 text-xs font-medium">Cox P-value</p>
                  <p className="text-lg font-bold text-gray-800">
                    {formatPValue(gene.avg_cox_p_value)}
                  </p>
                </div>
                <div className="text-center">
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${getRiskColor(gene.predominant_risk)}`}>
                    {gene.predominant_risk === 'high_risk' ? '↑ High Risk' : '↓ Low Risk'}
                  </span>
                </div>
              </div>
            </div>
          </div>
          <svg
            className={`w-6 h-6 text-indigo-600 transition-transform ${
              isExpanded ? 'transform rotate-180' : ''
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 14l-7 7m0 0l-7-7m7 7V3"
            />
          </svg>
        </div>
      </button>

      {isExpanded && (
        <div className="border-t border-gray-200 px-6 py-4 bg-gray-50">
          <div className="space-y-4">
            <div>
              <h4 className="font-semibold text-gray-800 mb-3">
                Found in Datasets
              </h4>
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

            <div className="grid grid-cols-4 gap-4 pt-4 border-t border-gray-200">
              <div>
                <p className="text-gray-600 text-xs font-medium mb-1">
                  Average Hazard Ratio
                </p>
                <p className={`text-2xl font-bold ${getHazardRatioColor(gene.avg_hazard_ratio)}`}>
                  {gene.avg_hazard_ratio.toFixed(3)}
                </p>
                <p className="text-gray-500 text-xs mt-1">
                  {gene.avg_hazard_ratio > 1 ? 'Increased risk' : 'Decreased risk'}
                </p>
              </div>
              <div>
                <p className="text-gray-600 text-xs font-medium mb-1">
                  Cox Regression P-value
                </p>
                <p className="text-2xl font-bold text-gray-800">
                  {formatPValue(gene.avg_cox_p_value)}
                </p>
                <p className="text-gray-500 text-xs mt-1">
                  {gene.avg_cox_p_value < 0.001 ? 'Highly significant' : 
                   gene.avg_cox_p_value < 0.01 ? 'Very significant' : 'Significant'}
                </p>
              </div>
              <div>
                <p className="text-gray-600 text-xs font-medium mb-1">
                  Log-rank P-value
                </p>
                <p className="text-2xl font-bold text-gray-800">
                  {formatPValue(gene.avg_log_rank_p_value)}
                </p>
                <p className="text-gray-500 text-xs mt-1">
                  Kaplan-Meier test
                </p>
              </div>
              <div>
                <p className="text-gray-600 text-xs font-medium mb-1">
                  Risk Consistency
                </p>
                <p className={`text-2xl font-bold ${getConsistencyColor(gene.risk_direction_consistency)}`}>
                  {(gene.risk_direction_consistency * 100).toFixed(0)}%
                </p>
                <p className="text-gray-500 text-xs mt-1">
                  {gene.risk_direction_consistency > 0.7
                    ? 'Consistent'
                    : gene.risk_direction_consistency > 0.5
                      ? 'Mixed'
                      : 'Variable'}
                  {' across datasets'}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default GeneCard
