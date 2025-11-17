import React from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Dataset, expandDataset } from '../store/searchSlice'
import { RootState } from '../store/store'
import DatasetCard from './DatasetCard'

interface DatasetListProps {
  datasets: Dataset[]
}

const DatasetList: React.FC<DatasetListProps> = ({ datasets }) => {
  const dispatch = useDispatch()
  const expandedDatasetId = useSelector(
    (state: RootState) => state.search.expandedDatasetId
  )

  return (
    <div className="space-y-4">
      {datasets.map((dataset) => (
        <DatasetCard
          key={dataset.id}
          dataset={dataset}
          isExpanded={expandedDatasetId === dataset.id}
          onToggle={() => dispatch(expandDataset(dataset.id))}
        />
      ))}
    </div>
  )
}

export default DatasetList
