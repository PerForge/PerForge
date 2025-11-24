# PerForge Settings Management System - Implementation Plan

## Overview

This document outlines the implementation plan for a centralized, database-backed settings management system for PerForge. This will replace hardcoded configuration parameters with per-project, user-configurable settings stored in the database.

## Goals

1. **Centralize Configuration**: Replace scattered hardcoded parameters with a unified settings system
2. **Per-Project Settings**: Each project maintains its own configuration
3. **User Control**: Provide UI for viewing and modifying settings
4. **Backwards Compatibility**: Use sensible defaults that match current behavior
5. **Performance**: Cache settings to avoid excessive database queries

## Architecture

### 1. Database Layer

#### 1.1 Settings Model (`settings_db.py`)

```python
class DBProjectSettings(db.Model):
    __tablename__ = 'project_settings'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'ml_analysis', 'transaction_status', 'data_aggregation'
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Text, nullable=False)  # JSON serialized value
    value_type = db.Column(db.String(20), nullable=False)  # 'float', 'int', 'bool', 'string', 'list'
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('project_id', 'category', 'key', name='uq_project_category_key'),
    )
```

#### 1.2 Add Relationship to Projects

```python
# In projects_db.py
settings = db.relationship('DBProjectSettings', backref='project', cascade='all, delete-orphan', lazy=True)
```

### 2. Service Layer

#### 2.1 Settings Service (`settings_service.py`)

Purpose: Centralized service for retrieving and managing settings with caching

```python
class SettingsService:
    """Service for managing project settings with caching."""

    _cache = {}  # {project_id: {category: {key: value}}}
    _defaults = None

    @classmethod
    def get_defaults(cls) -> Dict[str, Dict[str, Any]]:
        """Get default settings structure."""

    @classmethod
    def get_project_settings(cls, project_id: int, category: str = None) -> Dict[str, Any]:
        """Get settings for a project (from cache or DB)."""

    @classmethod
    def update_setting(cls, project_id: int, category: str, key: str, value: Any):
        """Update a single setting."""

    @classmethod
    def initialize_project_settings(cls, project_id: int):
        """Initialize default settings for a new project."""

    @classmethod
    def clear_cache(cls, project_id: int = None):
        """Clear settings cache."""
```

### 3. API Layer

#### 3.1 Settings API Endpoints (`api/settings.py`)

```
GET    /api/v1/settings              # Get all settings for current project
GET    /api/v1/settings/:category    # Get settings by category
PUT    /api/v1/settings/:category    # Update multiple settings in category
PUT    /api/v1/settings/:category/:key  # Update single setting
POST   /api/v1/settings/reset        # Reset to defaults
GET    /api/v1/settings/defaults     # Get default values (for reference)
```

### 4. Frontend Layer

#### 4.1 Settings Page Structure

**File**: `app/templates/settings.html`

**UI Sections**:
1. **ML & Anomaly Detection Settings**
   - Isolation Forest Parameters
   - Z-Score Detection
   - Rolling Analysis
   - Ramp-Up Detection
   - Metric Stability
   - Context Filtering
   - Per-Transaction Analysis

2. **Transaction Status Evaluation**
   - NFR Checking
   - Baseline Comparison
   - ML Anomaly Impact

3. **Data Aggregation**
   - Default aggregation type

**Features**:
- Grouped settings by category with collapsible sections
- Input validation (min/max values, types)
- Tooltips explaining each parameter
- Reset to defaults button (per category or all)
- Save changes with confirmation
- Show "last modified" timestamp
- Highlight changed values

#### 4.2 JavaScript Client (`settings.js`)

```javascript
const SettingsClient = {
    async getSettings(category = null) { },
    async updateSettings(category, settings) { },
    async updateSetting(category, key, value) { },
    async resetSettings(category = null) { },
    async getDefaults() { }
};
```

### 5. Integration Points

#### 5.1 AnomalyDetectionEngine

**Current**:
```python
default_params = {
    'contamination': 0.001,
    'isf_threshold': 0.1,
    # ... 20+ more parameters
}
```

**New**:
```python
def __init__(self, params: Dict[str, Any], project_id: int):
    # Get settings from service
    ml_settings = SettingsService.get_project_settings(project_id, 'ml_analysis')

    # Merge with provided params (provided params take precedence)
    self._validate_and_set_params({**ml_settings, **params}, ml_settings)
```

#### 5.2 TransactionStatusConfig

**Current**: Dataclass with hardcoded defaults

**New**: Factory method that loads from database

```python
@classmethod
def from_project_settings(cls, project_id: int) -> 'TransactionStatusConfig':
    """Create config from project settings."""
    settings = SettingsService.get_project_settings(project_id, 'transaction_status')
    return cls(**settings)
```

#### 5.3 BaseTestData

**Current**: `self.aggregation = "median"`

**New**:
```python
def __init__(self, project_id: int):
    settings = SettingsService.get_project_settings(project_id, 'data_aggregation')
    self.aggregation = settings.get('default_aggregation', 'median')
```

### 6. Default Settings Structure

#### 6.1 ML Analysis Settings (Category: `ml_analysis`)

```python
ML_ANALYSIS_DEFAULTS = {
    # Isolation Forest
    'contamination': {
        'value': 0.001,
        'type': 'float',
        'min': 0.0001,
        'max': 0.5,
        'description': 'Expected proportion of outliers in the dataset'
    },
    'isf_threshold': {
        'value': 0.1,
        'type': 'float',
        'min': -1.0,
        'max': 1.0,
        'description': 'Decision function threshold for anomaly classification'
    },
    'isf_feature_metric': {
        'value': 'overalThroughput',
        'type': 'string',
        'options': ['overalThroughput', 'overalUsers', 'overalResponseTime'],
        'description': 'Primary metric to use for Isolation Forest analysis'
    },

    # Z-Score Detection
    'z_score_threshold': {
        'value': 3,
        'type': 'float',
        'min': 1.0,
        'max': 10.0,
        'description': 'Number of standard deviations for anomaly detection'
    },

    # Rolling Analysis
    'rolling_window': {
        'value': 5,
        'type': 'int',
        'min': 2,
        'max': 20,
        'description': 'Window size for rolling calculations'
    },
    'rolling_correlation_threshold': {
        'value': 0.4,
        'type': 'float',
        'min': 0.0,
        'max': 1.0,
        'description': 'Correlation threshold for ramp-up analysis'
    },

    # Ramp-Up Detection
    'ramp_up_required_breaches_min': {
        'value': 3,
        'type': 'int',
        'min': 1,
        'max': 10,
        'description': 'Minimum consecutive threshold breaches to confirm tipping point'
    },
    'ramp_up_required_breaches_max': {
        'value': 5,
        'type': 'int',
        'min': 1,
        'max': 20,
        'description': 'Maximum consecutive threshold breaches to confirm tipping point'
    },
    'ramp_up_required_breaches_fraction': {
        'value': 0.15,
        'type': 'float',
        'min': 0.01,
        'max': 0.5,
        'description': 'Fraction of data points used to calculate required breaches'
    },
    'ramp_up_base_metric': {
        'value': 'overalUsers',
        'type': 'string',
        'options': ['overalUsers', 'overalThroughput'],
        'description': 'Base metric for ramp-up correlation analysis'
    },

    # Load Detection
    'fixed_load_percentage': {
        'value': 60,
        'type': 'int',
        'min': 50,
        'max': 100,
        'description': 'Percentage of data points with stable users to classify as fixed load'
    },

    # Metric Stability
    'slope_threshold': {
        'value': 1.000,
        'type': 'float',
        'min': 0.0,
        'max': 10.0,
        'description': 'Threshold for detecting significant trends'
    },
    'p_value_threshold': {
        'value': 0.05,
        'type': 'float',
        'min': 0.01,
        'max': 0.2,
        'description': 'P-value threshold for statistical significance'
    },
    'numpy_var_threshold': {
        'value': 0.003,
        'type': 'float',
        'min': 0.0,
        'max': 0.1,
        'description': 'Variance threshold for stability detection'
    },
    'cv_threshold': {
        'value': 0.07,
        'type': 'float',
        'min': 0.0,
        'max': 1.0,
        'description': 'Coefficient of variation threshold'
    },

    # Context Filtering
    'context_median_window': {
        'value': 10,
        'type': 'int',
        'min': 3,
        'max': 50,
        'description': 'Window size for contextual median calculation'
    },
    'context_median_pct': {
        'value': 0.15,
        'type': 'float',
        'min': 0.0,
        'max': 1.0,
        'description': 'Percentage threshold for contextual median filtering'
    },
    'context_median_enabled': {
        'value': True,
        'type': 'bool',
        'description': 'Enable contextual median filtering'
    },

    # Merging & Grouping
    'merge_gap_samples': {
        'value': 4,
        'type': 'int',
        'min': 1,
        'max': 20,
        'description': 'Maximum gap between samples to merge into continuous period'
    },

    # Per-Transaction Analysis
    'per_txn_coverage': {
        'value': 0.8,
        'type': 'float',
        'min': 0.1,
        'max': 1.0,
        'description': 'Cumulative traffic share coverage for transaction selection'
    },
    'per_txn_max_k': {
        'value': 50,
        'type': 'int',
        'min': 1,
        'max': 200,
        'description': 'Maximum number of transactions to analyze'
    },
    'per_txn_min_points': {
        'value': 6,
        'type': 'int',
        'min': 3,
        'max': 20,
        'description': 'Minimum data points required for transaction analysis'
    }
}
```

#### 6.2 Transaction Status Settings (Category: `transaction_status`)

```python
TRANSACTION_STATUS_DEFAULTS = {
    # NFR Checking
    'nfr_enabled': {
        'value': True,
        'type': 'bool',
        'description': 'Enable NFR (Non-Functional Requirements) checking'
    },

    # Baseline Comparison
    'baseline_enabled': {
        'value': True,
        'type': 'bool',
        'description': 'Enable baseline comparison'
    },
    'baseline_warning_threshold_pct': {
        'value': 10.0,
        'type': 'float',
        'min': 0.0,
        'max': 100.0,
        'description': 'Percentage deviation threshold for warning status'
    },
    'baseline_failed_threshold_pct': {
        'value': 20.0,
        'type': 'float',
        'min': 0.0,
        'max': 100.0,
        'description': 'Percentage deviation threshold for failed status'
    },
    'baseline_metrics_to_check': {
        'value': ['rt_ms_avg', 'rt_ms_median', 'rt_ms_p90', 'error_rate'],
        'type': 'list',
        'description': 'Metrics to check in baseline comparison'
    },

    # ML Anomaly Detection
    'ml_enabled': {
        'value': True,
        'type': 'bool',
        'description': 'Enable ML anomaly detection in transaction status'
    },
    'ml_min_impact': {
        'value': 0.0,
        'type': 'float',
        'min': 0.0,
        'max': 1.0,
        'description': 'Minimum impact score to consider ML anomalies (0.0 = disabled)'
    }
}
```

#### 6.3 Data Aggregation Settings (Category: `data_aggregation`)

```python
DATA_AGGREGATION_DEFAULTS = {
    'default_aggregation': {
        'value': 'median',
        'type': 'string',
        'options': ['mean', 'median', 'p90', 'p99'],
        'description': 'Default aggregation method for metrics'
    }
}
```

## Implementation Steps

### Step 1: Database Model & Migration

**Files to Create**:
- `app/backend/components/settings/settings_db.py`
- `app/backend/components/settings/__init__.py`
- Migration script for creating `project_settings` table

**Actions**:
1. Create `DBProjectSettings` model
2. Add relationship to `DBProjects`
3. Create database migration
4. Run migration

### Step 2: Service Layer

**Files to Create**:
- `app/backend/components/settings/settings_service.py`
- `app/backend/components/settings/settings_defaults.py`

**Actions**:
1. Implement `SettingsService` with caching
2. Define all default settings with metadata
3. Implement CRUD operations
4. Add cache invalidation logic

### Step 3: API Endpoints

**Files to Create**:
- `app/api/settings.py`

**Files to Update**:
- `app/api/__init__.py` (register blueprint)

**Actions**:
1. Implement RESTful endpoints
2. Add validation
3. Add error handling
4. Test with API client

### Step 4: Frontend UI

**Files to Create**:
- `app/templates/settings.html` - Main settings page template
- `app/static/js/settings.js` - JavaScript for API interactions and validation
- `app/views/settings.py` - Route handler for /advanced-settings

**Files to Modify**:
- `app/templates/includes/sidebar.html` - Add link to Settings dropdown

**Page Structure**:
```
Advanced Settings
Current Project: [ProjectName]

┌─ ML Analysis Settings ▼ ───────────────────────────────┐
│ Isolation Forest                                        │
│   • Contamination: [0.001] (0.0001 - 0.1)              │
│   • ISF Threshold: [0.1]                                │
│   • ISF Feature Metric: [overalThroughput]             │
│                                                         │
│ Z-Score Detection                                       │
│   • Z-Score Threshold: [3]                             │
│ ...                                                     │
│                                                         │
│ [Save Changes] [Reset to Defaults]                     │
└─────────────────────────────────────────────────────────┘

┌─ Transaction Status Settings ▼ ─────────────────────────┐
│ ...                                                     │
└─────────────────────────────────────────────────────────┘

┌─ Data Aggregation Settings ▼ ───────────────────────────┐
│ ...                                                     │
└─────────────────────────────────────────────────────────┘
```

**Navigation Location**:
Settings dropdown (top-right) → Advanced Settings (with sliders icon)

**Actions**:
1. Create accordion-style page with collapsible category sections
2. Implement JavaScript API client using `/api/v1/settings` endpoints
3. Add input validation (client-side and server-side)
4. Display tooltips/help text from metadata
5. Implement save/reset functionality per category
6. Add change indicators (show unsaved changes)
7. Add to Settings dropdown in sidebar
8. Match existing PerForge UI styling (Bootstrap 5)

### Step 5: Integration - Anomaly Detection

**Files to Update**:
- `app/backend/data_provider/data_analysis/anomaly_detection.py`
- `app/backend/data_provider/data_provider.py` (pass project_id)

**Actions**:
1. Update `AnomalyDetectionEngine.__init__()` to accept `project_id`
2. Load settings from `SettingsService`
3. Maintain backward compatibility with params override
4. Update all instantiation points to pass `project_id`

### Step 6: Integration - Transaction Status

**Files to Update**:
- `app/backend/data_provider/test_data/transaction_status.py`
- All places where `TransactionStatusConfig` is instantiated

**Actions**:
1. Add `from_project_settings()` class method
2. Update instantiation to use settings
3. Maintain dataclass defaults for backwards compatibility

### Step 7: Integration - Base Test Data

**Files to Update**:
- `app/backend/data_provider/test_data/base_test_data.py`
- All test data classes

**Actions**:
1. Update `__init__()` to accept `project_id`
2. Load aggregation setting from database
3. Update all instantiation points

### Step 8: Project Creation

**Files to Update**:
- `app/backend/components/projects/projects_db.py`
- `app/api/projects.py`

**Actions**:
1. Add hook to initialize settings on project creation
2. Call `SettingsService.initialize_project_settings(project_id)`
3. Test project creation flow

### Step 9: Migration for Existing Projects

**Implementation**: Integrated into schema migration ✓

**Actions**:
1. ✅ Schema migration automatically initializes settings for existing projects
2. ✅ Runs on first app startup after deployment
3. ✅ No manual intervention required

### Step 10: Testing

**Files to Create**:
- `browser_tests/tests/settings.spec.js`
- Unit tests for `SettingsService`
- Integration tests for settings API

**Actions**:
1. Test settings CRUD operations
2. Test UI functionality
3. Test integration with ML analysis
4. Test project creation with settings
5. Test cache invalidation

## Database Schema

```sql
CREATE TABLE project_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    category VARCHAR(50) NOT NULL,
    key VARCHAR(100) NOT NULL,
    value TEXT NOT NULL,
    value_type VARCHAR(20) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    CONSTRAINT uq_project_category_key UNIQUE (project_id, category, key)
);

CREATE INDEX idx_project_settings_project_category ON project_settings(project_id, category);
```

## API Response Examples

### GET /api/v1/settings

```json
{
  "success": true,
  "data": {
    "ml_analysis": {
      "contamination": 0.001,
      "isf_threshold": 0.1,
      "z_score_threshold": 3,
      ...
    },
    "transaction_status": {
      "nfr_enabled": true,
      "baseline_enabled": true,
      ...
    },
    "data_aggregation": {
      "default_aggregation": "median"
    }
  }
}
```

### PUT /api/v1/settings/ml_analysis

```json
{
  "contamination": 0.002,
  "z_score_threshold": 3.5
}
```

Response:
```json
{
  "success": true,
  "message": "Settings updated successfully",
  "data": {
    "updated": ["contamination", "z_score_threshold"]
  }
}
```

## UI Mockup Structure

```
┌─────────────────────────────────────────────┐
│ Settings                            [Reset] │
├─────────────────────────────────────────────┤
│                                             │
│ ▼ ML & Anomaly Detection Settings          │
│   ┌─────────────────────────────────────┐  │
│   │ Isolation Forest                    │  │
│   │ ┌─────────────────────────────────┐ │  │
│   │ │ Contamination:  [0.001]     ⓘ  │ │  │
│   │ │ ISF Threshold:  [0.1]       ⓘ  │ │  │
│   │ │ Feature Metric: [dropdown]  ⓘ  │ │  │
│   │ └─────────────────────────────────┘ │  │
│   │                                     │  │
│   │ Z-Score Detection                   │  │
│   │ ┌─────────────────────────────────┐ │  │
│   │ │ Threshold:      [3]         ⓘ  │ │  │
│   │ └─────────────────────────────────┘ │  │
│   └─────────────────────────────────────┘  │
│                                             │
│ ▼ Transaction Status Evaluation            │
│   ...                                       │
│                                             │
│ ▼ Data Aggregation                         │
│   ...                                       │
│                                             │
│                      [Cancel] [Save Changes]│
└─────────────────────────────────────────────┘
```

## Performance Considerations

1. **Caching Strategy**
   - Cache settings in memory per project
   - Invalidate on update
   - Consider TTL if multiple servers

2. **Database Queries**
   - Eager load all settings for a project in single query
   - Use indexes on (project_id, category)

3. **Backwards Compatibility**
   - All code should work with or without database settings
   - Defaults in code as fallback
   - Gradual migration path

## Security Considerations

1. **Access Control**
   - Only project members can modify settings
   - Audit log for settings changes
   - Validate all input values

2. **Validation**
   - Type checking
   - Range validation
   - Prevent SQL injection via ORM

## Future Enhancements

1. **Settings Versioning**
   - Track history of settings changes
   - Ability to rollback to previous settings

2. **Settings Templates**
   - Predefined setting profiles (conservative, aggressive, balanced)
   - Import/export settings between projects

3. **Settings Impact Analysis**
   - Show which reports/analyses use which settings
   - Preview impact before applying changes

4. **Advanced Settings**
   - Expert mode with more granular controls
   - Setting dependencies and validation rules

## Rollout Strategy

1. **Phase 1**: Database & Service Layer (no UI)
2. **Phase 2**: API endpoints
3. **Phase 3**: UI for viewing settings (read-only)
4. **Phase 4**: UI for editing settings
5. **Phase 5**: Integration with ML engine
6. **Phase 6**: Integration with transaction status
7. **Phase 7**: Full rollout

## Success Criteria

- [ ] All hardcoded parameters moved to database
- [ ] Settings can be viewed and modified via UI
- [ ] New projects initialize with default settings
- [ ] Existing projects migrated to use settings
- [ ] ML analysis uses project-specific settings
- [ ] No performance degradation
- [ ] All browser tests passing
- [ ] Documentation updated

## Estimated Effort

- Database & Service Layer: 4 hours
- API Endpoints: 3 hours
- UI Development: 6 hours
- Integration Updates: 5 hours
- Testing: 4 hours
- Documentation: 2 hours

**Total**: ~24 hours

## Dependencies

- SQLAlchemy (already in use)
- Flask blueprints (already in use)
- Existing API client patterns
- Bootstrap/jQuery (for UI)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Settings cache inconsistency | Implement proper cache invalidation |
| Performance impact | Use caching, optimize queries |
| Breaking existing functionality | Maintain defaults, thorough testing |
| Complex UI | Iterative development, user feedback |
| Migration issues | Test migration script thoroughly |

---

**Document Version**: 1.0
**Last Updated**: 2025-11-21
**Author**: AI Assistant
**Status**: Draft - Pending Review
