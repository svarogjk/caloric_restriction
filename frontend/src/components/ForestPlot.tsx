import React from 'react'
import { HeterogeneityStats } from '../store/chatSlice'

interface DatasetPoint {
  dataset_id: string
  dataset_title: string
  hazard_ratio: number
  hazard_ratio_ci_lower: number
  hazard_ratio_ci_upper: number
  n_samples: number
  cox_p_value: number
}

interface ForestPlotProps {
  geneName: string
  datasets: DatasetPoint[]
  pooledHR: number
  heterogeneityStats?: HeterogeneityStats | null
}

export const ForestPlot: React.FC<ForestPlotProps> = ({
  geneName,
  datasets,
  pooledHR,
  heterogeneityStats,
}) => {
  // SVG layout constants
  const svgWidth = 680
  const rowHeight = 32
  const labelWidth = 180
  const plotLeft = labelWidth + 20
  const plotRight = svgWidth - 120
  const plotWidth = plotRight - plotLeft
  const headerHeight = 30
  const footerHeight = heterogeneityStats ? 50 : 20
  const svgHeight =
    headerHeight + datasets.length * rowHeight + rowHeight + footerHeight + 20

  // X-axis: log scale for HR. Range: 0.25 to 4.0
  const hrMin = 0.25
  const hrMax = 4.0
  const logMin = Math.log(hrMin)
  const logMax = Math.log(hrMax)

  const hrToX = (hr: number): number => {
    const logHR = Math.log(Math.max(hrMin, Math.min(hrMax, hr)))
    return plotLeft + ((logHR - logMin) / (logMax - logMin)) * plotWidth
  }

  const nullX = hrToX(1.0)

  const xTicks = [0.25, 0.5, 1.0, 2.0, 4.0]

  return (
    <div className="overflow-x-auto">
      <h3 className="text-sm font-semibold text-gray-700 mb-2">
        {geneName} — Per-Dataset Hazard Ratios
      </h3>
      <svg width={svgWidth} height={svgHeight} className="font-mono text-xs">
        {/* Column headers */}
        <text
          x={plotLeft + plotWidth / 2}
          y={18}
          textAnchor="middle"
          fontSize={11}
          fill="#6b7280"
          fontFamily="sans-serif"
        >
          Hazard Ratio (95% CI)
        </text>
        <text
          x={svgWidth - 60}
          y={18}
          textAnchor="middle"
          fontSize={11}
          fill="#6b7280"
          fontFamily="sans-serif"
        >
          HR [95% CI]
        </text>

        {/* Null effect line at HR=1 */}
        <line
          x1={nullX}
          y1={headerHeight}
          x2={nullX}
          y2={headerHeight + (datasets.length + 1) * rowHeight}
          stroke="#9ca3af"
          strokeWidth={1}
          strokeDasharray="4 3"
        />

        {/* X-axis ticks and labels */}
        {xTicks.map((tick) => (
          <g key={tick}>
            <line
              x1={hrToX(tick)}
              y1={headerHeight + (datasets.length + 1) * rowHeight}
              x2={hrToX(tick)}
              y2={headerHeight + (datasets.length + 1) * rowHeight + 5}
              stroke="#9ca3af"
              strokeWidth={1}
            />
            <text
              x={hrToX(tick)}
              y={headerHeight + (datasets.length + 1) * rowHeight + 16}
              textAnchor="middle"
              fontSize={10}
              fill="#6b7280"
              fontFamily="sans-serif"
            >
              {tick}
            </text>
          </g>
        ))}

        {/* X-axis baseline */}
        <line
          x1={plotLeft}
          y1={headerHeight + (datasets.length + 1) * rowHeight}
          x2={plotRight}
          y2={headerHeight + (datasets.length + 1) * rowHeight}
          stroke="#9ca3af"
          strokeWidth={1}
        />

        {/* Per-dataset rows */}
        {datasets.map((ds, i) => {
          const y = headerHeight + i * rowHeight + rowHeight / 2
          const hrX = hrToX(ds.hazard_ratio)
          const ciLowX = hrToX(ds.hazard_ratio_ci_lower)
          const ciHighX = hrToX(ds.hazard_ratio_ci_upper)
          const color = ds.hazard_ratio > 1 ? '#ef4444' : '#3b82f6'
          const squareSize = Math.min(8, Math.max(4, Math.sqrt(ds.n_samples) * 0.4))

          return (
            <g key={ds.dataset_id}>
              {/* Dataset label */}
              <text
                x={labelWidth}
                y={y + 4}
                textAnchor="end"
                fontSize={10}
                fill="#374151"
                fontFamily="sans-serif"
              >
                {ds.dataset_id.length > 22
                  ? ds.dataset_id.slice(0, 22) + '\u2026'
                  : ds.dataset_id}
              </text>

              {/* CI horizontal error bar */}
              <line
                x1={ciLowX}
                y1={y}
                x2={ciHighX}
                y2={y}
                stroke={color}
                strokeWidth={1.5}
              />
              {/* Left whisker */}
              <line
                x1={ciLowX}
                y1={y - 4}
                x2={ciLowX}
                y2={y + 4}
                stroke={color}
                strokeWidth={1.5}
              />
              {/* Right whisker */}
              <line
                x1={ciHighX}
                y1={y - 4}
                x2={ciHighX}
                y2={y + 4}
                stroke={color}
                strokeWidth={1.5}
              />

              {/* Square marker sized by sqrt(n) */}
              <rect
                x={hrX - squareSize / 2}
                y={y - squareSize / 2}
                width={squareSize}
                height={squareSize}
                fill={color}
              />

              {/* HR text on right */}
              <text
                x={svgWidth - 10}
                y={y + 4}
                textAnchor="end"
                fontSize={10}
                fill="#374151"
                fontFamily="monospace"
              >
                {ds.hazard_ratio.toFixed(2)} [{ds.hazard_ratio_ci_lower.toFixed(2)}
                {'\u2013'}
                {ds.hazard_ratio_ci_upper.toFixed(2)}]
              </text>
            </g>
          )
        })}

        {/* Pooled estimate row — diamond shape */}
        {(() => {
          const pooledY =
            headerHeight + datasets.length * rowHeight + rowHeight / 2
          const pooledX = hrToX(pooledHR)
          const diamondW = 10
          const diamondH = 8
          return (
            <g>
              <line
                x1={plotLeft}
                y1={pooledY - 1}
                x2={plotRight}
                y2={pooledY - 1}
                stroke="#e5e7eb"
                strokeWidth={1}
              />
              <text
                x={labelWidth}
                y={pooledY + 4}
                textAnchor="end"
                fontSize={10}
                fill="#374151"
                fontWeight="bold"
                fontFamily="sans-serif"
              >
                Pooled
              </text>
              <polygon
                points={`${pooledX},${pooledY - diamondH} ${pooledX + diamondW},${pooledY} ${pooledX},${pooledY + diamondH} ${pooledX - diamondW},${pooledY}`}
                fill="#7c3aed"
              />
              <text
                x={svgWidth - 10}
                y={pooledY + 4}
                textAnchor="end"
                fontSize={10}
                fill="#374151"
                fontWeight="bold"
                fontFamily="monospace"
              >
                {pooledHR.toFixed(2)}
              </text>
            </g>
          )
        })()}

        {/* Heterogeneity stats footer */}
        {heterogeneityStats && (
          <text
            x={plotLeft}
            y={headerHeight + (datasets.length + 1) * rowHeight + 38}
            fontSize={10}
            fill="#6b7280"
            fontFamily="sans-serif"
          >
            {`Heterogeneity: I\u00B2 = ${heterogeneityStats.i_squared != null ? heterogeneityStats.i_squared.toFixed(1) : '\u2014'}%,  Q = ${heterogeneityStats.q_statistic != null ? heterogeneityStats.q_statistic.toFixed(2) : '\u2014'},  p = ${heterogeneityStats.p_heterogeneity != null ? heterogeneityStats.p_heterogeneity.toFixed(3) : '\u2014'}`}
          </text>
        )}
      </svg>
    </div>
  )
}
