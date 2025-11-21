# Data Analysis Module - Improvement Recommendations

## Overview

This document contains recommendations for improving the anomaly detection and attribution logic in [`anomaly_detection.py`](file:///c:/Projects/experiments/GIT/PerForge/app/backend/data_provider/data_analysis/anomaly_detection.py).

**Current Implementation Status**: ⭐⭐⭐⭐ (4/5) - Production-ready with room for improvement

---

## High Priority Improvements 🔴

### 1. Add Direction Consistency Validation

**Issue**: Transaction anomalies are mapped to overall anomalies based solely on temporal overlap, without checking if they move in the same direction.

**Location**: [`attribute_overall_to_transactions()` L1256-1378](file:///c:/Projects/experiments/GIT/PerForge/app/backend/data_provider/data_analysis/anomaly_detection.py#L1256-L1378)

**Fix**:
```python
# In attribute_overall_to_transactions(), after line 1340
overall_direction = oa.get('direction')
if direction and overall_direction and direction != overall_direction:
    # Penalize contributors with opposite direction
    impact *= 0.5  # or filter out entirely
    contrib['direction_mismatch'] = True
```

**Impact**: Prevents false positives where a transaction improvement is flagged as contributor to overall degradation.

---

### 2. Improve Impact Scoring

**Issue**: Impact is just RPS share, ignoring anomaly severity and metric importance.

**Location**: Line 1343, 1188

**Current**:
```python
impact = float(share)
```

**Recommended**:
```python
def _calculate_impact_score(share, delta_abs, baseline, metric):
    """Calculate composite impact score."""
    severity = delta_abs / max(baseline, 1e-6) if baseline else 0.0
    metric_weight = {
        'error_rate': 2.0,      # Errors are critical
        'rt_ms_p90': 1.5,       # Tail latency important
        'rt_ms_avg': 1.2,       # Average latency
        'rt_ms_median': 1.0     # Median latency
    }.get(metric, 1.0)

    return share * severity * metric_weight

impact = _calculate_impact_score(share, delta_abs, baseline, metric_name)
```

**Impact**: More accurate ranking of contributors by actual business impact.

---

### 3. Add Attribution Status Metadata

**Issue**: Silent failures in attribution pipeline - users can't tell if attribution succeeded or failed.

**Location**: Line 1380-1450

**Fix**:
```python
# Add to each overall anomaly after attribution
oa['attribution_metadata'] = {
    'status': 'success' | 'failed' | 'not_attempted',
    'contributors_found': len(txns),
    'top_contributor_share': txns[0]['share'] if txns else 0.0,
    'total_explained_share': sum(t['share'] for t in txns),
    'timestamp': datetime.now().isoformat()
}
```

**Impact**: Better observability and debugging.

---

## Medium Priority Improvements 🟡

### 4. Refactor Complex Nested Loops

**Issue**: `attribute_overall_to_transactions()` has 3-level nested loops (O(A × M × W) complexity).

**Location**: Lines 1271-1369

**Recommended Refactoring**:
```python
def _find_best_overlapping_window(overall_window, txn_clusters):
    """Find cluster with maximum overlap to overall window."""
    best = {'overlap': 0.0, 'window': None, 'metrics': None}
    for cluster in txn_clusters:
        overlap = _calculate_overlap(overall_window, cluster)
        if overlap > best['overlap']:
            best = {'overlap': overlap, 'window': cluster, 'metrics': cluster.get('metrics')}
    return best

def _calculate_transaction_share_in_window(txn, window, annotated_df, txn_col):
    """Calculate RPS share for transaction in specific time window."""
    # Extract current slice logic from lines 1318-1329
    ...
    return share
```

**Impact**: Better maintainability and testability.

---

### 5. Consolidate Duplicate Window Extraction

**Issue**: Nearly identical logic in two places:
- `_extract_anomaly_windows()` (L960-1041)
- `_extract_windows_from_anomaly_col()` (L1203-1254)

**Recommended**:
```python
def _extract_windows(df_idx, metric, source_type='flag', flag_col=None):
    """
    Unified window extraction.

    Args:
        source_type: 'flag' for boolean column, 'anomaly_col' for string column
        flag_col: If None, uses f'{metric}_anomaly_flag' or f'{metric}_anomaly'
    """
    if source_type == 'flag':
        flags = df_idx[flag_col or f'{metric}_anomaly_flag'].to_numpy()
    else:
        flags = df_idx[flag_col or f'{metric}_anomaly'].apply(
            lambda v: isinstance(v, str) and 'Anomaly' in v
        ).to_numpy()

    # Common windowing logic...
```

**Impact**: DRY principle, easier to maintain gap-merging logic.

---

### 6. Make Hardcoded Values Configurable

**Issue**: Magic numbers scattered throughout code.

**Current**:
```python
top_txn: int = 5                    # L1380
coverage = float(getattr(self, 'per_txn_coverage', 0.8))  # L905
max_k = int(getattr(self, 'per_txn_max_k', 50))           # L906
```

**Recommended**: Add to `__init__` or config:
```python
self.attribution_top_n = config.get('attribution_top_n', 5)
self.attribution_min_overlap_sec = config.get('attribution_min_overlap', 5.0)
self.direction_mismatch_penalty = config.get('direction_penalty', 0.5)
```

---

### 7. Add Temporal Ordering Logic

**Issue**: Can't distinguish causes from downstream effects.

**Example**:
```
Overall RT spike: 10:00:00 → 10:05:00
Transaction A anomaly: 09:59:50 → 10:05:00  (likely CAUSE)
Transaction B anomaly: 10:00:10 → 10:05:00  (likely VICTIM)
```

**Recommended**:
```python
# In attribution logic, add temporal analysis
txn_start = pd.to_datetime(best_window[0])
overall_start = pd.to_datetime(o_start_ts)

if txn_start < overall_start - timedelta(seconds=10):
    contrib['temporal_relationship'] = 'potential_cause'
    impact *= 1.2  # Boost impact
elif txn_start > overall_start + timedelta(seconds=30):
    contrib['temporal_relationship'] = 'downstream_effect'
    impact *= 0.5  # Reduce impact
else:
    contrib['temporal_relationship'] = 'correlated'
```

---

## Low Priority Improvements 🟢

### 8. Add Statistical Validation

**Recommendation**: Calculate correlation coefficients between transaction metrics and overall metrics during overlap window.

```python
from scipy.stats import pearsonr

def _validate_correlation(txn_values, overall_values):
    """Check if transaction metric correlates with overall."""
    if len(txn_values) < 3 or len(overall_values) < 3:
        return None
    corr, p_value = pearsonr(txn_values, overall_values)
    return {'correlation': corr, 'p_value': p_value, 'significant': p_value < 0.05}
```

---

### 9. Standardize Baseline Calculation

**Issue**: Different baseline strategies:
- Overall: Median of previous K points (L1026-1035)
- Per-transaction: Varies

**Recommended**: Create unified baseline calculator:
```python
def _calculate_baseline(series, index, method='median', window=5):
    """Standard baseline calculation across all contexts."""
    ...
```

---

### 10. Unified Event Schema

**Issue**: Different schemas for overall vs transaction events.

**Recommended**:
```python
{
    'id': 'uuid',
    'type': 'overall_anomaly' | 'transaction_anomaly',
    'scope': 'overall' | '<transaction_name>',
    'window': {'start': ..., 'end': ..., 'durationSec': ...},
    'metrics': [{'name': ..., 'direction': ..., 'severity': ...}],
    'attribution': {
        'contributors': [...],  # For overall anomalies
        'contributes_to': [...]  # For transaction anomalies
    },
    'confidence': 0.0-1.0
}
```

---

## Implementation Checklist

- [ ] **P0**: Add direction consistency validation (#1)
- [ ] **P0**: Implement composite impact scoring (#2)
- [ ] **P0**: Add attribution metadata (#3)
- [ ] **P1**: Refactor nested loops in attribution (#4)
- [ ] **P1**: Consolidate window extraction (#5)
- [ ] **P1**: Make magic numbers configurable (#6)
- [ ] **P1**: Add temporal ordering logic (#7)
- [ ] **P2**: Add correlation validation (#8)
- [ ] **P2**: Standardize baseline calculation (#9)
- [ ] **P2**: Unify event schema (#10)

---

## Testing Recommendations

When implementing these changes, ensure:

1. **Unit Tests**: Test each helper function independently
   - `_calculate_impact_score()` with various inputs
   - `_find_best_overlapping_window()` with edge cases
   - Direction mismatch scenarios

2. **Integration Tests**:
   - Overall anomaly with 0, 1, and N contributors
   - Transaction anomaly starting before/after overall
   - Opposite direction anomalies

3. **Performance Tests**:
   - 50+ transactions
   - Multiple overlapping windows
   - Edge case: 500 transactions (stress test)

---

## Additional Resources

- Full detailed review: `anomaly_detection_review.md` (in artifacts)
- Current implementation: [`anomaly_detection.py`](file:///c:/Projects/experiments/GIT/PerForge/app/backend/data_provider/data_analysis/anomaly_detection.py)
- Pipeline entry point: [`analyze_test_data()` L724](file:///c:/Projects/experiments/GIT/PerForge/app/backend/data_provider/data_analysis/anomaly_detection.py#L724)

---

**Last Updated**: 2025-11-20
**Reviewer**: AI Code Analysis
**Status**: Recommendations Pending Implementation
