import React from 'react'
import { SAMPLE_PATIENTS, SamplePatient } from '../../utils/samplePatients'
import { GalleryCancer } from '../../services/api'
import CaseCard from './CaseCard'
import ExpressionFormatCard from './ExpressionFormatCard'
import CancerTypeSelect from './CancerTypeSelect'

interface CaseLibraryProps {
    cancers: GalleryCancer[]
    cancersLoading: boolean
    onSelectCancer: (cancer: GalleryCancer) => void
    onBuildOther: (query: string) => void
    onLoadCase: (patient: SamplePatient) => void
    onTryFormatExample: (text: string) => void
    /** Inside the rail's "change cancer type" disclosure: drop the heading and
     *  the format explainer, which are already on screen. */
    compact?: boolean
}

/**
 * The console's empty state — the biggest thing on screen on arrival. A
 * direct manual path (pick a cancer type) sits alongside the agent-mediated
 * one (describe the case in the composer) and the worked examples — not every
 * interaction needs to go through a chat turn.
 */
const CaseLibrary: React.FC<CaseLibraryProps> = ({ cancers, cancersLoading, onSelectCancer, onBuildOther, onLoadCase, onTryFormatExample, compact = false }) => {
    const curated = SAMPLE_PATIENTS.filter((p) => p.cancerKey !== null)
    const uncurated = SAMPLE_PATIENTS.filter((p) => p.cancerKey === null)

    return (
        <div className="space-y-4">
            {!compact && (
                <p className="text-xs text-fg-muted">
                    Describe a case in the composer, pick a cancer type, or load a worked example.
                </p>
            )}

            <CancerTypeSelect cancers={cancers} loading={cancersLoading} onSelect={onSelectCancer} onBuildOther={onBuildOther} />

            {!compact && <ExpressionFormatCard onTryExample={onTryFormatExample} />}

            <div>
                <p className="text-xs font-semibold text-fg-muted mb-2">Worked examples — curated models, scores in seconds</p>
                <div className="grid grid-cols-1 gap-3">
                    {curated.map((p) => <CaseCard key={p.id} patient={p} onLoad={onLoadCase} />)}
                </div>
            </div>

            {uncurated.length > 0 && (
                <div>
                    <p className="text-xs font-semibold text-fg-muted mb-2">
                        Cases without a curated model — a cohort model is built on demand (~3 min)
                    </p>
                    <div className="grid grid-cols-1 gap-3">
                        {uncurated.map((p) => <CaseCard key={p.id} patient={p} onLoad={onLoadCase} />)}
                    </div>
                </div>
            )}
        </div>
    )
}

export default CaseLibrary
