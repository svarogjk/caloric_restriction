# Recharts Exercises

Exercises based on patterns from `frontend/src/components/KaplanMeierPlot.tsx` and `VolcanoPlot.tsx`.

## Beginner

### Exercise 1: Basic Line Chart
**Task**: Create a `SurvivalOverviewChart` that renders a simple line chart showing survival probability over time. Include `XAxis` (Time in months), `YAxis` (Survival Probability, domain [0,1]), `Tooltip`, and `Legend`. Use dummy data.
**Starter code**:
```typescript
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface SurvivalPoint { time: number; probability: number; }

// TODO: Create sample data (10+ points from 1.0 decreasing)
// TODO: Create SurvivalOverviewChart component that renders:
//   - ResponsiveContainer width="100%" height={400}
//   - LineChart with data
//   - XAxis with label "Time (months)"
//   - YAxis with domain [0, 1] and label "Survival Probability"
//   - Line with stroke color and dot={false}
//   - Tooltip and Legend
```
**Test criteria**:
- Chart renders with correct axes, labels, and domain
- Line connects all data points, responsive container fills parent
**Key concepts**: LineChart, XAxis, YAxis, ResponsiveContainer, Tooltip, Legend

### Exercise 2: Bar Chart with Categories
**Task**: Create a `GeneCountChart` showing the number of significant genes per dataset as a bar chart. Color bars by significance level (high=red, medium=amber, low=gray). Add a custom tooltip showing dataset details.
**Starter code**:
```typescript
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';

// TODO: Define data interface and sample data
// TODO: Create color function based on gene count thresholds
// TODO: Create GeneCountChart with BarChart and Cell for per-bar coloring
// TODO: Create custom tooltip component
```
**Test criteria**:
- Bars colored by threshold, tooltip shows dataset details
- Axes labeled correctly, responsive sizing
**Key concepts**: BarChart, Bar, Cell for individual colors, custom tooltip

## Intermediate

### Exercise 3: Step-Function Kaplan-Meier Chart
**Task**: Create a KM plot with `type="stepAfter"` showing high vs low expression groups. Include two lines with different colors (red for high risk, green for protective), proper step function rendering, and a reference line at survival probability 0.5.
**Starter code**:
```typescript
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ReferenceLine } from 'recharts';

interface KMDataPoint { time: number; survival_high: number; survival_low: number; }

// TODO: Create sample KM data with step decreases
// TODO: Create KaplanMeierChart with:
//   - Two Line components with type="stepAfter"
//   - High expression line in #ef4444 (red)
//   - Low expression line in #22c55e (green)
//   - ReferenceLine at y=0.5 (median survival indicator)
//   - YAxis domain [0, 1]
//   - Custom tooltip showing time and both survival probabilities
```
**Test criteria**:
- Lines render as step functions (flat then vertical drop)
- Reference line at 0.5, correct colors for each group
**Key concepts**: type="stepAfter", ReferenceLine, dual lines, step functions

### Exercise 4: Scatter Chart with Color Coding
**Task**: Create a `VolcanoPlot` scatter chart where X = log2(hazard_ratio), Y = -log10(p_value). Color dots by significance: red (HR>1.5, p<0.05), blue (HR<0.67, p<0.05), gray (not significant). Add reference lines at x=0 and y=-log10(0.05).
**Starter code**:
```typescript
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, Cell, ReferenceLine } from 'recharts';

interface GenePoint { x: number; y: number; gene: string; color: string; }

// TODO: Transform gene data into plot coordinates using useMemo
// TODO: Create getSignificanceColor function
// TODO: Render ScatterChart with Cell-colored dots
// TODO: Add reference lines for significance thresholds
```
**Test criteria**:
- Coordinates correctly transformed (log2 HR, -log10 p-value)
- Colors match significance criteria, reference lines at correct positions
**Key concepts**: ScatterChart, log transformations, Cell colors, ReferenceLine

## Advanced

### Exercise 5: Multi-Dataset Chart with Selector
**Task**: Create a KM plot that shows curves from multiple datasets. Include a dataset selector (checkboxes) to toggle which datasets are visible. Each dataset gets a unique color from a palette. Use useState for selection and useMemo for visible data transformation.
**Starter code**:
```typescript
interface DatasetKMData { accession: string; title: string; km_data: KMDataPoint[]; }

// TODO: Create MultiDatasetKMPlot that:
//   1. useState for selectedDatasets (Set<string>)
//   2. useMemo to merge visible datasets into combined chart data
//   3. Render checkbox list for dataset selection
//   4. Render LineChart with one Line per selected dataset
//   5. Use color palette (array of hex colors) for consistent coloring
//   6. Legend showing dataset accession labels
```
**Test criteria**:
- Toggling datasets adds/removes lines from chart
- Colors consistent (same dataset always same color), useMemo prevents re-computation
**Key concepts**: Dynamic Line rendering, useState for selection, useMemo, color palettes

### Exercise 6: Custom Tooltip with Rich Display
**Task**: Create a custom Recharts tooltip component that shows: gene symbol, hazard ratio with colored indicator, p-value in scientific notation, confidence interval, and a mini significance bar. The tooltip should handle edge cases (missing data, extreme values).
**Starter code**:
```typescript
import { TooltipProps } from 'recharts';

// TODO: Create CustomGeneTooltip component receiving TooltipProps
// TODO: Handle active/inactive states
// TODO: Format p-value in scientific notation (e.g., 1.23e-5)
// TODO: Color-code HR indicator (red > 1, green < 1)
// TODO: Show CI as "95% CI: [lower, upper]"
// TODO: Mini bar showing relative significance strength
```
**Test criteria**:
- Renders correctly when active with payload, renders nothing when inactive
- P-value formatted in scientific notation, HR color-coded
**Key concepts**: Custom tooltip, TooltipProps, number formatting, conditional styling
