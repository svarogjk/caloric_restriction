import React from 'react'
import TherapyDirections from '../../oncologist/TherapyDirections'
import { ReferenceKMCurve } from '../../../services/api'

interface TreatmentEvidenceCardProps {
    modelId: string
    riskGroup: string | null
    genes: string[]
    baselineCurve: ReferenceKMCurve | null
    expression: Record<string, number>
    clinical: Record<string, string>
    timeUnit: string
}

/** "What treatments should we discuss?" outside of an already-open readout —
 *  reuses TherapyDirections with autoGenerate so it starts immediately. */
const TreatmentEvidenceCard: React.FC<TreatmentEvidenceCardProps> = (props) => (
    <TherapyDirections
        modelId={props.modelId}
        riskGroup={props.riskGroup ?? undefined}
        genes={props.genes}
        baselineCurve={props.baselineCurve ?? undefined}
        expression={props.expression}
        clinical={props.clinical}
        timeUnit={props.timeUnit}
        autoGenerate
    />
)

export default TreatmentEvidenceCard
