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
    <div className="w-48">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        LLM Model
      </label>
      <select
        value={selectedModel}
        onChange={(e) => onChange(e.value)}
        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white transition"
      >
        <option value="mistral">Mistral</option>
        <option value="claude">Claude</option>
      </select>
    </div>
  )
}

export default ModelSelector
