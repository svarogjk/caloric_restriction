import React from 'react'

interface DatasetCountSelectorProps {
  value: number
  onChange: (value: number) => void
}

const DatasetCountSelector: React.FC<DatasetCountSelectorProps> = ({
  value,
  onChange,
}) => {
  const options = [10, 20, 50, 100, 500, 1000]

  return (
    <div className="w-48">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Datasets to Search
      </label>
      <select
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white transition"
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </div>
  )
}

export default DatasetCountSelector
