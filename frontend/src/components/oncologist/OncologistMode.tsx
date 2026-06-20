import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getGallery, GalleryCancer } from '../../services/api'
import PatientPanel from './PatientPanel'

/**
 * Oncologist Mode — now a thin preset on top of the unified personalization flow.
 * It is the curated-analysis picker: choose a cancer type (a pre-built combined
 * clinical + expression model) and score a patient via the shared PatientPanel.
 * The actual scoring path is identical to attaching a patient to any free-text
 * analysis. Predictive + advisory, research use only.
 */
const OncologistMode: React.FC = () => {
    const [cancers, setCancers] = useState<GalleryCancer[]>([])
    const [error, setError] = useState<string | null>(null)
    const [selected, setSelected] = useState<GalleryCancer | null>(null)

    useEffect(() => {
        getGallery().then(setCancers).catch(() => setError('Could not load the cancer catalogue.'))
    }, [])

    if (!selected) {
        return <CancerPicker cancers={cancers} error={error} onSelect={setSelected} />
    }

    return (
        <div className="max-w-4xl mx-auto px-4 py-8">
            <button onClick={() => setSelected(null)} className="text-sm text-indigo-600 hover:underline mb-4">
                ← Choose a different cancer type
            </button>

            <h1 className="text-2xl font-semibold text-gray-800 flex items-center gap-2">
                <span>{selected.icon}</span> {selected.label}
            </h1>
            <p className="text-gray-500 mt-1">
                Enter this patient's tumour data to predict a risk group and surface advisory treatments to discuss.
                <span className="font-medium"> Predictive + advisory, research use only.</span>
            </p>

            <div className="mt-3 text-xs text-gray-500">
                Model: combined C-index {(selected.c_index_combined ?? selected.pooled_c_index ?? 0).toFixed(3)}
                {selected.delta_c_index != null && ` (Δ ${selected.delta_c_index >= 0 ? '+' : ''}${selected.delta_c_index.toFixed(3)} over expression)`}
                {selected.n_genes ? ` · ${selected.n_genes} genes` : ''}
                {selected.model_is_demo ? ' · demo model' : ''}
            </div>

            <div className="mt-5">
                <PatientPanel
                    modelId={selected.model_id}
                    label={selected.label}
                    initialCovariates={selected.clinical_covariates}
                    alwaysOpen
                    cancerType={selected.key}
                />
            </div>
        </div>
    )
}

const CancerPicker: React.FC<{
    cancers: GalleryCancer[]
    error: string | null
    onSelect: (c: GalleryCancer) => void
}> = ({ cancers, error, onSelect }) => (
    <div className="max-w-5xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-semibold text-gray-800">Oncologist Mode</h1>
        <p className="text-gray-500 mt-1">
            Pick a cancer type, then enter your patient's tumour data to predict a risk group and surface advisory
            treatments to discuss, from a cross-cohort-validated model.
            <span className="font-medium"> Predictive + advisory, research use only — not a prescription.</span>
        </p>

        {error && <p className="text-red-600 mt-4">{error}</p>}
        {!cancers.length && !error && <p className="text-gray-500 mt-4">Loading…</p>}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
            {cancers.map((c) => {
                const ready = !!c.model_id
                return (
                    <button
                        key={c.key}
                        onClick={() => onSelect(c)}
                        disabled={!ready}
                        className={`text-left bg-white rounded-lg border p-4 flex flex-col transition-all ${
                            ready
                                ? 'border-gray-200 shadow-sm hover:shadow-md hover:border-indigo-300'
                                : 'border-gray-100 opacity-60 cursor-not-allowed'
                        }`}
                    >
                        <div className="flex items-center gap-2">
                            <span className="text-2xl">{c.icon}</span>
                            <h3 className="font-semibold text-gray-800">{c.label}</h3>
                        </div>
                        <p className="text-sm text-gray-500 mt-2 flex-1">{c.blurb}</p>
                        <div className="mt-3 flex items-center justify-between text-xs">
                            {ready ? (
                                <span className="text-gray-500">
                                    C-index {(c.pooled_c_index ?? 0).toFixed(2)}
                                    {c.n_genes ? ` · ${c.n_genes} genes` : ''}
                                    {c.model_is_demo ? ' · demo model' : ''}
                                </span>
                            ) : (
                                <span className="text-gray-400">Preparing model…</span>
                            )}
                            {ready && <span className="text-indigo-600 font-medium">Score a patient →</span>}
                        </div>
                    </button>
                )
            })}
        </div>

        <div className="mt-8 text-center">
            <Link to="/" className="text-sm text-indigo-600 hover:underline">← Back to free-text analysis</Link>
        </div>
    </div>
)

export default OncologistMode
