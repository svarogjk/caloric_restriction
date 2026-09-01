import React from 'react'
import PatientReadout from '../../oncologist/PatientReadout'
import { PredictResponse, ReferenceKMCurve } from '../../../services/api'

interface ReadoutCardProps {
    prediction: PredictResponse
    modelId: string
    cancerLabel: string
    modelIsDemo: boolean
    referenceCurves?: ReferenceKMCurve[]
    timeUnit: string
    expression: Record<string, number>
    clinical: Record<string, string>
}

/** Thin wrapper — all the real rendering (risk badge, KM, driver bars,
 *  advisory treatments, print report) is the existing PatientReadout. */
const ReadoutCard: React.FC<ReadoutCardProps> = (props) => (
    <div className="bg-surface border border-border rounded-card p-4">
        <PatientReadout {...props} />
    </div>
)

export default ReadoutCard
