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
Plotly image renderer for server-side chart generation.

This module provides a `PlotlyImageRenderer` class that mirrors the frontend
Plotly styling defined in `app/static/assets/js/report.js` and
`app/api/reports.py:get_report_data()`.

Usage example:

    renderer = PlotlyImageRenderer()
    renderer.create_throughput_users(chart_data, "./out/throughput_users.png")

Requirements:
    - Kaleido 1.0+ requires Chrome/Chromium to be installed separately
    - Install kaleido: pip install -U plotly kaleido
    - Install Chrome (if not present): python -c 'import kaleido; kaleido.get_chrome_sync()'
    - Docker: Chrome is auto-installed via Dockerfile
    - Windows: Download Chrome from https://www.google.com/chrome/
    - Linux: sudo apt-get install chromium-browser

Note: This implementation includes retry logic for Windows subprocess cleanup issues.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import re
import os
import logging
import tempfile
import time

# Third-party
import plotly.graph_objects as go
import kaleido
from datetime import datetime, timedelta
from dateutil import parser as date_parser

# --------------------------------------------------------------------------------------
# Defaults matching frontend styling
# --------------------------------------------------------------------------------------

_DEFAULT_STYLING: Dict[str, Any] = {
    "paper_bgcolor": "#232324",
    "plot_bgcolor": "#232324",
    "title_font_color": "#d1d1d1",
    "axis_font_color": "#d1d1d1",
    "legend_font_color": "#d1d1d1",
    "legend_font_size": 13,
    "hover_bgcolor": "#333",
    "hover_bordercolor": "#d1d1d1",
    "hover_font_color": "#d1d1d1",
    "line_shape": "spline",
    "line_width": 2,
    "marker_size": 8,
    "marker_color_normal": "rgba(75, 192, 192, 1)",
    "marker_color_anomaly": "red",
    "yaxis_tickformat": ",.0f",
    "font_family": "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Color Emoji', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', sans-serif",
    "yaxis_tickfont_size": 13,
    "xaxis_tickfont_size": 13,
    "title_size": 15,
    "gridcolor": "#3b3b3d",
}

_DEFAULT_LAYOUT: Dict[str, Any] = {
    "margin": {"l": 50, "r": 50, "b": 50, "t": 50, "pad": 1},
    # 'responsive' is a browser thing, but margins etc. still apply
    "autosize": True,
}


class PlotlyImageRenderer:
    """
    Server-side Plotly renderer that mirrors the frontend charts and styling.

    Inputs are compatible with the metrics dictionary returned by
    `DataProvider.collect_test_data_for_report_page()` and exposed via
    `app/api/reports.py:get_report_data`.
    """

    def __init__(
        self,
        styling: Optional[Dict[str, Any]] = None,
        layout_config: Optional[Dict[str, Any]] = None,
        *,
        quiet_logs: bool = True,
        log_level: int = logging.WARNING,
    ):
        self.styling: Dict[str, Any] = {**_DEFAULT_STYLING, **(styling or {})}
        self.layout_config: Dict[str, Any] = {**_DEFAULT_LAYOUT, **(layout_config or {})}
        # Reduce very chatty INFO logs from Kaleido/Choreographer by default
        if quiet_logs:
            self._configure_third_party_logging(log_level)
    # ----------------------------------------------------------------------------------
    # Public API - High level rendering methods
    # ----------------------------------------------------------------------------------

    def create_throughput_users(self, chart_data: Dict[str, Any], output_path: str, *, width: int = 1024, height: int = 400, image_format: str = "png") -> str:
        """Render 'Throughput and Users' line chart to an image file.

        Expects chart_data keys: 'overalThroughput', 'overalUsers'.
        """
        timestamps = self._extract_timestamps(chart_data, "overalAvgResponseTime") or self._extract_timestamps(chart_data, "overalThroughput")
        throughput = self._extract_values(chart_data, "overalThroughput")
        users = self._extract_values(chart_data, "overalUsers")
        throughput_anomalies, throughput_msgs = self._extract_anomalies(chart_data, "overalThroughput")

        metrics = [
            {"name": "Throughput", "data": throughput, "anomalies": throughput_anomalies, "anomalyMessages": throughput_msgs, "color": "rgba(31, 119, 180, 1)", "yAxisUnit": "r/s"},
            {"name": "Users", "data": users, "anomalies": [], "anomalyMessages": [], "color": "rgba(0, 155, 162, 0.8)", "yAxisUnit": "vu", "useRightYAxis": True},
        ]
        overall_windows = (chart_data.get("overall_anomaly_windows") or {}).get("overalThroughput") or []
        return self._build_line_chart(
            title="Throughput and Users",
            labels=timestamps,
            metrics=metrics,
            anomaly_windows=overall_windows,
            output_path=output_path,
            width=width,
            height=height,
            image_format=image_format,
        )

    def create_response_time(self, chart_data: Dict[str, Any], output_path: str, *, width: int = 1024, height: int = 400, image_format: str = "png") -> str:
        """Render 'Response Time' line chart (Avg/Median/90Pct) to an image file."""
        timestamps = self._extract_timestamps(chart_data, "overalAvgResponseTime")
        avg_vals, avg_ano, avg_msgs = self._extract_series(chart_data, "overalAvgResponseTime")
        med_vals, med_ano, med_msgs = self._extract_series(chart_data, "overalMedianResponseTime")
        p90_vals, p90_ano, p90_msgs = self._extract_series(chart_data, "overal90PctResponseTime")

        metrics = [
            {"name": "Avg Response Time", "data": avg_vals, "anomalies": avg_ano, "anomalyMessages": avg_msgs, "color": "rgba(2, 208, 81, 0.8)", "yAxisUnit": "ms"},
            {"name": "Median Response Time", "data": med_vals, "anomalies": med_ano, "anomalyMessages": med_msgs, "color": "rgba(23, 100, 254, 0.8)", "yAxisUnit": "ms"},
            {"name": "90Pct Response Time", "data": p90_vals, "anomalies": p90_ano, "anomalyMessages": p90_msgs, "color": "rgba(245, 165, 100, 1)", "yAxisUnit": "ms"},
        ]
        # Union anomaly windows across RT overall metrics
        overall_windows_rt = []
        overall_map = chart_data.get("overall_anomaly_windows") or {}
        for key in ("overalAvgResponseTime", "overalMedianResponseTime", "overal90PctResponseTime"):
            wins = overall_map.get(key) or []
            overall_windows_rt.extend(wins)
        return self._build_line_chart(
            title="Response Time",
            labels=timestamps,
            metrics=metrics,
            anomaly_windows=overall_windows_rt,
            output_path=output_path,
            width=width,
            height=height,
            image_format=image_format,
        )

    def create_errors(self, chart_data: Dict[str, Any], output_path: str, *, width: int = 1024, height: int = 320, image_format: str = "png") -> str:
        """Render 'Errors' line chart to an image file."""
        timestamps = self._extract_timestamps(chart_data, "overalErrors") or self._extract_timestamps(chart_data, "overalAvgResponseTime")
        err_vals = self._extract_values(chart_data, "overalErrors")
        metrics = [
            {"name": "Errors", "data": err_vals, "anomalies": [], "anomalyMessages": [], "color": "rgba(255, 8, 8, 0.8)", "yAxisUnit": "er"},
        ]
        overall_windows = (chart_data.get("overall_anomaly_windows") or {}).get("overalErrors") or []
        return self._build_line_chart(
            title="Errors",
            labels=timestamps,
            metrics=metrics,
            anomaly_windows=overall_windows,
            output_path=output_path,
            width=width,
            height=height,
            image_format=image_format,
        )

    def create_transaction_response_time(self, chart_data: Dict[str, Any], transaction_name: str, output_path: str, *, width: int = 1024, height: int = 360, image_format: str = "png") -> str:
        """Render per-transaction response time chart (Avg/Median/Pct90) to an image file."""
        avg_tx = self._find_transaction_series(chart_data, "avgResponseTimePerReq", transaction_name)
        med_tx = self._find_transaction_series(chart_data, "medianResponseTimePerReq", transaction_name)
        p90_tx = self._find_transaction_series(chart_data, "pctResponseTimePerReq", transaction_name)
        if not (avg_tx and med_tx and p90_tx):
            raise ValueError(f"Transaction data not found for '{transaction_name}'.")

        timestamps = [self._parse_ts(p["timestamp"]) for p in avg_tx["data"]]
        avg_vals = [p["value"] for p in avg_tx["data"]]
        med_vals = [p["value"] for p in med_tx["data"]]
        p90_vals = [p["value"] for p in p90_tx["data"]]

        metrics = [
            {"name": "Avg Response Time", "data": avg_vals, "anomalies": [], "anomalyMessages": [], "color": "rgba(2, 208, 81, 0.8)", "yAxisUnit": "ms"},
            {"name": "Median Response Time", "data": med_vals, "anomalies": [], "anomalyMessages": [], "color": "rgba(23, 100, 254, 0.8)", "yAxisUnit": "ms"},
            {"name": "Pct90 Response Time", "data": p90_vals, "anomalies": [], "anomalyMessages": [], "color": "rgba(245, 165, 100, 1)", "yAxisUnit": "ms"},
        ]
        return self._build_line_chart(
            title=transaction_name,
            labels=timestamps,
            metrics=metrics,
            output_path=output_path,
            width=width,
            height=height,
            image_format=image_format,
        )

    # ----------------------------------------------------------------------------------
    # Internals - helpers
    # ----------------------------------------------------------------------------------

    def _configure_third_party_logging(self, level: int = logging.WARNING) -> None:
        """Silence noisy third-party loggers used by Plotly Kaleido backend.

        Important: we avoid instantiating third-party loggers directly (via
        logging.getLogger(name)) because some libraries customize the logger
        class (e.g., adding methods like `debug2`). Creating them too early can
        result in standard Logger instances without those methods. Instead, we
        attach a filter to existing root handlers that drops records from
        targeted packages below the desired level.
        """
        prefixes = (
            "kaleido",
            "choreographer",
        )

        class _PkgLevelFilter(logging.Filter):
            def __init__(self, pkg_prefixes: tuple[str, ...], min_level: int) -> None:
                super().__init__()
                self._prefixes = pkg_prefixes
                self._min_level = min_level

            def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
                if record.name.startswith(self._prefixes):
                    return record.levelno >= self._min_level
                return True

        root = logging.getLogger()
        for h in getattr(root, "handlers", []):
            # Avoid adding duplicate filters to the same handler
            if not getattr(h, "_pf_quiet_kaleido_filter", False):
                h.addFilter(_PkgLevelFilter(prefixes, level))
                setattr(h, "_pf_quiet_kaleido_filter", True)

    def _build_line_chart(self, title: str, labels: List[datetime], metrics: List[Dict[str, Any]], output_path: str, *, width: int, height: int, image_format: str, anomaly_windows: Optional[List[Dict[str, Any]]] = None) -> str:
        fig = self._build_line_chart_figure(title=title, labels=labels, metrics=metrics, anomaly_windows=anomaly_windows)
        return self._save(fig, output_path, width, height, image_format)

    def _build_line_chart_figure(self, title: str, labels: List[datetime], metrics: List[Dict[str, Any]], anomaly_windows: Optional[List[Dict[str, Any]]] = None) -> go.Figure:
        traces: List[go.Scatter] = []
        # Prepare colors for axes
        left_metric = next((m for m in metrics if not m.get("useRightYAxis")), metrics[0])
        right_metric = next((m for m in metrics if m.get("useRightYAxis")), None)
        left_y_color = left_metric["color"]
        right_y_color = right_metric["color"] if right_metric else left_y_color

        for m in metrics:
            anomalies: List[bool] = m.get("anomalies", []) or [False] * len(m.get("data", []))
            anomaly_msgs: List[str] = m.get("anomalyMessages", []) or [""] * len(m.get("data", []))

            trace = go.Scatter(
                x=labels,
                y=m["data"],
                mode="lines",  # lines only; no markers/dots
                name=m["name"],
                line=dict(shape=self.styling["line_shape"], width=self.styling["line_width"], color=m["color"]),
                hoverinfo="x+y+text",
                text=[msg if anomalies[i] else "" for i, msg in enumerate(anomaly_msgs)],
                yaxis="y2" if m.get("useRightYAxis") else "y",
                cliponaxis=False,
            )
            traces.append(trace)

        layout = self._base_layout(title, left_y_color=left_y_color, right_y_color=right_y_color, metrics=metrics, labels=labels)

        # Add shaded anomaly bands if explicit windows were provided
        try:
            shapes: List[Dict[str, Any]] = []
            if anomaly_windows:
                # Normalize and merge overlapping windows
                normalized = []
                for win in anomaly_windows:
                    if not win:
                        continue
                    raw_start = win.get("start") or win.get("x0")
                    raw_end = win.get("end") or win.get("x1")
                    if not raw_start or not raw_end:
                        continue
                    try:
                        s = self._parse_ts(str(raw_start))
                        e = self._parse_ts(str(raw_end))
                    except Exception:
                        continue
                    if s <= e:
                        normalized.append({"start": s, "end": e})
                    else:
                        normalized.append({"start": e, "end": s})

                normalized.sort(key=lambda w: w["start"])
                merged: List[Dict[str, datetime]] = []
                for win in normalized:
                    if not merged:
                        merged.append({"start": win["start"], "end": win["end"]})
                        continue
                    last = merged[-1]
                    if win["start"] <= last["end"]:
                        if win["end"] > last["end"]:
                            last["end"] = win["end"]
                    else:
                        merged.append({"start": win["start"], "end": win["end"]})

                for win in merged:
                    x0 = win["start"]
                    x1 = win["end"]
                    is_point_anomaly = x0 == x1

                    if is_point_anomaly:
                        # Expand by 2 minutes on each side
                        expansion = timedelta(minutes=2)
                        x0 = x0 - expansion
                        x1 = x1 + expansion

                        # Add vertical dotted line
                        shapes.append(
                            dict(
                                type="line",
                                xref="x",
                                yref="paper",
                                x0=win["start"],
                                x1=win["start"],
                                y0=0,
                                y1=1,
                                line=dict(
                                    color="rgba(231, 14, 36, 0.8)",
                                    width=2,
                                    dash="dot",
                                ),
                            )
                        )

                    shapes.append(
                        dict(
                            type="rect",
                            xref="x",
                            yref="paper",
                            x0=x0,
                            x1=x1,
                            y0=0,
                            y1=1,
                            fillcolor="rgba(220, 53, 69, 0.25)",
                            line=dict(width=0),
                        )
                    )

            if shapes:
                # Preserve any existing shapes in layout_config
                base_shapes = list(layout.shapes) if getattr(layout, "shapes", None) else []
                layout.shapes = tuple(base_shapes + shapes)
        except Exception as e:
            logging.warning(f"_build_line_chart_figure: failed to attach anomaly window shapes: {e}")

        fig = go.Figure(data=traces, layout=layout)
        return fig

    def _base_layout(self, title: str, *, left_y_color: Optional[str] = None, right_y_color: Optional[str] = None, metrics: Optional[List[Dict[str, Any]]] = None, labels: Optional[List[datetime]] = None) -> go.Layout:
        layout_cfg = self.layout_config or {}
        styling = self.styling

        # Determine units for axes
        left_unit = ""
        right_unit = ""
        if metrics:
            left = next((m for m in metrics if not m.get("useRightYAxis")), metrics[0])
            left_unit = f" {left.get('yAxisUnit', '')}"
            right = next((m for m in metrics if m.get("useRightYAxis")), None)
            right_unit = f" {right.get('yAxisUnit', '')}" if right else ""

        # Calculate x-axis range with padding
        xaxis_range = None
        if labels:
            try:
                # Filter out None values just in case
                valid_labels = [l for l in labels if l]
                if valid_labels:
                    min_time = min(valid_labels)
                    max_time = max(valid_labels)
                    duration = max_time - min_time

                    # Add 5% padding on each side, or default to 1 minute
                    padding = duration * 0.03 if duration.total_seconds() > 0 else timedelta(minutes=1)

                    xaxis_range = [min_time - padding, max_time + padding]
            except Exception as e:
                logging.warning(f"Failed to calculate xaxis range: {e}")

        layout = go.Layout(
            title=dict(
                text=title,
                font=dict(color=styling["title_font_color"], family=styling["font_family"], size=styling["title_size"]),
            ),
            paper_bgcolor=styling["paper_bgcolor"],
            plot_bgcolor=styling["plot_bgcolor"],
            margin=layout_cfg.get("margin", dict(l=50, r=50, b=50, t=50, pad=1)),
            xaxis=dict(
                tickfont=dict(color=styling["axis_font_color"], family=styling["font_family"], size=styling["xaxis_tickfont_size"]),
                color=styling["axis_font_color"],
                gridcolor=styling["gridcolor"],
                tickformat='%I:%M %p',  # 12-hour format without seconds
                range=xaxis_range,
            ),
            yaxis=dict(
                tickfont=dict(color=left_y_color or styling["axis_font_color"], family=styling["font_family"], size=styling["yaxis_tickfont_size"]),
                color=left_y_color or styling["axis_font_color"],
                ticksuffix=left_unit,
                zeroline=False,
                gridcolor=styling["gridcolor"],
                rangemode="tozero",
            ),
            yaxis2=dict(
                tickfont=dict(color=right_y_color or styling["axis_font_color"], family=styling["font_family"], size=styling["yaxis_tickfont_size"]),
                color=right_y_color or styling["axis_font_color"],
                ticksuffix=right_unit,
                zeroline=False,
                overlaying="y",
                side="right",
                showgrid=False,
                rangemode="tozero",
            ),
            hoverlabel=dict(
                bgcolor=styling["hover_bgcolor"],
                bordercolor=styling["hover_bordercolor"],
                font=dict(color=styling["hover_font_color"], family=styling["font_family"]),
            ),
            legend=dict(
                orientation="h",
                x=0,
                y=-0.2,
                xanchor="left",
                yanchor="top",
                font=dict(
                    color=styling["legend_font_color"],
                    family=styling["font_family"],
                    size=styling["legend_font_size"],
                ),
            ),
        )
        return layout

    def _save(self, fig: go.Figure, output_path: str, width: int, height: int, image_format: str) -> str:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        # Retry logic for transient failures (especially Windows subprocess cleanup issues)
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                # Use higher pixel density by default for crisper images (no external config)
                kaleido.write_fig_sync(
                    fig,
                    path=output_path,
                    opts={"format": image_format, "width": width, "height": height, "scale": 3},
                )
                break  # Success
            except RuntimeError as e:
                last_error = e
                error_msg = str(e)

                # Handle subprocess cleanup errors (known issue on Windows)
                if "browser subprocess" in error_msg.lower():
                    # Check if file was actually created despite the error
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        logging.warning(
                            f"Kaleido subprocess cleanup error (attempt {attempt + 1}), "
                            "but image was saved successfully"
                        )
                        break  # Image created successfully despite cleanup error
                    elif attempt < max_retries - 1:
                        logging.warning(f"Kaleido subprocess error on attempt {attempt + 1}, retrying...")
                        time.sleep(0.5)  # Brief delay before retry
                        continue
                raise  # Re-raise if not a known issue or last attempt
            except Exception as e:
                last_error = e
                # Re-raise non-RuntimeError exceptions immediately
                raise RuntimeError(
                    "Failed to write image. Ensure 'kaleido' is installed and Chrome is available.\n"
                    "Install Chrome: python -c 'import kaleido; kaleido.get_chrome_sync()'\n"
                    f"Original error: {e}"
                ) from e

        # Verify file exists and has content
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError(
                f"Image file was not created successfully at {output_path}. Last error: {last_error}"
            )

        return output_path

    def _to_image_bytes(self, fig: go.Figure, *, width: int, height: int, image_format: str = "png") -> bytes:
        tmp_path = None
        try:
            # Use higher pixel density by default for crisper images (no external config)
            suffix = f".{image_format}"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp_path = tmp.name

            # Retry logic for transient failures (especially Windows subprocess cleanup issues)
            max_retries = 3
            last_error = None

            for attempt in range(max_retries):
                try:
                    kaleido.write_fig_sync(
                        fig,
                        path=tmp_path,
                        opts={"format": image_format, "width": width, "height": height, "scale": 3},
                    )
                    break  # Success
                except RuntimeError as e:
                    last_error = e
                    error_msg = str(e)

                    # Handle subprocess cleanup errors (known issue on Windows)
                    if "browser subprocess" in error_msg.lower():
                        # Check if file was actually created despite the error
                        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                            logging.warning(
                                f"Kaleido subprocess cleanup error (attempt {attempt + 1}), "
                                "but image was generated successfully"
                            )
                            break  # Image created successfully despite cleanup error
                        elif attempt < max_retries - 1:
                            logging.warning(f"Kaleido subprocess error on attempt {attempt + 1}, retrying...")
                            time.sleep(0.5)  # Brief delay before retry
                            continue
                    raise  # Re-raise if not a known issue or last attempt

            # Verify file exists and has content
            if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
                raise RuntimeError(
                    f"Image file was not created successfully. Last error: {last_error}"
                )

            with open(tmp_path, "rb") as f:
                data = f.read()

        except Exception as e:
            # Provide helpful guidance for common issues
            raise RuntimeError(
                "Failed to render image to bytes. Ensure 'kaleido' is installed and Chrome is available.\n"
                "Install Chrome: python -c 'import kaleido; kaleido.get_chrome_sync()'\n"
                f"Original error: {e}"
            ) from e
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass  # Ignore cleanup errors

        return data

    # ----------------------------------------------------------------------------------
    # Public API - In-memory rendering methods
    # ----------------------------------------------------------------------------------

    def create_throughput_users_bytes(self, chart_data: Dict[str, Any], *, width: int = 1024, height: int = 400, image_format: str = "png") -> bytes:
        timestamps = self._extract_timestamps(chart_data, "overalAvgResponseTime") or self._extract_timestamps(chart_data, "overalThroughput")
        throughput = self._extract_values(chart_data, "overalThroughput")
        users = self._extract_values(chart_data, "overalUsers")
        throughput_anomalies, throughput_msgs = self._extract_anomalies(chart_data, "overalThroughput")

        metrics = [
            {"name": "Throughput", "data": throughput, "anomalies": throughput_anomalies, "anomalyMessages": throughput_msgs, "color": "rgba(31, 119, 180, 1)", "yAxisUnit": "r/s"},
            {"name": "Users", "data": users, "anomalies": [], "anomalyMessages": [], "color": "rgba(0, 155, 162, 0.8)", "yAxisUnit": "vu", "useRightYAxis": True},
        ]
        overall_windows = (chart_data.get("overall_anomaly_windows") or {}).get("overalThroughput") or []
        fig = self._build_line_chart_figure(
            title="Throughput and Users",
            labels=timestamps,
            metrics=metrics,
            anomaly_windows=overall_windows,
        )
        return self._to_image_bytes(fig, width=width, height=height, image_format=image_format)

    def create_response_time_bytes(self, chart_data: Dict[str, Any], *, width: int = 1024, height: int = 400, image_format: str = "png") -> bytes:
        timestamps = self._extract_timestamps(chart_data, "overalAvgResponseTime")
        avg_vals, avg_ano, avg_msgs = self._extract_series(chart_data, "overalAvgResponseTime")
        med_vals, med_ano, med_msgs = self._extract_series(chart_data, "overalMedianResponseTime")
        p90_vals, p90_ano, p90_msgs = self._extract_series(chart_data, "overal90PctResponseTime")

        metrics = [
            {"name": "Avg Response Time", "data": avg_vals, "anomalies": avg_ano, "anomalyMessages": avg_msgs, "color": "rgba(2, 208, 81, 0.8)", "yAxisUnit": "ms"},
            {"name": "Median Response Time", "data": med_vals, "anomalies": med_ano, "anomalyMessages": med_msgs, "color": "rgba(23, 100, 254, 0.8)", "yAxisUnit": "ms"},
            {"name": "90Pct Response Time", "data": p90_vals, "anomalies": p90_ano, "anomalyMessages": p90_msgs, "color": "rgba(245, 165, 100, 1)", "yAxisUnit": "ms"},
        ]
        overall_windows_rt: List[Dict[str, Any]] = []
        overall_map = chart_data.get("overall_anomaly_windows") or {}
        for key in ("overalAvgResponseTime", "overalMedianResponseTime", "overal90PctResponseTime"):
            wins = overall_map.get(key) or []
            overall_windows_rt.extend(wins)
        fig = self._build_line_chart_figure(
            title="Response Time",
            labels=timestamps,
            metrics=metrics,
            anomaly_windows=overall_windows_rt,
        )
        return self._to_image_bytes(fig, width=width, height=height, image_format=image_format)

    def create_errors_bytes(self, chart_data: Dict[str, Any], *, width: int = 1024, height: int = 320, image_format: str = "png") -> bytes:
        timestamps = self._extract_timestamps(chart_data, "overalErrors") or self._extract_timestamps(chart_data, "overalAvgResponseTime")
        err_vals = self._extract_values(chart_data, "overalErrors")
        metrics = [
            {"name": "Errors", "data": err_vals, "anomalies": [], "anomalyMessages": [], "color": "rgba(255, 8, 8, 0.8)", "yAxisUnit": "er"},
        ]
        overall_windows = (chart_data.get("overall_anomaly_windows") or {}).get("overalErrors") or []
        fig = self._build_line_chart_figure(
            title="Errors",
            labels=timestamps,
            metrics=metrics,
            anomaly_windows=overall_windows,
        )
        return self._to_image_bytes(fig, width=width, height=height, image_format=image_format)

    # ----------------------------------------------------------------------------------
    # Name-to-function mapping
    # ----------------------------------------------------------------------------------

    @staticmethod
    def _normalize_key(name: str) -> str:
        key = name.lower()
        key = re.sub(r"[^a-z0-9]+", "_", key)
        return key.strip("_")

    def renderer_map(self):
        """
        Return a normalized name-to-renderer mapping for internal graphs.

        Keys are normalized (lowercased, non-alnum -> '_'). Include common synonyms.
        """
        return {
            # Throughput & Users
            "throughput_and_users": self.create_throughput_users_bytes,
            "throughput_users": self.create_throughput_users_bytes,
            # Response Time
            "response_time": self.create_response_time_bytes,
            # Errors
            "errors": self.create_errors_bytes,
        }

    def render_bytes_by_name(self, name: str, chart_data: Dict[str, Any], *, width: int = 1024, height: int = 400, image_format: str = "png") -> bytes:
        key = self._normalize_key(name)
        mapping = self.renderer_map()
        func = mapping.get(key)
        if not func:
            raise KeyError(f"No internal renderer found for graph name '{name}' (normalized key '{key}').")
        # Some charts prefer specific default heights (e.g., errors)
        if key == "errors" and height == 400:
            height = 320
        return func(chart_data, width=width, height=height, image_format=image_format)

    # ------------------------------- Extraction helpers -------------------------------

    def _extract_timestamps(self, chart_data: Dict[str, Any], key: str) -> List[datetime]:
        series = chart_data.get(key, {})
        data = series.get("data", []) if isinstance(series, dict) else []
        return [self._parse_ts(p.get("timestamp")) for p in data]

    def _extract_values(self, chart_data: Dict[str, Any], key: str) -> List[float]:
        series = chart_data.get(key, {})
        data = series.get("data", []) if isinstance(series, dict) else []
        return [p.get("value") for p in data]

    def _extract_anomalies(self, chart_data: Dict[str, Any], key: str) -> tuple[List[bool], List[str]]:
        series = chart_data.get(key, {})
        data = series.get("data", []) if isinstance(series, dict) else []
        anomalies = [(p.get("anomaly") != "Normal") for p in data]
        messages = [p.get("anomaly", "") for p in data]
        return anomalies, messages

    def _extract_series(self, chart_data: Dict[str, Any], key: str) -> tuple[List[float], List[bool], List[str]]:
        values = self._extract_values(chart_data, key)
        anomalies, messages = self._extract_anomalies(chart_data, key)
        return values, anomalies, messages

    def _find_transaction_series(self, chart_data: Dict[str, Any], key: str, transaction_name: str) -> Optional[Dict[str, Any]]:
        arr = chart_data.get(key)
        if not isinstance(arr, list):
            return None
        return next((tx for tx in arr if tx.get("name") == transaction_name), None)

    def _parse_ts(self, value: str) -> datetime:
        """Parse ISO timestamp string to datetime; supports 'Z' suffix."""
        # dateutil handles most formats including Zulu time
        return date_parser.isoparse(value)
