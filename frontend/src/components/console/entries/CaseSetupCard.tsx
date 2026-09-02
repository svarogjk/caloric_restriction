import React from 'react'
import { Card, StepHeader } from '../../ui'
import CancerTypeSelect from '../CancerTypeSelect'
import ClinicalCovariateFields from '../../oncologist/ClinicalCovariateFields'
import { GalleryCancer, ClinicalCovariateSpec } from '../../../services/api'

export interface CaseSetupCardProps {
    cancers: GalleryCancer[]
    cancersLoading: boolean
    onSelectCancer: (cancer: GalleryCancer) => void
    onBuildOther: (query: string) => void
    /** Already-chosen cancer type, so a superseded card reads as settled. */
    selectedLabel: string | null
    /** Covariate spec for the chosen model — empty until one is picked. */
    covariates: ClinicalCovariateSpec[]
    clinical: Record<string, string>
    onClinicalChange: (name: string, value: string) => void
}

/**
 * Step 1, in the conversation.
 *
 * The curated-cancer picker used to exist only in the right rail, so the chat
 * could describe the first step but never complete it — the clinician had to
 * break out of the conversation to answer. It is the same `CancerTypeSelect`
 * control, just rendered where the question was asked.
 */
const CaseSetupCard: React.FC<CaseSetupCardProps> = ({
    cancers, cancersLoading, onSelectCancer, onBuildOther,
    selectedLabel, covariates, clinical, onClinicalChange,
}) => {
    const filled = Object.values(clinical).filter((v) => v !== '').length

    return (
        <Card tone="clinical" dense>
            <StepHeader
                index={1}
                title="Case"
                status={selectedLabel ? 'done' : 'active'}
                hint={selectedLabel ?? 'which cancer type, and therefore which validated model'}
            />

            <div className="mt-2.5">
                <CancerTypeSelect
                    cancers={cancers}
                    loading={cancersLoading}
                    onSelect={onSelectCancer}
                    onBuildOther={onBuildOther}
                />
            </div>

            {/* Covariates only appear once a model is chosen: the accepted names come
                from that model's own training cohort (covariate_form_spec), so there
                is no fixed clinical schema to offer before then. */}
            {covariates.length > 0 && (
                <div className="mt-3 pt-3 border-t border-border">
                    <StepHeader
                        index={2}
                        title="Clinical covariates"
                        status={filled > 0 ? 'done' : 'todo'}
                        hint={`optional — this model's cohort recorded ${covariates.length}`}
                    />
                    <div className="mt-2">
                        <ClinicalCovariateFields
                            covariates={covariates}
                            values={clinical}
                            onChange={onClinicalChange}
                            columns={3}
                        />
                    </div>
                    <p className="text-[11px] text-fg-faint mt-1.5">
                        Covariates refine a score — they cannot replace the expression profile.
                    </p>
                </div>
            )}
        </Card>
    )
}

export default CaseSetupCard
