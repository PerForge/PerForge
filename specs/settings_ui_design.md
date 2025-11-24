# Advanced Settings UI Design

## Navigation Placement

### Sidebar Integration
The "Advanced Settings" link will be added to the **Settings dropdown** (gear icon) in the top-right of the sidebar.

**Location in Sidebar:**
```
┌─ Sidebar ───────────────────────────────────────────────┐
│ [Home] [Tests] [Templates] [Graphs] ... [⚙️ Settings ▼] │
└─────────────────────────────────────────────────────────┘
                                              │
                                              ▼
        ┌─ Settings Dropdown ─────────────────────────┐
        │ ☀️ Theme                                     │
        │ ──────────────────────────────────────      │
        │ 🎛️ Advanced Settings                  ← NEW │
        │ ──────────────────────────────────────      │
        │ [Current project]                           │
        │ MyProject                                    │
        │ ──────────────────────────────────────      │
        │ 🔄 Change Project                           │
        │ ──────────────────────────────────────      │
        │ ➕ Add user                                 │
        │ ──────────────────────────────────────      │
        │ 🚪 Sign out                                 │
        └─────────────────────────────────────────────┘
```

### Route
- **URL**: `/advanced-settings`
- **Icon**: `fa-sliders-h` (sliders/tuning icon)
- **Label**: "Advanced Settings"

---

## Page Layout

### Header
```
┌────────────────────────────────────────────────────────────┐
│ Advanced Settings                                          │
│ Current Project: MyProject                                 │
│                                                            │
│ Configure ML analysis, transaction evaluation, and data   │
│ aggregation parameters for this project.                  │
└────────────────────────────────────────────────────────────┘
```

### Category Sections (Accordion)

#### 1. ML Analysis Settings
```
┌─ ML Analysis Settings ▼ ───────────────────────────────────┐
│                                                             │
│ Isolation Forest Detection                                 │
│ ├─ Contamination                  [0.001]  ℹ️               │
│ │  Range: 0.0001 - 0.1                                     │
│ ├─ ISF Threshold                  [0.1]    ℹ️               │
│ │  Range: -1.0 - 1.0                                       │
│ └─ ISF Feature Metric             [overalThroughput ▼]     │
│                                                             │
│ Z-Score Detection                                           │
│ └─ Z-Score Threshold              [3]      ℹ️               │
│    Range: 1 - 10                                           │
│                                                             │
│ Rolling Analysis                                            │
│ ├─ Rolling Window                 [5]      ℹ️               │
│ │  Range: 3 - 20                                           │
│ └─ Rolling Correlation Threshold  [0.4]    ℹ️               │
│    Range: 0.0 - 1.0                                        │
│                                                             │
│ Ramp-Up Detection                                           │
│ ├─ Base Metric                    [overalUsers ▼]          │
│ ├─ Min Required Breaches          [3]      ℹ️               │
│ ├─ Max Required Breaches          [5]      ℹ️               │
│ └─ Breaches Fraction              [0.15]   ℹ️               │
│                                                             │
│ [... more subsections ...]                                 │
│                                                             │
│ [Save Changes]  [Reset to Defaults]                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2. Transaction Status Settings
```
┌─ Transaction Status Settings ▼ ─────────────────────────────┐
│                                                             │
│ NFR Validation                                              │
│ └─ NFR Check Enabled              [✓]      ℹ️               │
│                                                             │
│ Baseline Comparison                                         │
│ ├─ Baseline Check Enabled         [✓]      ℹ️               │
│ ├─ Warning Threshold (%)          [10.0]   ℹ️               │
│ ├─ Failed Threshold (%)           [20.0]   ℹ️               │
│ └─ Metrics to Check              [rt_ms_avg, rt_ms_median...│
│                                   rt_ms_p90, error_rate]    │
│                                                             │
│ ML Anomaly Detection                                        │
│ ├─ ML Check Enabled               [✓]      ℹ️               │
│ └─ Minimum Impact                 [0.0]    ℹ️               │
│                                                             │
│ [Save Changes]  [Reset to Defaults]                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3. Data Aggregation Settings
```
┌─ Data Aggregation Settings ▼ ───────────────────────────────┐
│                                                             │
│ Default Aggregation                                         │
│ └─ Aggregation Type               [median ▼]   ℹ️            │
│    Options: mean, median, p90, p99                         │
│                                                             │
│ [Save Changes]  [Reset to Defaults]                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## UI Elements

### Input Types

1. **Numeric Input** (int/float)
   - Text input with type="number"
   - Min/max attributes from metadata
   - Step attribute for precision (0.001 for floats)
   - Range display below input

2. **Boolean Toggle**
   - Bootstrap toggle switch
   - Green when enabled, gray when disabled

3. **String Input**
   - Text input
   - Validation for special cases (e.g., metric names)

4. **Select Dropdown**
   - For enum-like fields (e.g., aggregation type)
   - Options from metadata

5. **List Input**
   - Comma-separated text input
   - OR: Tag-style multi-select

### Interactive Elements

#### Tooltip (ℹ️)
- Appears on hover
- Shows description from metadata
- Positioned to avoid covering inputs

#### Change Indicator
- Blue dot or asterisk (*) next to modified values
- "Unsaved changes" banner at top when changes exist

#### Validation
- Real-time validation (client-side)
- Red border + error message for invalid values
- Prevent save if validation fails

#### Buttons
- **Save Changes**: Primary button (blue)
  - Disabled if no changes
  - Shows spinner during save
  - Success toast on completion

- **Reset to Defaults**: Secondary button (gray)
  - Confirmation modal before reset
  - Resets only the current category

#### Notifications
- Toast messages (top-right)
- Success: Green with checkmark
- Error: Red with error icon
- Info: Blue with info icon

---

## Responsive Design

### Desktop (>992px)
- Full accordion layout
- Two-column grid within each category
- Wide inputs with labels on left

### Tablet (768px - 992px)
- Single column layout
- Labels above inputs

### Mobile (<768px)
- Stacked layout
- Full-width inputs
- Larger touch targets

---

## Color Scheme

Match existing PerForge theme:
- **Primary**: Bootstrap primary (blue)
- **Success**: Bootstrap success (green)
- **Warning**: Bootstrap warning (yellow)
- **Danger**: Bootstrap danger (red)
- **Background**: Light gray for sections
- **Border**: Light gray (#dee2e6)

---

## User Flow

1. User clicks **Settings** dropdown in sidebar
2. User clicks **Advanced Settings**
3. Page loads with all categories collapsed by default
4. User expands category of interest
5. User modifies values (sees change indicators)
6. User clicks **Save Changes** for that category
7. Success message appears
8. Changes are persisted to database
9. Changes take effect immediately for new test runs

---

## Accessibility

- ✅ ARIA labels on all inputs
- ✅ Keyboard navigation support
- ✅ High contrast for text
- ✅ Screen reader friendly
- ✅ Focus indicators on interactive elements

---

## Example Code Snippets

### Sidebar Link Addition
```html
<!-- In app/templates/includes/sidebar.html -->
<li><hr class="dropdown-divider"></li>
<li>
    <a class="dropdown-item" href="/advanced-settings">
        <i class="fas fa-sliders-h me-2"></i>Advanced Settings
    </a>
</li>
<li><hr class="dropdown-divider"></li>
```

### Category Accordion
```html
<div class="accordion" id="settingsAccordion">
    <!-- ML Analysis -->
    <div class="accordion-item">
        <h2 class="accordion-header">
            <button class="accordion-button collapsed" type="button"
                    data-bs-toggle="collapse" data-bs-target="#mlAnalysis">
                ML Analysis Settings
            </button>
        </h2>
        <div id="mlAnalysis" class="accordion-collapse collapse">
            <div class="accordion-body">
                <!-- Settings form here -->
            </div>
        </div>
    </div>
    <!-- More categories... -->
</div>
```

### Numeric Input with Validation
```html
<div class="mb-3">
    <label for="contamination" class="form-label">
        Contamination
        <i class="fas fa-info-circle" data-bs-toggle="tooltip"
           title="Expected proportion of outliers in the dataset"></i>
    </label>
    <input type="number" class="form-control" id="contamination"
           name="contamination" value="0.001"
           min="0.0001" max="0.1" step="0.0001" required>
    <div class="form-text">Range: 0.0001 - 0.1</div>
    <div class="invalid-feedback">
        Value must be between 0.0001 and 0.1
    </div>
</div>
```

---

## Implementation Checklist

- [ ] Add route in `app/views/settings.py`
- [ ] Create template `app/templates/settings.html`
- [ ] Create JavaScript `app/static/js/settings.js`
- [ ] Add link to sidebar `app/templates/includes/sidebar.html`
- [ ] Load settings via API `/api/v1/settings/metadata`
- [ ] Implement client-side validation
- [ ] Implement save functionality (PUT requests)
- [ ] Implement reset functionality (POST to /reset)
- [ ] Add success/error toast notifications
- [ ] Test responsiveness
- [ ] Test all input types
- [ ] Test validation edge cases
- [ ] Add browser tests
