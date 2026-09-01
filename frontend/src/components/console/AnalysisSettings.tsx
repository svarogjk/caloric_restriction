import React from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState, AppDispatch } from '../../store/store'
import {
    setOrganism, setCancerGenesOnly, setDatasetCount,
    setHazardRatioUpper, setHazardRatioLower, setGeneFilterInput,
} from '../../store/chatSlice'
import { Field, FieldGrid } from '../ui'

const ORGANISMS = ['Homo sapiens', 'Mus musculus', 'Rattus norvegicus']

/**
 * The knobs a chat-driven run actually uses.
 *
 * These values already drove every console analysis — they just had no UI
 * outside /research, so the console silently applied settings nobody could see.
 * They are also forwarded to the agent (UserSettings), so it stops promising
 * results the hazard-ratio gates exclude.
 *
 * `ranking_multiplier` is deliberately left out: it is a search-internal knob,
 * not something to reason about, and it still reaches the agent as context.
 */
const AnalysisSettings: React.FC = () => {
    const dispatch = useDispatch<AppDispatch>()
    const {
        organism, cancerGenesOnly, datasetCount, hazardRatioUpper, hazardRatioLower, geneFilterInput,
    } = useSelector((s: RootState) => s.chat)

    const inputClass = 'w-full text-sm bg-surface-sunken text-fg border border-border-strong rounded-control px-2 py-1 focus:outline-none focus:ring-1 focus:ring-accent-ring'

    return (
        <details className="rounded-card border border-border bg-surface">
            <summary className="px-3 py-2 text-[11px] text-fg-muted cursor-pointer select-none">
                Analysis settings
            </summary>
            <div className="px-3 pb-3 space-y-3">
                <FieldGrid columns={2}>
                    <Field label="Organism">
                        <select
                            value={organism ?? ''}
                            onChange={(e) => dispatch(setOrganism(e.target.value || null))}
                            className={inputClass}
                        >
                            <option value="">Any</option>
                            {ORGANISMS.map((o) => <option key={o} value={o}>{o}</option>)}
                        </select>
                    </Field>
                    <Field label="Max datasets" hint="More cohorts, longer run">
                        <input
                            type="number"
                            min={1}
                            max={50}
                            value={datasetCount}
                            onChange={(e) => dispatch(setDatasetCount(Number(e.target.value) || 1))}
                            className={inputClass}
                        />
                    </Field>
                </FieldGrid>

                <FieldGrid columns={2}>
                    <Field label="HR upper gate" hint="Report if HR ≥ this">
                        <input
                            type="number" step={0.05} min={1} max={20}
                            value={hazardRatioUpper}
                            onChange={(e) => dispatch(setHazardRatioUpper(Number(e.target.value) || 1))}
                            className={inputClass}
                        />
                    </Field>
                    <Field label="HR lower gate" hint="…or HR ≤ this">
                        <input
                            type="number" step={0.05} min={0.01} max={1}
                            value={hazardRatioLower}
                            onChange={(e) => dispatch(setHazardRatioLower(Number(e.target.value) || 0.01))}
                            className={inputClass}
                        />
                    </Field>
                </FieldGrid>
                <p className="text-[10px] text-fg-faint">
                    A gene must clear one of these gates <em>and</em> the p-value threshold to be reported —
                    so a significant but small effect is excluded.
                </p>

                <label className="flex items-center gap-2 text-xs text-fg-muted">
                    <input
                        type="checkbox"
                        checked={cancerGenesOnly}
                        onChange={(e) => dispatch(setCancerGenesOnly(e.target.checked))}
                    />
                    Restrict to ~600 COSMIC cancer driver genes
                </label>

                <Field label="Candidate genes" hint="Optional — one per line or comma-separated">
                    <textarea
                        rows={2}
                        value={geneFilterInput}
                        onChange={(e) => dispatch(setGeneFilterInput(e.target.value))}
                        placeholder="MKI67, TP53, ESR1"
                        className={`${inputClass} font-mono text-xs resize-y`}
                    />
                </Field>
                {geneFilterInput.trim() && (
                    <p className="text-[10px] text-warn">
                        Restricting the tested set means the results are not multiple-testing corrected —
                        p-values will be reported as nominal.
                    </p>
                )}
            </div>
        </details>
    )
}

export default AnalysisSettings
