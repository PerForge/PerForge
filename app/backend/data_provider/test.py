# Copyright 2024 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>

from typing import Optional

class Test:
    """
    Test class represents a performance test and its attributes.

    This class encapsulates all test-related data including timing information,
    performance metrics, and test metadata.
    """

    def __init__(self) -> None:
        self.test_title: Optional[str] = None
        self.start_time_human: Optional[str] = None
        self.end_time_human: Optional[str] = None
        self.start_time_iso: Optional[str] = None
        self.end_time_iso: Optional[str] = None
        self.start_time_timestamp: Optional[float] = None
        self.end_time_timestamp: Optional[float] = None
        self.application: Optional[str] = None
        self.test_type: Optional[str] = None
        self.duration: Optional[str] = None
        self.max_active_users: Optional[int] = None
        self.median_throughput: Optional[float] = None
        self.median_response_time_stats: Optional[float] = None
        self.pct90_response_time_stats: Optional[float] = None
        self.errors_pct_stats: Optional[float] = None

    def calculate_duration(self) -> None:
        """Calculate test duration from start and end timestamps."""
        if self.start_time_timestamp and self.end_time_timestamp:
            self.duration = str(int((self.end_time_timestamp - self.start_time_timestamp) / 1000))
