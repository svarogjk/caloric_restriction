import React from 'react'

interface RankingMultiplierSelectorProps {
  value: number
  onChange: (value: number) => void
}

const RankingMultiplierSelector: React.FC<RankingMultiplierSelectorProps> = ({
  value,
  onChange,
}) => {
  return (
    <div className="w-48">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Ranking Multiplier
      </label>
      <div className="flex items-center gap-4">
        <input
          type="range"
          min="1"
          max="10"
          value={value}
          onChange={(e) => onChange(parseInt(e.target.value))}
          className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
        />
        <span className="text-sm font-semibold text-gray-700 w-8 text-center">
          {value}x
        </span>
      </div>
      <p className="text-xs text-gray-500 mt-1">
        Higher = more thorough ranking
      </p>
    </div>
  )
}

export default RankingMultiplierSelector
