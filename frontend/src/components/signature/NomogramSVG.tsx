import React from 'react'
import { PrognosticModel } from '../../services/api'

interface NomogramProps {
    model: PrognosticModel
}

/**
 * F18 — Clinical nomogram rendered as a custom SVG directly from the locked
 * Cox coefficients. Each gene gets a points axis; the per-gene contribution is
 * coefficient * (+1 SD of expression), scaled so the most influential gene
 * spans 0–100 points. Predicts outcome risk; advisory, research use only.
 */
const NomogramSVG: React.FC<NomogramProps> = ({ model }) => {
    const rows = React.useMemo(() => {
        // Magnitude of one-SD effect on the linear predictor = |coefficient|.
        const effects = model.genes.map((g) => ({
            symbol: g.gene_symbol,
            coef: g.coefficient,
            hr: g.hazard_ratio,
            magnitude: Math.abs(g.coefficient),
            direction: g.coefficient >= 0 ? 'risk' : 'protective',
        }))
        const maxMag = Math.max(...effects.map((e) => e.magnitude), 1e-6)
        return effects
            .map((e) => ({ ...e, points: (e.magnitude / maxMag) * 100 }))
            .sort((a, b) => b.points - a.points)
    }, [model])

    const width = 560
    const left = 130
    const axisWidth = width - left - 40
    const rowH = 26
    const top = 50
    const height = top + rows.length * rowH + 40

    const ticks = [0, 25, 50, 75, 100]

    return (
        <div className="overflow-x-auto">
            <svg width={width} height={height} role="img" aria-label="Predictive risk nomogram">
                {/* Points header axis */}
                <text x={left - 8} y={top - 22} textAnchor="end" fontSize={11} fill="#374151" fontWeight={600}>
                    Points
                </text>
                {ticks.map((t) => {
                    const x = left + (t / 100) * axisWidth
                    return (
                        <g key={`tick-${t}`}>
                            <line x1={x} y1={top - 16} x2={x} y2={top - 10} stroke="#9ca3af" />
                            <text x={x} y={top - 20} textAnchor="middle" fontSize={9} fill="#6b7280">
                                {t}
                            </text>
                        </g>
                    )
                })}
                <line x1={left} y1={top - 10} x2={left + axisWidth} y2={top - 10} stroke="#d1d5db" />

                {/* One row per gene */}
                {rows.map((r, i) => {
                    const y = top + i * rowH + 8
                    const barW = (r.points / 100) * axisWidth
                    const color = r.direction === 'risk' ? '#ef4444' : '#3b82f6'
                    return (
                        <g key={r.symbol}>
                            <text x={left - 10} y={y + 4} textAnchor="end" fontSize={11} fill="#111827" fontWeight={500}>
                                {r.symbol}
                            </text>
                            <line x1={left} y1={y} x2={left + axisWidth} y2={y} stroke="#f3f4f6" />
                            <line x1={left} y1={y} x2={left + barW} y2={y} stroke={color} strokeWidth={3} />
                            <circle cx={left + barW} cy={y} r={4} fill={color} />
                            <text x={left + axisWidth + 6} y={y + 4} fontSize={9} fill="#6b7280">
                                HR {r.hr.toFixed(2)}
                            </text>
                        </g>
                    )
                })}
            </svg>
            <div className="flex gap-4 text-xs mt-1 ml-2">
                <span className="flex items-center gap-1">
                    <span className="inline-block w-3 h-0.5 bg-red-500" /> Higher expression → higher risk
                </span>
                <span className="flex items-center gap-1">
                    <span className="inline-block w-3 h-0.5 bg-blue-500" /> Higher expression → protective
                </span>
            </div>
            <p className="text-[11px] text-gray-400 mt-1 ml-2">
                Points ∝ |Cox coefficient| per +1 SD of expression. Add the points for a patient's genes to gauge
                relative predicted risk burden. Advisory, research use only — not a prescription.
            </p>
        </div>
    )
}

export default NomogramSVG
