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

"""
Base classes and utilities for data insertion implementations.

This mirrors the structure used for extraction (see `base_extraction.py`),
providing a common interface for configuration/client lifecycle and a
standard write API surface that concrete integrations (e.g. InfluxDB V2)
should implement.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Dict

import pandas as pd


class DataInsertionBase(ABC):
    """
    Abstract base class for all data insertion implementations.

    Responsibilities:
    - Hold project context and provide hooks for configuration loading.
    - Provide context manager hooks to initialize/close the client.
    - Define a standard write API to be implemented by concrete classes.
    """

    def __init__(self, project: int):
        self.project = project

    # -------------------- Configuration & Client --------------------
    @abstractmethod
    def set_config(self, id: int | None) -> None:
        """Load configuration for the concrete integration by id or default."""
        pass

    @abstractmethod
    def _initialize_client(self) -> None:
        """Initialize the underlying client/connection."""
        pass

    @abstractmethod
    def _close_client(self) -> None:
        """Close the underlying client/connection."""
        pass

    def __enter__(self):
        try:
            self._initialize_client()
        except Exception as er:
            logging.error(f"Failed to initialize insertion client: {er}")
            raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self._close_client()
        except Exception as er:
            logging.error(f"Failed to close insertion client: {er}")

    # -------------------- Public Write API --------------------
    @abstractmethod
    def write_upload(
        self,
        df: pd.DataFrame,
        test_title: str,
        write_events: bool = True,
        aggregation_window: str = "5s",
    ) -> Dict[str, int]:
        """
        Write dataset represented by the normalized DataFrame to the target store.

        Must return a dict with at least: { "points_written": int }.
        Input validation is responsibility of the concrete implementation.
        """
        pass
