import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getAnalysisResult, SurvivalAnalysisResponse } from '../services/api'
import AnalysisResultsDisplay from './chat/AnalysisResultsDisplay'
import { AnalysisResult } from '../store/chatSlice'

const SharedResultPage: React.FC = () => {
    const { resultId } = useParams<{ resultId: string }>()
    const [result, setResult] = useState<AnalysisResult | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        if (!resultId) {
            setError('Invalid result ID')
            setLoading(false)
            return
        }

        getAnalysisResult(resultId)
            .then((data: SurvivalAnalysisResponse) => {
                setResult(data as AnalysisResult)
                setLoading(false)
            })
            .catch(() => {
                setError('Result not found or has expired')
                setLoading(false)
            })
    }, [resultId])

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-100">
                <div className="text-center">
                    <svg className="animate-spin h-10 w-10 text-indigo-600 mx-auto" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <p className="mt-4 text-gray-600">Loading analysis result...</p>
                </div>
            </div>
        )
    }

    if (error || !result) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-100">
                <div className="text-center max-w-md px-4">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-100 flex items-center justify-center">
                        <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                    </div>
                    <h2 className="text-xl font-semibold text-gray-800 mb-2">Result Not Found</h2>
                    <p className="text-gray-600 mb-6">{error ?? 'This analysis result could not be found or may have expired.'}</p>
                    <Link
                        to="/"
                        className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                    >
                        Go to Home
                    </Link>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-gray-100">
            {/* Shared banner */}
            <div className="bg-indigo-600 text-white px-4 py-2 text-sm flex items-center justify-between">
                <span>Shared analysis from GEO Survival Analysis</span>
                <Link
                    to="/"
                    className="text-indigo-200 hover:text-white font-medium underline underline-offset-2"
                >
                    Run your own &rarr;
                </Link>
            </div>

            {/* Nav */}
            <nav className="bg-white shadow-sm border-b border-gray-200">
                <div className="max-w-4xl mx-auto px-4">
                    <div className="flex items-center h-14">
                        <h1 className="text-xl font-semibold text-gray-800">GEO Survival Analysis</h1>
                    </div>
                </div>
            </nav>

            {/* Content */}
            <main className="max-w-4xl mx-auto px-4 py-6">
                <AnalysisResultsDisplay results={result} />
            </main>
        </div>
    )
}

export default SharedResultPage
