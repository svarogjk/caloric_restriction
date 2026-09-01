import React from 'react'
import { ClinicalCovariateSpec } from '../../services/api'

interface ClinicalCovariateFieldsProps {
    covariates: ClinicalCovariateSpec[]
    values: Record<string, string>
    onChange: (name: string, value: string) => void
    columns?: 1 | 2 | 3
}

/**
 * The clinical covariate input grid, shared by PatientPanel and the clinical
 * console. Renders a numeric input or a categorical select per covariate,
 * driven entirely by the server-provided ClinicalCovariateSpec — never
 * hardcodes which fields a model accepts.
 */
const ClinicalCovariateFields: React.FC<ClinicalCovariateFieldsProps> = ({ covariates, values, onChange, columns = 3 }) => {
    if (covariates.length === 0) return null
    const gridCols = columns === 1 ? 'grid-cols-1' : columns === 2 ? 'grid-cols-2' : 'grid-cols-2 sm:grid-cols-3'

    return (
        <div>
            <label className="block text-sm font-medium text-fg mb-1">
                Clinical covariates <span className="font-normal text-fg-faint">(optional — blank ⇒ expression only)</span>
            </label>
            <div className={`grid ${gridCols} gap-3`}>
                {covariates.map((cov) => (
                    <div key={cov.name}>
                        <label className="block text-xs text-fg-muted mb-0.5">{cov.display_label}</label>
                        {cov.kind === 'categorical' && cov.options ? (
                            <select
                                value={values[cov.name] ?? ''}
                                onChange={(e) => onChange(cov.name, e.target.value)}
                                className="w-full text-sm border border-border-strong rounded p-1.5 focus:outline-none focus:ring-1 focus:ring-accent-ring"
                            >
                                <option value="">—</option>
                                {cov.options.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
                            </select>
                        ) : (
                            <input
                                type="number"
                                value={values[cov.name] ?? ''}
                                min={cov.min_value ?? undefined}
                                max={cov.max_value ?? undefined}
                                onChange={(e) => onChange(cov.name, e.target.value)}
                                className="w-full text-sm border border-border-strong rounded p-1.5 focus:outline-none focus:ring-1 focus:ring-accent-ring"
                            />
                        )}
                    </div>
                ))}
            </div>
        </div>
    )
}

export default ClinicalCovariateFields
