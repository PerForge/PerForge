# Copyright 2025 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from dataclasses import dataclass, field
from typing import List, Dict, Any, Literal, Optional
from collections import OrderedDict
import logging


@dataclass
class TransactionStatusConfig:
    """Configuration for transaction status evaluation."""
    # NFR check
    nfr_enabled: bool = True

    # Baseline comparison check (global thresholds)
    baseline_enabled: bool = True
    baseline_warning_threshold_pct: float = 10.0   # 10-20% = WARNING
    baseline_failed_threshold_pct: float = 20.0     # ≥20% = FAILED
    baseline_metrics_to_check: List[str] = field(default_factory=lambda: [
        'rt_ms_avg', 'rt_ms_median', 'rt_ms_p90', 'error_rate'
    ])

    # ML anomaly check
    ml_enabled: bool = True
    ml_min_impact: float = 0.0  # Disabled for now (impact = share, not severity)

    @classmethod
    def from_project_settings(cls, project_id: int) -> 'TransactionStatusConfig':
        """
        Create TransactionStatusConfig from project settings.

        Args:
            project_id: Project ID to load settings for

        Returns:
            TransactionStatusConfig instance with project-specific settings
        """
        from app.backend.components.settings.settings_service import SettingsService

        try:
            # Load transaction status settings from database
            settings = SettingsService.get_project_settings(project_id, 'transaction_status')

            # Create config from loaded settings
            return cls(
                nfr_enabled=settings.get('nfr_enabled', True),
                baseline_enabled=settings.get('baseline_enabled', True),
                baseline_warning_threshold_pct=settings.get('baseline_warning_threshold_pct', 10.0),
                baseline_failed_threshold_pct=settings.get('baseline_failed_threshold_pct', 20.0),
                baseline_metrics_to_check=settings.get('baseline_metrics_to_check', [
                    'rt_ms_avg', 'rt_ms_median', 'rt_ms_p90', 'error_rate'
                ]),
                ml_enabled=settings.get('ml_enabled', True),
                ml_min_impact=settings.get('ml_min_impact', 0.0)
            )
        except Exception as e:
            logging.warning(f"Failed to load transaction status settings for project {project_id}, using defaults: {e}")
            # Return instance with default values from settings_defaults.py
            return cls()


@dataclass
class TransactionStatus:
    """Encapsulates transaction-level status for reporting."""
    transaction: str
    status: Literal['PASSED', 'FAILED', 'WARNING', 'NOT_EVALUATED']
    reasons: List[str]

    # Detailed breakdown
    nfr_status: Literal['PASSED', 'FAILED', 'NOT_EVALUATED'] = 'NOT_EVALUATED'
    nfr_failures: List[str] = field(default_factory=list)

    baseline_status: Literal['PASSED', 'FAILED', 'NOT_AVAILABLE'] = 'NOT_AVAILABLE'
    baseline_regressions: List[Dict[str, Any]] = field(default_factory=list)

    ml_status: Literal['PASSED', 'FAILED', 'NOT_EVALUATED'] = 'NOT_EVALUATED'
    ml_events: List[Dict[str, Any]] = field(default_factory=list)

    def to_report_row(self) -> OrderedDict[str, str]:
        """Convert to single-row format for simple table with explicit column order."""
        return OrderedDict([
            ('Transaction', self.transaction),
            ('Status', self.status),
            ('Reason', '; '.join(self.reasons) if self.reasons else 'All checks passed')
        ])


class TransactionStatusTable:
    """Table of transaction statuses for report generation."""

    def __init__(self, name: str = "transaction_status"):
        self.name = name
        self.statuses: List[TransactionStatus] = []

    def add_status(self, status: TransactionStatus) -> None:
        """Add a transaction status to the table."""
        self.statuses.append(status)

    def get_failed_transactions(self) -> List[TransactionStatus]:
        """Get all transactions with FAILED status."""
        return [s for s in self.statuses if s.status == 'FAILED']

    def get_warning_transactions(self) -> List[TransactionStatus]:
        """Get all transactions with WARNING status."""
        return [s for s in self.statuses if s.status == 'WARNING']

    def format_for_report(self) -> List[Dict[str, str]]:
        """Format as simple table for report (Transaction, Status, Reason)."""
        return [s.to_report_row() for s in self.statuses]

    def format_detailed(self) -> List[Dict[str, Any]]:
        """Format with detailed breakdown for debugging/analysis.

        Columns: Transaction, Status, NFR Status, Baseline Status, ML Status,
                 Reason, NFR Failures, Regressions, ML Events
        """
        detailed = []
        for s in self.statuses:
            # Use OrderedDict to maintain explicit column order
            row = OrderedDict([
                ('Transaction', s.transaction),
                ('Status', s.status),
                ('NFR Status', s.nfr_status),
                ('Baseline Status', s.baseline_status),
                ('ML Status', s.ml_status),
                ('Reason', '; '.join(s.reasons) if s.reasons else 'All checks passed'),
                ('NFR Failures', len(s.nfr_failures)),
                ('Regressions', len(s.baseline_regressions)),
                ('ML Events', len(s.ml_events))
            ])
            detailed.append(row)
        return detailed
