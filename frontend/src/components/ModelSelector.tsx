import React from 'react'

interface ModelSelectorProps {
  selectedModel: string
  models: string[]
  onChange: (value: string) => void
}

const ModelSelector: React.FC<ModelSelectorProps> = ({
  selectedModel,
  models,
  onChange,
}) => {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Analysis Model
      </label>
      <select
        value={selectedModel}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white transition"
      >
        <option value="all-models">All Models</option>
        {models.map((model) => (
          <option key={model} value={model}>
            {model}
          </option>
        ))}
      </select>
    </div>
  )
}

export default ModelSelector
