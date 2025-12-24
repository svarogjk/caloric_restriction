import React from 'react'
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts'
import { GeneSurvival } from '../store/searchSlice'

interface VolcanoPlotProps {
  data: GeneSurvival[]
  onGeneClick: (gene: GeneSurvival) => void
  selectedGeneId?: string | null
}

interface TransformedGene {
  gene_id: string
  gene_symbol: string | null
  hazard_ratio: number
  log_hazard_ratio: number
  negLog10PValue: number
  p_value: number
  color: string
  predominant_risk: string
  n_datasets: number
  original: GeneSurvival
}

const VolcanoPlot: React.FC<VolcanoPlotProps> = ({ data, onGeneClick, selectedGeneId }) => {
  // Transform data for volcano plot: x-axis is log(Hazard Ratio), y-axis is -log10(p-value)
  const transformedData = React.useMemo<TransformedGene[]>(() => {
    return data.map((gene) => ({
      gene_id: gene.gene_id,
      gene_symbol: gene.gene_symbol,
      hazard_ratio: gene.avg_hazard_ratio,
      // Use log2 of hazard ratio for better visualization (centered at 0)
      log_hazard_ratio: Math.log2(gene.avg_hazard_ratio),
      negLog10PValue: -Math.log10(gene.avg_log_rank_p_value),
      p_value: gene.avg_log_rank_p_value,
      color: getGeneColor(gene.avg_hazard_ratio, gene.avg_log_rank_p_value),
      predominant_risk: gene.predominant_risk,
      n_datasets: gene.n_datasets,
      original: gene,
    }))
  }, [data])

  function getGeneColor(hazardRatio: number, pValue: number): string {
    const negLog10P = -Math.log10(pValue)
    const significanceThreshold = -Math.log10(0.05)
    
    // High risk (HR > 1.5) and significant
    if (negLog10P > significanceThreshold && hazardRatio > 1.5) {
      return '#ef4444' // Red - high risk
    }
    // Protective (HR < 0.67) and significant
    if (negLog10P > significanceThreshold && hazardRatio < 0.67) {
      return '#3b82f6' // Blue - protective
    }
    // Significant but moderate effect
    if (negLog10P > significanceThreshold) {
      return '#f59e0b' // Amber - moderate
    }
    return '#9ca3af' // Gray - not significant
  }

  const CustomTooltip: React.FC<any> = ({ active, payload }) => {
    if (active && payload && payload[0]) {
      const data = payload[0].payload as TransformedGene
      return (
        <div className="bg-white p-3 border border-gray-300 rounded shadow-lg z-50">
          <p className="font-semibold text-gray-800">
            {data.gene_symbol || data.gene_id}
          </p>
          {data.gene_symbol && data.gene_symbol !== data.gene_id && (
            <p className="text-xs text-gray-500">{data.gene_id}</p>
          )}
          <div className="mt-2 space-y-1">
            <p className="text-sm text-gray-600">
              <span className="font-medium">Hazard Ratio:</span>{' '}
              <span className={data.hazard_ratio > 1 ? 'text-red-600' : 'text-blue-600'}>
                {data.hazard_ratio.toFixed(2)}
              </span>
            </p>
            <p className="text-sm text-gray-600">
              <span className="font-medium">P-value:</span>{' '}
              {data.p_value < 0.001
                ? data.p_value.toExponential(2)
                : data.p_value.toFixed(4)}
            </p>
            <p className="text-sm text-gray-600">
              <span className="font-medium">Datasets:</span> {data.n_datasets}
            </p>
            <p className={`text-sm font-medium ${
              data.predominant_risk === 'high_risk' ? 'text-red-600' : 'text-blue-600'
            }`}>
              {data.predominant_risk === 'high_risk' ? '↑ High Risk' : '↓ Protective'}
            </p>
          </div>
          <p className="text-xs text-gray-400 mt-2 italic">Click to view Kaplan-Meier curves</p>
        </div>
      )
    }
    return null
  }

  const handleClick = (data: any) => {
    if (data && data.original) {
      onGeneClick(data.original)
    }
  }

  // Calculate axis domains with some padding
  const xMin = Math.min(...transformedData.map((d) => d.log_hazard_ratio), -1)
  const xMax = Math.max(...transformedData.map((d) => d.log_hazard_ratio), 1)
  const yMax = Math.max(...transformedData.map((d) => d.negLog10PValue), 3)

  return (
    <div className="w-full bg-white rounded-lg p-4">
      <h3 className="text-lg font-semibold text-gray-800 mb-2 text-center">
        Survival Volcano Plot
      </h3>
      <p className="text-sm text-gray-500 mb-4 text-center">
        Click on a gene to view Kaplan-Meier survival curves
      </p>
      <div className="h-96">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 20, right: 30, bottom: 40, left: 50 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.5} />
            <XAxis
              type="number"
              dataKey="log_hazard_ratio"
              name="log2(Hazard Ratio)"
              domain={[xMin - 0.5, xMax + 0.5]}
              tickFormatter={(value) => value.toFixed(1)}
              label={{
                value: 'log₂(Hazard Ratio)',
                position: 'insideBottom',
                offset: -10,
                style: { textAnchor: 'middle' },
              }}
            />
            <YAxis
              type="number"
              dataKey="negLog10PValue"
              name="-log10(p-value)"
              domain={[0, yMax + 1]}
              label={{
                value: '-log₁₀(p-value logrank)',
                angle: -90,
                position: 'insideLeft',
                style: { textAnchor: 'middle' },
              }}
            />
            {/* Reference lines */}
            <ReferenceLine x={0} stroke="#6b7280" strokeDasharray="3 3" />
            <ReferenceLine
              y={-Math.log10(0.05)}
              stroke="#6b7280"
              strokeDasharray="3 3"
              label={{
                value: 'p=0.05',
                position: 'right',
                fill: '#6b7280',
                fontSize: 12,
              }}
            />
            <ReferenceLine
              x={Math.log2(1.5)}
              stroke="#fca5a5"
              strokeDasharray="5 5"
              opacity={0.5}
            />
            <ReferenceLine
              x={Math.log2(0.67)}
              stroke="#93c5fd"
              strokeDasharray="5 5"
              opacity={0.5}
            />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              content={<CustomTooltip />}
            />
            <Legend
              verticalAlign="top"
              height={36}
              payload={[
                { value: 'High Risk (HR > 1.5)', type: 'circle', color: '#ef4444' },
                { value: 'Protective (HR < 0.67)', type: 'circle', color: '#3b82f6' },
                { value: 'Moderate Effect', type: 'circle', color: '#f59e0b' },
                { value: 'Not Significant', type: 'circle', color: '#9ca3af' },
              ]}
            />
            <Scatter
              name="Genes"
              data={transformedData}
              fill="#8884d8"
              onClick={handleClick}
              cursor="pointer"
            >
              {transformedData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.color}
                  stroke={selectedGeneId === entry.gene_id ? '#000' : entry.color}
                  strokeWidth={selectedGeneId === entry.gene_id ? 2 : 1}
                  r={selectedGeneId === entry.gene_id ? 8 : entry.n_datasets > 3 ? 6 : 4}
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-4 flex gap-6 justify-center text-sm flex-wrap">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-red-500 rounded-full"></div>
          <span className="text-gray-600">High Risk (HR {'>'} 1.5)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
          <span className="text-gray-600">Protective (HR {'<'} 0.67)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-amber-500 rounded-full"></div>
          <span className="text-gray-600">Moderate Effect</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-gray-400 rounded-full"></div>
          <span className="text-gray-600">Not Significant</span>
        </div>
      </div>
      <p className="text-xs text-gray-400 mt-2 text-center">
        Dot size indicates number of datasets where gene was found significant
      </p>
    </div>
  )
}

export default VolcanoPlot
