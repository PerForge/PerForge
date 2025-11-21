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

from dataclasses import dataclass
from typing import Optional, Any, Dict
from app.backend.components.nfrs.nfr_validation import NFRStatus


@dataclass
class Metric:
    """
    Encapsulates all information about a single metric including NFR evaluation
    """
    name: str
    value: float
    scope: Optional[str] = None  # e.g., transaction name, page name
    baseline: Optional[float] = None
    difference: Optional[float] = None
    difference_pct: Optional[float] = None
    nfr_status: NFRStatus = NFRStatus.NOT_EVALUATED
    nfr_threshold: Optional[float] = None  # NFR threshold value
    nfr_operation: Optional[str] = None  # NFR operation (e.g., '<', '>', '<=', '>=')

    def __post_init__(self):
        """Calculate differences if baseline is provided"""
        if self.baseline is not None and self.value is not None:
            self.difference = self.value - self.baseline
            if self.baseline != 0:
                self.difference_pct = (self.difference / self.baseline) * 100

    def set_nfr_status(self, status: NFRStatus, threshold: Optional[float] = None, operation: Optional[str] = None) -> None:
        """
        Set NFR evaluation status and related metadata

        Args:
            status: NFR evaluation status
            threshold: Optional threshold value used for evaluation
            operation: Optional operation used for evaluation
        """
        self.nfr_status = status
        self.nfr_threshold = threshold
        self.nfr_operation = operation

    def get_display_color(self) -> str:
        """Get color for UI display based on NFR status"""
        color_map = {
            NFRStatus.PASSED: "green",
            NFRStatus.FAILED: "red",
            NFRStatus.NOT_EVALUATED: "gray"
        }
        return color_map[self.nfr_status]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'value': self.value,
            'scope': self.scope,
            'baseline': self.baseline,
            'difference': self.difference,
            'difference_pct': self.difference_pct,
            'nfr_status': self.nfr_status.value,
            'nfr_threshold': self.nfr_threshold,
            'nfr_operation': self.nfr_operation
        }
