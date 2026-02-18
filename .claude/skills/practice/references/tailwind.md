# Tailwind CSS Exercises

Exercises based on styling patterns from `frontend/src/components/`.

## Beginner

### Exercise 1: Card Component with Hover Effect
**Task**: Create a `StatCard` component that displays a label, value, and optional trend indicator. Use Tailwind for: white background, rounded corners, shadow, padding, hover shadow increase, and transition animation.
**Starter code**:
```typescript
interface StatCardProps {
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'neutral';
}

// TODO: Create StatCard with:
//   Container: bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow
//   Label: text-sm text-gray-500 uppercase tracking-wide
//   Value: text-2xl font-bold text-gray-900 mt-2
//   Trend indicator: text-green-600 (up), text-red-600 (down), text-gray-400 (neutral)
//   Trend arrow: ↑ or ↓ or →
```
**Test criteria**:
- Card has correct background, shadow, padding, rounded corners
- Hover increases shadow, transition is smooth
- Trend color matches direction
**Key concepts**: bg, rounded, shadow, hover:, transition, text colors, conditional classes

### Exercise 2: Responsive Grid Layout
**Task**: Create a responsive grid that shows 1 column on mobile, 2 on tablet, 3 on desktop, 4 on large screens. Cards should have consistent gap spacing.
**Starter code**:
```typescript
interface GridLayoutProps {
  items: { id: string; title: string; value: number }[];
}

// TODO: Create GridLayout with:
//   Grid: grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4
//   Each item: StatCard from Exercise 1
//   Container: max-w-7xl mx-auto px-4
```
**Test criteria**:
- 1/2/3/4 columns at mobile/tablet/desktop/xl breakpoints
- Consistent gap between cards, centered with max width
**Key concepts**: grid, grid-cols, responsive breakpoints (md, lg, xl), gap, max-w, mx-auto

## Intermediate

### Exercise 3: Data Table with Sort Indicators
**Task**: Create a gene results table with alternating row colors, sortable column headers with arrow indicators, and significance highlighting. Use Tailwind for all styling.
**Starter code**:
```typescript
// TODO: Create GeneTable with:
//   Table: min-w-full divide-y divide-gray-200
//   Header: bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase
//   Sort indicator: inline arrow ▲/▼ next to active sort column
//   Rows: alternating bg-white/bg-gray-50 (even:bg-gray-50)
//   Significant rows: highlighted with bg-yellow-50 border-l-4 border-yellow-400
//   HR cell: text-red-600 if > 1.5, text-green-600 if < 0.67, text-gray-900 otherwise
//   P-value cell: font-mono text-sm
//   Hover: hover:bg-blue-50 cursor-pointer
```
**Test criteria**:
- Alternating row colors, sort arrows on active column
- Significant rows highlighted, HR color-coded
**Key concepts**: divide, even:, hover:, border-l, conditional colors, font-mono

### Exercise 4: Badge Component with Variants
**Task**: Create a reusable `Badge` component with color variants (success, danger, warning, info, neutral) and size variants (sm, md, lg). Use a className builder function.
**Starter code**:
```typescript
type BadgeVariant = 'success' | 'danger' | 'warning' | 'info' | 'neutral';
type BadgeSize = 'sm' | 'md' | 'lg';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
}

// TODO: Create variant color map:
//   success: bg-green-100 text-green-800
//   danger: bg-red-100 text-red-800
//   warning: bg-amber-100 text-amber-800
//   info: bg-blue-100 text-blue-800
//   neutral: bg-gray-100 text-gray-800

// TODO: Create size map:
//   sm: px-1.5 py-0.5 text-xs
//   md: px-2 py-1 text-sm
//   lg: px-3 py-1.5 text-base

// TODO: Base classes: inline-flex items-center rounded-full font-medium
```
**Test criteria**:
- Each variant has correct background and text color
- Each size has correct padding and font size
- Base classes always applied (rounded-full, inline-flex)
**Key concepts**: Variant patterns, className builder, rounded-full, inline-flex

## Advanced

### Exercise 5: Dashboard Layout with Sidebar
**Task**: Create a full dashboard layout with: fixed sidebar (collapsible), top header bar, main content area with scroll. Sidebar has navigation items with active state highlighting.
**Starter code**:
```typescript
// TODO: Create DashboardLayout with:
//   Sidebar: fixed left-0 top-0 h-screen w-64 bg-gray-900 text-white
//     Collapsed: w-16 (icons only)
//     Toggle button at bottom
//     Nav items: flex items-center px-4 py-3 hover:bg-gray-700 rounded-lg
//     Active item: bg-gray-700 border-l-4 border-blue-500
//   Header: fixed top-0 left-64 right-0 h-16 bg-white border-b shadow-sm z-10
//     Title, search bar, user avatar
//   Main: ml-64 mt-16 p-6 bg-gray-100 min-h-screen
//     Content area with overflow-y-auto
//   Responsive: sidebar hidden on mobile, shown via hamburger menu
```
**Test criteria**:
- Sidebar fixed, content offset by sidebar width
- Collapse toggles width, active nav highlighted
- Header spans remaining width, content scrolls independently
**Key concepts**: fixed positioning, z-index, responsive sidebar, flexbox layout

### Exercise 6: Form with Validation States
**Task**: Create a search configuration form with Tailwind-styled validation states. Include: valid (green border), invalid (red border with error message), focused (blue ring), disabled (gray background). Support floating labels.
**Starter code**:
```typescript
// TODO: Create FormField component with states:
//   Base: w-full px-4 py-3 border rounded-lg transition-colors
//   Valid: border-green-500 focus:ring-green-200
//   Invalid: border-red-500 focus:ring-red-200
//     Error message: text-sm text-red-600 mt-1
//   Focused: ring-2 ring-blue-200 border-blue-500 outline-none
//   Disabled: bg-gray-100 text-gray-500 cursor-not-allowed
//   Floating label: absolute text-sm transition-all
//     Unfocused+empty: top-3 text-gray-400 text-base
//     Focused or filled: -top-2.5 text-xs text-blue-600 bg-white px-1

// TODO: Create SearchConfigForm using FormField for:
//   Query input (required, maxLength 500)
//   Dataset count (number, 1-50)
//   Organism dropdown
//   Submit button: w-full bg-blue-600 text-white py-3 rounded-lg
//     hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
```
**Test criteria**:
- Correct border colors for each validation state
- Floating labels transition on focus/blur
- Error messages appear/disappear with animation
- Submit button disabled state styled correctly
**Key concepts**: focus:ring, border colors, disabled:, transition, absolute positioning
