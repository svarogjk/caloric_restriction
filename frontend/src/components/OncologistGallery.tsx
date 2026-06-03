import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getGallery, GalleryCancer } from '../services/api'

/**
 * F20 — Oncologist Mode. A curated gallery of common cancer types. Entries with
 * a pre-run cached analysis load instantly via the public /results/:id page;
 * others kick off a fresh run on the home screen. Reuses results-persistence.
 */
const OncologistGallery: React.FC = () => {
    const navigate = useNavigate()
    const [cancers, setCancers] = useState<GalleryCancer[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        getGallery()
            .then((data) => {
                setCancers(data)
                setLoading(false)
            })
            .catch(() => {
                setError('Could not load the gallery.')
                setLoading(false)
            })
    }, [])

    const handleSelect = (c: GalleryCancer) => {
        if (c.result_id) {
            navigate(`/results/${c.result_id}`)
        } else {
            navigate(`/?run=${encodeURIComponent(c.query)}`)
        }
    }

    return (
        <div className="max-w-5xl mx-auto px-4 py-8">
            <div className="mb-6">
                <h1 className="text-2xl font-semibold text-gray-800">Oncologist Mode</h1>
                <p className="text-gray-500 mt-1">
                    Curated prognostic analyses by cancer type. Pre-run cohorts load instantly; others start a
                    fresh cross-cohort analysis. <span className="font-medium">Prognostic, research use only.</span>
                </p>
            </div>

            {loading && <p className="text-gray-500">Loading gallery…</p>}
            {error && <p className="text-red-600">{error}</p>}

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {cancers.map((c) => (
                    <button
                        key={c.key}
                        onClick={() => handleSelect(c)}
                        className="text-left bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md hover:border-indigo-300 transition-all p-4 flex flex-col"
                    >
                        <div className="flex items-center gap-2">
                            <span className="text-2xl">{c.icon}</span>
                            <h3 className="font-semibold text-gray-800">{c.label}</h3>
                        </div>
                        <p className="text-sm text-gray-500 mt-2 flex-1">{c.blurb}</p>
                        <div className="mt-3 flex items-center justify-between">
                            {c.result_id ? (
                                <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-medium">
                                    ✓ Pre-run · {c.n_genes_found ?? 0} genes
                                </span>
                            ) : (
                                <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 font-medium">
                                    Run now
                                </span>
                            )}
                            <span className="text-indigo-600 text-sm font-medium">
                                {c.result_id ? 'Open →' : 'Analyze →'}
                            </span>
                        </div>
                    </button>
                ))}
            </div>

            <div className="mt-8 text-center">
                <Link to="/" className="text-sm text-indigo-600 hover:underline">
                    ← Back to free-text analysis
                </Link>
            </div>
        </div>
    )
}

export default OncologistGallery
