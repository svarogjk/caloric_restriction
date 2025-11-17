# Genomic Data Search Frontend

A modern React + TypeScript frontend for searching and analyzing differential gene expression datasets.

## Features

- 🔍 **Search Interface**: Search genomic datasets by gene name, dataset name, or disease condition
- 📊 **Model Selection**: Filter results by different analysis models
- 📈 **Volcano Plot**: Interactive visualization of differential expression data
- 📥 **Data Export**: Download results in CSV or JSON format
- 🎨 **Modern UI**: Built with Tailwind CSS for a clean, responsive design
- 🔄 **State Management**: Redux Toolkit for predictable state management

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Redux Toolkit** - State management
- **Tailwind CSS** - Styling
- **Recharts** - Data visualization
- **Vite** - Build tool
- **Axios** - HTTP client

## Installation

```bash
npm install
```

## Development

Start the development server:

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## Build

Build for production:

```bash
npm run build
```

## API Integration

The frontend expects the backend API to be available at `/api`. Configure the proxy in `vite.config.ts` to point to your backend server.

### Expected API Endpoints

- `GET /api/search?q=query&model=model-name` - Search datasets
- `GET /api/datasets/:id` - Get dataset details
- `GET /api/datasets/:id/download?format=csv|json` - Download dataset
- `GET /api/models` - Get available analysis models

## Project Structure

```
src/
├── components/          # React components
│   ├── SearchPage.tsx  # Main search interface
│   ├── SearchBar.tsx   # Search input component
│   ├── ModelSelector.tsx # Model dropdown
│   ├── DatasetList.tsx # List of search results
│   ├── DatasetCard.tsx # Individual dataset card
│   └── VolcanoPlot.tsx # Volcano plot visualization
├── store/              # Redux store
│   ├── store.ts       # Redux store configuration
│   └── searchSlice.ts # Search state and actions
├── services/           # API services
│   └── api.ts         # API client
├── App.tsx            # Root component
└── main.tsx           # Entry point
```

## Features Explained

### Search Interface
- Input field for queries with Enter key support
- Real-time query validation
- Loading state indication

### Model Selection
- Dropdown to filter by analysis model
- "All Models" option for comprehensive search

### Results Display
- List of matching datasets with descriptions
- Click to expand for detailed analysis
- Responsive card-based layout

### Volcano Plot
- Interactive scatter plot of gene expression
- Color coding:
  - Red: Upregulated genes (log2FC > 1, p < 0.05)
  - Blue: Downregulated genes (log2FC < -1, p < 0.05)
  - Gray: Not significant
- Hover tooltips with gene details
- Responsive sizing

### Data Export
- Download in CSV format for spreadsheet analysis
- Download in JSON format for programmatic access
- Error handling and user feedback

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## License

MIT
