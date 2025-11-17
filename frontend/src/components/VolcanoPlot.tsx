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
} from 'recharts'

interface GeneExpression {
  gene: string
  log2FoldChange: number
  pValue: number
}

interface VolcanoPlotProps {
  data: GeneExpression[]
}

const VolcanoPlot: React.FC<VolcanoPlotProps> = ({ data }) => {
  // Transform data for volcano plot: x-axis is log2FoldChange, y-axis is -log10(pValue)
  const transformedData = React.useMemo(() => {
    return data.map((item) => ({
      ...item,
      negLog10PValue: -Math.log10(item.pValue),
      color: getGeneColor(item.log2FoldChange, item.pValue),
    }))
  }, [data])

  const getGeneColor = (log2FC: number, pValue: number): string => {
    const logPValue = -Math.log10(pValue)
    // Red: upregulated (log2FC > 1, p < 0.05)
    // Blue: downregulated (log2FC < -1, p < 0.05)
    // Gray: not significant
    if (logPValue > -Math.log10(0.05)) {
      if (log2FC > 1) return '#ef4444' // Red
      if (log2FC < -1) return '#3b82f6' // Blue
    }
    return '#9ca3af' // Gray
  }

  const CustomTooltip: React.FC<any> = ({ active, payload }) => {
    if (active && payload && payload[0]) {
      const data = payload[0].payload
      return (
        <div className="bg-white p-3 border border-gray-300 rounded shadow-lg">
          <p className="font-semibold text-gray-800">{data.gene}</p>
          <p className="text-sm text-gray-600">
            log2FC: {data.log2FoldChange.toFixed(2)}
          </p>
          <p className="text-sm text-gray-600">
            p-value: {data.pValue.toExponential(2)}
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <div className="w-full h-96 bg-white rounded-lg p-4">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            type="number"
            dataKey="log2FoldChange"
            name="log2(Fold Change)"
            label={{ value: 'log2(Fold Change)', position: 'insideBottomRight', offset: -5 }}
          />
          <YAxis
            type="number"
            dataKey="negLog10PValue"
            name="-log10(p-value)"
            label={{ value: '-log10(p-value)', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip cursor={{ strokeDasharray: '3 3' }} content={<CustomTooltip />} />
          <Legend />
          <Scatter
            name="Gene Expression"
            data={transformedData}
            fill="#8884d8"
            shape="circle"
          >
            {transformedData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
      <div className="mt-4 flex gap-4 justify-center text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-red-500 rounded-full"></div>
          <span>Upregulated</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
          <span>Downregulated</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-gray-400 rounded-full"></div>
          <span>Not Significant</span>
        </div>
      </div>
    </div>
  )
}

export default VolcanoPlot
