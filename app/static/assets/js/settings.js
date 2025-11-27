/**
 * Advanced Settings Page JavaScript
 * Handles loading, validation, and saving of project settings
 */

// State management
const settingsState = {
    original: {},  // Original values from API
    current: {},   // Current form values
    metadata: {}   // Settings metadata (types, descriptions, constraints)
};

// Category display names
const categoryNames = {
    'ml_analysis': 'ML Analysis',
    'transaction_status': 'Transaction Status'
};

// Subsection groupings for ML Analysis
const mlAnalysisGroups = {
    'Isolation Forest': ['contamination', 'isf_threshold', 'isf_feature_metric'],
    'Z-Score Detection': ['z_score_threshold'],
    'Rolling Analysis': ['rolling_window', 'rolling_correlation_threshold'],
    'Ramp-Up Detection': ['ramp_up_base_metric', 'ramp_up_required_breaches_min', 'ramp_up_required_breaches_max', 'ramp_up_required_breaches_fraction'],
    'Load Detection': ['fixed_load_percentage'],
    'Metric Stability': ['slope_threshold', 'p_value_threshold', 'numpy_var_threshold', 'cv_threshold'],
    'Context Filtering': ['context_median_window', 'context_median_pct', 'context_median_enabled'],
    'Merging & Grouping': ['merge_gap_samples'],
    'Per-Transaction Analysis': ['per_txn_analysis_enabled', 'per_txn_metrics', 'per_txn_coverage', 'per_txn_max_k', 'per_txn_min_points']
};

// Subsection groupings for Transaction Status
const transactionStatusGroups = {
    'NFR Validation': ['nfr_enabled'],
    'Baseline Comparison': ['baseline_enabled', 'baseline_warning_threshold_pct', 'baseline_failed_threshold_pct', 'baseline_metrics_to_check'],
    'ML Anomaly Detection': ['ml_enabled', 'ml_min_impact']
};

/**
 * Initialize settings page
 */
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Load settings with metadata
        await loadAllSettings();

        // Set up event listeners
        setupEventListeners();
    } catch (error) {
        console.error('Error initializing settings:', error);
        showFlashMessage('Failed to load settings: ' + error.message, 'error');
    }
});

/**
 * Load all settings with metadata from API
 */
async function loadAllSettings() {
    try {
        const response = await fetch('/api/v1/settings/metadata');
        const data = await response.json();

        if (data.status === 'error') {
            throw new Error(data.message || 'Failed to load settings');
        }

        settingsState.metadata = data.data.settings;

        // Store original and current values
        for (const [category, settings] of Object.entries(data.data.settings)) {
            settingsState.original[category] = {};
            settingsState.current[category] = {};

            for (const [key, setting] of Object.entries(settings)) {
                settingsState.original[category][key] = setting.value;
                settingsState.current[category][key] = setting.value;
            }
        }

        // Render each category
        renderCategory('ml_analysis', mlAnalysisGroups);
        renderCategory('transaction_status', transactionStatusGroups);

        // Hide all unsaved indicators initially
        document.querySelectorAll('.unsaved-indicator').forEach(indicator => {
            indicator.classList.add('d-none');
        });

    } catch (error) {
        console.error('Error loading settings:', error);
        throw error;
    }
}

/**
 * Render settings for a category
 */
function renderCategory(category, groups) {
    const containerId = category === 'ml_analysis' ? 'mlAnalysisSettings' :
        category === 'transaction_status' ? 'transactionStatusSettings' :
            'dataAggregationSettings';

    const container = document.getElementById(containerId);
    if (!container) return;

    const settings = settingsState.metadata[category];
    if (!settings) return;

    let html = '';

    // Render grouped settings
    for (const [groupName, keys] of Object.entries(groups)) {
        html += `<div class="settings-subsection">`;
        html += `<div class="settings-subsection-title">${groupName}</div>`;

        for (const key of keys) {
            const setting = settings[key];
            if (!setting) continue;

            html += renderSetting(category, key, setting);
        }

        html += `</div>`;
    }

    container.innerHTML = html;

    // Initialize tooltips
    const tooltips = container.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(el => new bootstrap.Tooltip(el));
}

/**
 * Render a single setting input
 */
function renderSetting(category, key, setting) {
    const value = settingsState.current[category][key];
    const type = setting.type;
    const description = setting.description || '';
    const min = setting.min;
    const max = setting.max;
    const options = setting.options;

    let html = `<div class="setting-item">`;
    html += `<label class="setting-label" for="${category}-${key}">`;
    html += formatLabel(key);
    html += `</label>`;

    // Render appropriate input based on type
    if (type === 'bool') {
        html += renderBooleanInput(category, key, value);
    } else if (type === 'int') {
        html += renderNumberInput(category, key, value, 'number', min, max, 1);
    } else if (type === 'float') {
        // Use 'any' step for floats to allow any decimal precision
        html += renderNumberInput(category, key, value, 'number', min, max, 'any');
    } else if (options && options.length > 0) {
        html += renderSelectInput(category, key, value, options);
    } else if (type === 'list') {
        html += renderListInput(category, key, value);
    } else {
        html += renderTextInput(category, key, value);
    }

    // Add range info for numeric fields
    if ((type === 'int' || type === 'float') && (min !== undefined || max !== undefined)) {
        html += `<div class="setting-range">Range: ${min !== undefined ? min : '-∞'} - ${max !== undefined ? max : '∞'}</div>`;
    }

    // Add form hint if description exists
    if (description) {
        html += `<div class="form-hint">
                  <i class="fas fa-info-circle icon" aria-hidden="true"></i>
                  <div>${escapeHtml(description)}</div>
                </div>`;
    }

    html += `</div>`;

    return html;
}

/**
 * Render boolean toggle input
 */
function renderBooleanInput(category, key, value) {
    const checked = value ? 'checked' : '';
    return `
        <div class="form-check form-switch">
            <input class="form-check-input" type="checkbox" id="${category}-${key}"
                   name="${key}" ${checked} data-category="${category}" data-key="${key}">
        </div>
    `;
}

/**
 * Render number input
 */
function renderNumberInput(category, key, value, inputType, min, max, step) {
    const minAttr = min !== undefined ? `min="${min}"` : '';
    const maxAttr = max !== undefined ? `max="${max}"` : '';
    return `
        <input type="${inputType}" class="form-control" id="${category}-${key}"
               name="${key}" value="${value}" ${minAttr} ${maxAttr} step="${step}"
               required data-category="${category}" data-key="${key}">
        <div class="invalid-feedback">Please enter a valid number${min !== undefined ? ` between ${min} and ${max}` : ''}.</div>
    `;
}

/**
 * Render select dropdown
 */
function renderSelectInput(category, key, value, options) {
    let html = `<select class="form-select" id="${category}-${key}" name="${key}"
                        required data-category="${category}" data-key="${key}">`;

    for (const option of options) {
        const selected = value === option ? 'selected' : '';
        html += `<option value="${option}" ${selected}>${option}</option>`;
    }

    html += `</select>`;
    return html;
}

/**
 * Render text input
 */
function renderTextInput(category, key, value) {
    return `
        <input type="text" class="form-control" id="${category}-${key}"
               name="${key}" value="${escapeHtml(value)}"
               data-category="${category}" data-key="${key}">
    `;
}

/**
 * Render list input (comma-separated)
 */
function renderListInput(category, key, value) {
    const displayValue = Array.isArray(value) ? value.join(', ') : value;
    return `
        <input type="text" class="form-control" id="${category}-${key}"
               name="${key}" value="${escapeHtml(displayValue)}"
               placeholder="Comma-separated values"
               data-category="${category}" data-key="${key}">
        <div class="form-text">Enter values separated by commas</div>
    `;
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Form submissions
    document.getElementById('mlAnalysisForm').addEventListener('submit', handleFormSubmit);
    document.getElementById('transactionStatusForm').addEventListener('submit', handleFormSubmit);

    // Reset buttons
    document.querySelectorAll('.reset-btn').forEach(btn => {
        btn.addEventListener('click', handleResetClick);
    });

    // Confirm reset button
    document.getElementById('confirmResetBtn').addEventListener('click', handleConfirmReset);

    // Track input changes
    document.addEventListener('input', handleInputChange);
    document.addEventListener('change', handleInputChange);
}

/**
 * Handle input changes to track unsaved changes
 */
function handleInputChange(e) {
    const input = e.target;
    const category = input.dataset.category;
    const key = input.dataset.key;

    if (!category || !key) return;

    let value;
    if (input.type === 'checkbox') {
        value = input.checked;
    } else if (input.type === 'number') {
        value = input.value === '' ? '' : parseFloat(input.value);
    } else {
        value = input.value;
    }

    // Update current state
    settingsState.current[category][key] = value;

    // Update unsaved indicator for this category
    updateUnsavedIndicator(category);
}

/**
 * Update unsaved changes indicator
 */
function updateUnsavedIndicator(category) {
    const indicatorId = category.replace(/_/g, '-') + '-unsaved';
    const indicator = document.getElementById(indicatorId);

    if (indicator) {
        // Check if any setting in category has changes
        let anyChanged = false;
        for (const key in settingsState.current[category]) {
            if (settingsState.current[category][key] !== settingsState.original[category][key]) {
                anyChanged = true;
                break;
            }
        }

        if (anyChanged) {
            indicator.classList.remove('d-none');
        } else {
            indicator.classList.add('d-none');
        }
    }
}

/**
 * Handle form submission
 */
async function handleFormSubmit(e) {
    e.preventDefault();

    const form = e.target;
    const category = form.dataset.category;
    const submitBtn = form.querySelector('button[type="submit"]');
    const spinner = submitBtn.querySelector('.loading-spinner');

    // Validate form
    if (!form.checkValidity()) {
        form.classList.add('was-validated');
        showFlashMessage('Please fix validation errors', 'error');
        return;
    }

    // Collect form data - iterate over all settings in metadata to catch unchecked checkboxes
    const settings = {};

    for (const [key, setting] of Object.entries(settingsState.metadata[category])) {
        const element = form.elements[key];
        if (!element) continue;

        // Convert value to appropriate type
        if (setting.type === 'bool') {
            settings[key] = element.checked;
        } else if (setting.type === 'int') {
            settings[key] = parseInt(element.value, 10);
        } else if (setting.type === 'float') {
            settings[key] = parseFloat(element.value);
        } else if (setting.type === 'list') {
            settings[key] = element.value.split(',').map(v => v.trim()).filter(v => v);
        } else {
            settings[key] = element.value;
        }
    }

    // Show loading
    submitBtn.disabled = true;
    spinner.style.display = 'inline-block';

    try {
        const response = await fetch(`/api/v1/settings/${category}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });

        const data = await response.json();

        if (data.status === 'error') {
            throw new Error(data.message || 'Failed to save settings');
        }

        // Update original state
        for (const key in settings) {
            settingsState.original[category][key] = settings[key];
            settingsState.current[category][key] = settings[key];
        }

        // Hide unsaved indicator
        updateUnsavedIndicator(category);

        showFlashMessage('Settings saved successfully', 'success');

    } catch (error) {
        console.error('Error saving settings:', error);
        showFlashMessage('Failed to save settings: ' + error.message, 'error');
    } finally {
        submitBtn.disabled = false;
        spinner.style.display = 'none';
    }
}

/**
 * Handle reset button click
 */
function handleResetClick(e) {
    const category = e.target.dataset.category;
    const categoryName = categoryNames[category] || category;

    document.getElementById('resetCategoryName').textContent = categoryName;
    document.getElementById('confirmResetBtn').dataset.category = category;

    const modal = new bootstrap.Modal(document.getElementById('resetConfirmModal'));
    modal.show();
}

/**
 * Handle confirmed reset
 */
async function handleConfirmReset(e) {
    const category = e.target.dataset.category;

    try {
        const response = await fetch('/api/v1/settings/reset', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ category: category })
        });

        const data = await response.json();

        if (data.status === 'error') {
            throw new Error(data.message || 'Failed to reset settings');
        }

        // Reload settings
        await loadAllSettings();

        // Hide modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('resetConfirmModal'));
        modal.hide();

        showFlashMessage('Settings reset to defaults', 'success');

    } catch (error) {
        console.error('Error resetting settings:', error);
        showFlashMessage('Failed to reset settings: ' + error.message, 'error');
    }
}

/**
 * Format setting key to readable label
 */
function formatLabel(key) {
    return key
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
