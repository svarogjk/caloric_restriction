import React from 'react'
import { QueryEstimation as QueryEstimationType } from '../../store/chatSlice'

interface QueryEstimationProps {
    estimation: QueryEstimationType
    onRunAnalysis: (query: string) => void
    onDismiss: () => void
}

const QueryEstimation: React.FC<QueryEstimationProps> = ({
    estimation,
    onRunAnalysis,
    onDismiss,
}) => {
    const getConfidenceColor = (score: number) => {
        if (score >= 0.7) return 'green'
        if (score >= 0.4) return 'yellow'
        return 'red'
    }

    const color = getConfidenceColor(estimation.confidenceScore)

    const colorClasses = {
        green: {
            bg: 'bg-green-50',
            border: 'border-green-500',
            text: 'text-green-700',
            badge: 'bg-green-100 text-green-800',
        },
        yellow: {
            bg: 'bg-yellow-50',
            border: 'border-yellow-500',
            text: 'text-yellow-700',
            badge: 'bg-yellow-100 text-yellow-800',
        },
        red: {
            bg: 'bg-red-50',
            border: 'border-red-500',
            text: 'text-red-700',
            badge: 'bg-red-100 text-red-800',
        },
    }

    const classes = colorClasses[color]

    return (
        <div className={`${classes.bg} border-l-4 ${classes.border} p-4 mx-4 my-2 rounded-r-lg`}>
            <div className="flex items-start justify-between">
                <div className="flex-1">
                    {/* Header with confidence score */}
                    <div className="flex items-center gap-3 mb-2">
                        <h4 className={`font-semibold ${classes.text}`}>
                            Query Analysis
                        </h4>
                        <span className={`px-2 py-0.5 text-sm rounded-full ${classes.badge}`}>
                            {(estimation.confidenceScore * 100).toFixed(0)}% Confidence
                        </span>
                    </div>

                    {/* Stats */}
                    <div className="flex gap-4 text-sm text-gray-600 mb-3">
                        <span>
                            Est. {estimation.estimatedDatasets} datasets
                        </span>
                        <span>|</span>
                        <span>
                            ~{Math.ceil(estimation.estimatedTimeSeconds / 60)} min
                        </span>
                    </div>

                    {/* Suggestions */}
                    {estimation.suggestions.length > 0 && (
                        <div className="mb-3">
                            <p className="text-sm font-medium text-gray-700 mb-1">
                                Suggestions to improve results:
                            </p>
                            <ul className="text-sm text-gray-600 list-disc list-inside space-y-1">
                                {estimation.suggestions.slice(0, 3).map((suggestion, i) => (
                                    <li key={i}>{suggestion}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Improved Query */}
                    {estimation.improvedQuery && (
                        <div className="bg-white p-3 rounded border border-gray-200">
                            <p className="text-sm font-medium text-gray-700 mb-1">
                                Suggested query:
                            </p>
                            <p className="text-sm text-blue-600 italic">
                                "{estimation.improvedQuery}"
                            </p>
                            <button
                                onClick={() => onRunAnalysis(estimation.improvedQuery!)}
                                className="mt-2 text-sm text-blue-600 hover:text-blue-700 font-medium"
                            >
                                Use this query
                            </button>
                        </div>
                    )}
                </div>

                {/* Actions */}
                <div className="flex flex-col gap-2 ml-4">
                    <button
                        onClick={onDismiss}
                        className="text-gray-400 hover:text-gray-600"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>

                    {estimation.canProceed && (
                        <button
                            onClick={() => onRunAnalysis(estimation.improvedQuery || '')}
                            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
                        >
                            Run Analysis
                        </button>
                    )}
                </div>
            </div>
        </div>
    )
}

export default QueryEstimation
