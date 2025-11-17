import React from 'react'
import { Dataset, downloadDataset } from '../services/api'
import VolcanoPlot from './VolcanoPlot'

interface DatasetCardProps {
  dataset: Dataset
  isExpanded: boolean
  onToggle: () => void
}

const DatasetCard: React.FC<DatasetCardProps> = ({
  dataset,
  isExpanded,
  onToggle,
}) => {
  const [downloading, setDownloading] = React.useState(false)

  const handleDownload = React.useCallback(
    async (format: 'csv' | 'json') => {
      setDownloading(true)
      try {
        const blob = await downloadDataset(dataset.id, format)
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `${dataset.id}.${format}`
        document.body.appendChild(link)
        link.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(link)
      } catch (error) {
        console.error('Download failed:', error)
      } finally {
        setDownloading(false)
      }
    },
    [dataset.id]
  )

  return (
    <div className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow">
      <button
        onClick={onToggle}
        className="w-full text-left px-6 py-4 hover:bg-gray-50 transition"
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-800">
              {dataset.name}
            </h3>
            <p className="text-gray-600 text-sm mt-1">{dataset.description}</p>
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
        <div className="border-t border-gray-200 px-6 py-6 bg-gray-50">
          <div className="space-y-6">
            <div>
              <h4 className="text-lg font-semibold text-gray-800 mb-4">
                Differential Expression Analysis
              </h4>
              <VolcanoPlot data={dataset.geneExpression} />
            </div>

            <div className="flex gap-2 pt-4 border-t border-gray-200">
              <button
                onClick={() => handleDownload('csv')}
                disabled={downloading}
                className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-semibold py-2 px-4 rounded-lg transition"
              >
                {downloading ? 'Downloading...' : 'Download CSV'}
              </button>
              <button
                onClick={() => handleDownload('json')}
                disabled={downloading}
                className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold py-2 px-4 rounded-lg transition"
              >
                {downloading ? 'Downloading...' : 'Download JSON'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default DatasetCard
