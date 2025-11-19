import React from 'react'
import { GeneOccurrence } from '../store/searchSlice'

interface GeneCardProps {
  gene: GeneOccurrence
  isExpanded: boolean
  onToggle: () => void
}

const GeneCard: React.FC<GeneCardProps> = ({ gene, isExpanded, onToggle }) => {
  const getDirectionColor = (consistency: number) => {
    if (consistency > 0.7) return 'text-green-600'
    if (consistency > 0.3) return 'text-yellow-600'
    return 'text-orange-600'
  }

  const getLogFcColor = (logFc: number) => {
    if (logFc > 0) return 'text-red-600'
    return 'text-blue-600'
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
                  {gene.gene_id}
                </h3>
                <p className="text-gray-600 text-sm mt-1">
                  Found in {gene.n_datasets} dataset{gene.n_datasets !== 1 ? 's' : ''}
                </p>
              </div>
              <div className="flex gap-6 ml-4">
                <div className="text-center">
                  <p className="text-gray-600 text-xs font-medium">Avg Log FC</p>
                  <p className={`text-lg font-bold ${getLogFcColor(gene.avg_log_fc)}`}>
                    {gene.avg_log_fc.toFixed(2)}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-gray-600 text-xs font-medium">
                    Consistency
                  </p>
                  <p className={`text-lg font-bold ${getDirectionColor(gene.direction_consistency)}`}>
                    {(gene.direction_consistency * 100).toFixed(0)}%
                  </p>
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

            <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200">
              <div>
                <p className="text-gray-600 text-xs font-medium mb-1">
                  Average Log2 Fold Change
                </p>
                <p className={`text-2xl font-bold ${getLogFcColor(gene.avg_log_fc)}`}>
                  {gene.avg_log_fc.toFixed(4)}
                </p>
                <p className="text-gray-500 text-xs mt-1">
                  {gene.avg_log_fc > 0 ? 'Upregulated' : 'Downregulated'}
                </p>
              </div>
              <div>
                <p className="text-gray-600 text-xs font-medium mb-1">
                  Direction Consistency
                </p>
                <p className={`text-2xl font-bold ${getDirectionColor(gene.direction_consistency)}`}>
                  {(gene.direction_consistency * 100).toFixed(1)}%
                </p>
                <p className="text-gray-500 text-xs mt-1">
                  {gene.direction_consistency > 0.7
                    ? 'Consistent'
                    : gene.direction_consistency > 0.3
                      ? 'Mixed'
                      : 'Variable'}
                  {' direction'}
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
