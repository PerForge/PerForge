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
InfluxDB v2 write-side integration.

This module encapsulates the end-to-end flow required to persist aggregated
JMeter samples and lightweight discovery events into InfluxDB v2. It handles:

- configuration loading (URL/org/bucket/token/test title tag),
- client lifecycle (connect/close),
- point construction for the "jmeter" and "events" measurements,
- robust, synchronous batched writes, and
- best-effort rollback via the Delete API if a write fails.

Only write logic lives here. Read/analytics live elsewhere.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any

import numpy as np
import pandas as pd
from datetime import timedelta
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from app.backend.integrations.data_sources.influxdb_v2.influxdb_db import DBInfluxdb
from app.backend.components.secrets.secrets_db import DBSecrets
from app.backend.errors import ErrorMessages
from app.backend.integrations.data_sources.base_insertion import DataInsertionBase


class InfluxdbV2Insertion(DataInsertionBase):
    """InfluxDB v2 insertion implementation.

    Provides a small façade around the InfluxDB Python client to reliably write
    time-series derived from JMeter results. The class is intended to be used as
    a short-lived object (per upload) and supports usage as a context manager.
    """

    def __init__(self, project: int, id: int | None = None):
        super().__init__(project)
        self.influxdb_connection: InfluxDBClient | None = None
        self.set_config(id)
        self._initialize_client()

    def __enter__(self) -> "InfluxdbV2Insertion":
        self._initialize_client()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._close_client()

    # -------------------- Configuration & Client --------------------
    def set_config(self, id: int | None) -> None:
        """Load integration configuration and resolve the secret token.

        Picks the provided configuration by id or falls back to the project's
        default InfluxDB config. Populates instance attributes with connection
        parameters and metadata used for tagging writes.
        """
        id = id if id else DBInfluxdb.get_default_config(project_id=self.project)["id"]
        config = DBInfluxdb.get_config_by_id(project_id=self.project, id=id)
        if config["id"]:
            self.id = config["id"]
            self.name = config["name"]
            self.url = config["url"]
            self.org_id = config["org_id"]
            self.token = DBSecrets.get_config_by_id(project_id=self.project, id=config["token"]) ["value"]
            self.timeout = config["timeout"]
            self.bucket = config["bucket"]
            self.listener = config["listener"]
            self.test_title_tag_name = config["test_title_tag_name"]
            self.tmz = config["tmz"]
        else:
            logging.warning("There's no InfluxDB integration configured, or you're attempting to send a request from an unsupported location.")

    def _initialize_client(self) -> None:
        """Create an InfluxDB client if it is not already initialized."""
        if self.influxdb_connection is not None:
            return
        try:
            self.influxdb_connection = InfluxDBClient(
                url=self.url, org=self.org_id, token=self.token, timeout=int(self.timeout or 60000)
            )
        except Exception as er:
            logging.error(ErrorMessages.ER00052.value.format(self.name))
            logging.error(er)

    def _close_client(self) -> None:
        """Close the InfluxDB client and release resources."""
        if self.influxdb_connection:
            try:
                self.influxdb_connection.close()
            except Exception as er:
                logging.error(ErrorMessages.ER00053.value.format(self.name))
                logging.error(er)
            finally:
                self.influxdb_connection = None

    # -------------------- Public API --------------------
    def write_upload(self, df: pd.DataFrame, test_title: str, write_events: bool = True, aggregation_window: str = "5s") -> Dict[str, Any]:
        """Aggregate JMeter samples and write them into InfluxDB.

        Parameters
        - df: A DataFrame of normalized JMeter samples. It must contain either
          a DatetimeIndex named "timestamp" or a "timestamp" column. Required
          columns: "label", "elapsed", "success". Optional columns are
          auto-filled if missing: "bytes", "sentBytes", "responseCode",
          "responseMessage", "allThreads".
        - test_title: Logical name of the test used to tag data points.
        - write_events: If True, also emit lightweight "events" points marking
          the start and end timestamps of the upload.
        - aggregation_window: Pandas offset string used for resampling, e.g.
          "1s", "5s", "1min".

        Returns
        - dict with a single key: {"points_written": int}
        """
        if df is None or df.empty:
            return {"points_written": 0}

        # Validate aggregation_window is a positive pandas offset string
        try:
            td = pd.to_timedelta(aggregation_window)
            if td is None or td.total_seconds() <= 0:
                raise ValueError("non-positive")
        except Exception:
            raise ValueError("Parameter 'aggregation_window' must be a positive pandas offset string, e.g. 1s, 5s, 1min, 500ms")

        # Ensure required columns exist (accept either a DatetimeIndex named
        # "timestamp" or a separate "timestamp" column).
        if not isinstance(df.index, pd.DatetimeIndex) or df.index.name != "timestamp":
            if "timestamp" not in df.columns:
                raise ValueError("DataFrame must have a 'timestamp' column")
        required = ["label", "elapsed", "success"]
        missing = [c for c in required if c not in getattr(df, "columns", [])]
        if missing:
            raise ValueError(f"DataFrame missing required columns: {', '.join(missing)}")

        # Prepare DataFrame: set timestamp index and coerce types
        if not isinstance(df.index, pd.DatetimeIndex) or df.index.name != "timestamp":
            df = df.copy()
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            df = df.set_index("timestamp").sort_index()
        else:
            df = df.copy()

        # Ensure optional columns
        for col, default in [("bytes", 0), ("sentBytes", 0), ("responseCode", ""), ("responseMessage", ""), ("allThreads", 0)]:
            if col not in df.columns:
                df[col] = default

        # Coerce types consistently
        df["elapsed"] = pd.to_numeric(df["elapsed"], errors="coerce")
        df["bytes"] = pd.to_numeric(df["bytes"], errors="coerce").fillna(0).astype(int)
        df["sentBytes"] = pd.to_numeric(df["sentBytes"], errors="coerce").fillna(0).astype(int)
        df["allThreads"] = pd.to_numeric(df.get("allThreads", 0), errors="coerce").fillna(0).astype(int)
        df["success"] = df["success"].astype(bool)
        df["label"] = df["label"].astype(str)
        df["responseCode"] = df["responseCode"].astype(str)
        df["responseMessage"] = df["responseMessage"].astype(str)

        # Derive statut tag from success
        df["statut"] = np.where(df["success"].astype(bool), "ok", "ko")

        points: List[Point] = []
        test_title_tag = self.test_title_tag_name or "testTitle"
        # Time bounds for this upload (used for rollback and events). Influx delete stop is exclusive.
        start_dt = df.index.min().to_pydatetime()
        stop_dt = df.index.max().to_pydatetime() + timedelta(seconds=1)

        # Per-transaction aggregates for each statut
        def build_points_for_group(group_df: pd.DataFrame, label_val: str, statut_val: str):
            agg = group_df.resample(aggregation_window).agg(
                count=("elapsed", "count"),
                avg=("elapsed", "mean"),
                max=("elapsed", "max"),
                min=("elapsed", "min"),
                rb=("bytes", "sum"),
                sb=("sentBytes", "sum"),
            )
            pct = group_df["elapsed"].resample(aggregation_window).quantile([0.50, 0.75, 0.90, 0.95, 0.99]).unstack(level=-1)
            if not pct.empty:
                agg["pct50.0"] = pct.get(0.50, np.nan)
                agg["pct75.0"] = pct.get(0.75, np.nan)
                agg["pct90.0"] = pct.get(0.90, np.nan)
                agg["pct95.0"] = pct.get(0.95, np.nan)
                agg["pct99.0"] = pct.get(0.99, np.nan)
            agg = agg.fillna(0)

            # For cumulated series (transaction="all" and statut="all"), compute KO counts for countError
            ko_counts = None
            if label_val == "all" and statut_val == "all" and "statut" in group_df.columns:
                try:
                    ko_counts = (
                        group_df[group_df["statut"] == "ko"]["elapsed"].resample(aggregation_window).count()
                    ).reindex(agg.index, fill_value=0)
                except Exception:
                    ko_counts = None

            for ts, row in agg.iterrows():
                p = Point("jmeter").time(ts.to_pydatetime())
                p.tag(test_title_tag, test_title)
                p.tag("backend_listener", "perforge")
                p.tag("transaction", label_val)
                p.tag("statut", statut_val)
                # Align field types with existing bucket schema
                p.field("count", float(row["count"]))
                p.field("avg", float(row["avg"]))
                p.field("max", float(row["max"]))
                p.field("min", float(row["min"]))
                # Include bytes only on per-transaction statut="all"
                if statut_val == "all":
                    p.field("rb", float(row["rb"]))
                    p.field("sb", float(row["sb"]))
                # Include hit and countError only for cumulated series transaction="all" & statut="all"
                if label_val == "all" and statut_val == "all":
                    p.field("hit", float(row["count"]))
                    if ko_counts is not None:
                        try:
                            p.field("countError", float(ko_counts.loc[ts]))
                        except Exception:
                            p.field("countError", 0.0)
                if "pct50.0" in row:
                    p.field("pct50.0", float(row["pct50.0"]))
                if "pct75.0" in row:
                    p.field("pct75.0", float(row["pct75.0"]))
                if "pct90.0" in row:
                    p.field("pct90.0", float(row["pct90.0"]))
                if "pct95.0" in row:
                    p.field("pct95.0", float(row["pct95.0"]))
                if "pct99.0" in row:
                    p.field("pct99.0", float(row["pct99.0"]))
                points.append(p)

        for label_val, g_label in df.groupby("label"):
            build_points_for_group(g_label, str(label_val), "all")
            g_ok = g_label[g_label["statut"] == "ok"]
            if not g_ok.empty:
                build_points_for_group(g_ok, str(label_val), "ok")
            g_ko = g_label[g_label["statut"] == "ko"]
            if not g_ko.empty:
                build_points_for_group(g_ko, str(label_val), "ko")

        # Additionally, write combined aggregates with transaction="all" to match BL
        build_points_for_group(df, "all", "all")
        g_ok_all = df[df["statut"] == "ok"]
        if not g_ok_all.empty:
            build_points_for_group(g_ok_all, "all", "ok")
        g_ko_all = df[df["statut"] == "ko"]
        if not g_ko_all.empty:
            build_points_for_group(g_ko_all, "all", "ko")

        # Response code counts (failures only, to match JMeter semantics)
        if "responseCode" in df.columns:
            failed = df[df["success"] == False] if "success" in df.columns else df
            # Small helpers to normalize tags consistently
            def _norm_rc(rc_raw: Any) -> str:
                """Normalize responseCode to a canonical string (e.g. 200.0 -> "200")."""
                if pd.isna(rc_raw):
                    return "0"
                rc_s = str(rc_raw).strip()
                if rc_s.lower() in ("", "nan", "none", "null"):
                    return "0"
                try:
                    return str(int(float(rc_s)))
                except Exception:
                    return rc_s

            def _norm_msg(rm_raw: Any) -> str:
                if pd.isna(rm_raw):
                    return ""
                rm_s = str(rm_raw).strip()
                return "" if rm_s.lower() in ("nan", "none", "null") else rm_s
            rc_counts = (
                failed
                .groupby([pd.Grouper(freq=aggregation_window), "label", "responseCode", "responseMessage"])  # type: ignore[arg-type]
                .size()
                .rename("count")
                .reset_index()
            )
            if not rc_counts.empty:
                for _, row in rc_counts.iterrows():
                    ts = row["timestamp"]
                    ts_dt = ts if isinstance(ts, pd.Timestamp) else pd.Timestamp(ts, tz="UTC")
                    p = Point("jmeter").time(ts_dt.to_pydatetime())
                    p.tag(test_title_tag, test_title)
                    p.tag("backend_listener", "perforge")
                    p.tag("transaction", str(row["label"]))
                    p.tag("responseCode", _norm_rc(row.get("responseCode", "")))
                    p.tag("responseMessage", _norm_msg(row.get("responseMessage", "")))
                    p.field("count", float(row["count"]))
                    points.append(p)

            # Also write combined response code counts with transaction="all"
            rc_counts_all = (
                failed
                .groupby([pd.Grouper(freq=aggregation_window), "responseCode", "responseMessage"])  # type: ignore[arg-type]
                .size()
                .rename("count")
                .reset_index()
            )
            if not rc_counts_all.empty:
                for _, row in rc_counts_all.iterrows():
                    ts = row["timestamp"]
                    ts_dt = ts if isinstance(ts, pd.Timestamp) else pd.Timestamp(ts, tz="UTC")
                    p = Point("jmeter").time(ts_dt.to_pydatetime())
                    p.tag(test_title_tag, test_title)
                    p.tag("backend_listener", "perforge")
                    p.tag("transaction", "all")
                    p.tag("responseCode", _norm_rc(row.get("responseCode", "")))
                    p.tag("responseMessage", _norm_msg(row.get("responseMessage", "")))
                    p.field("count", float(row["count"]))
                    points.append(p)

        # Active threads series: emit one "jmeter" point per window with transaction="internal"
        if "allThreads" in df.columns and not df["allThreads"].isna().all():
            at_series = df["allThreads"].astype(float)
            at_max = at_series.resample(aggregation_window).max().fillna(0).astype(int)
            at_mean = at_series.resample(aggregation_window).mean().fillna(0.0).astype(float)
            at_min = at_series.resample(aggregation_window).min().fillna(0).astype(int)
            # Vectorized startedT/endedT from diffs (avoid Python groupby-apply)
            d = at_series.diff().fillna(0)
            startedT = d.clip(lower=0).resample(aggregation_window).sum().reindex(at_max.index, fill_value=0).astype(int)
            endedT = (-d.clip(upper=0)).resample(aggregation_window).sum().reindex(at_max.index, fill_value=0).astype(int)
            idx = at_max.index
        else:
            idx = pd.to_datetime([df.index.min(), df.index.max()], utc=True)
            at_max = pd.Series(data=[0, 0], index=idx)
            at_mean = pd.Series(data=[0.0, 0.0], index=idx)
            at_min = pd.Series(data=[0, 0], index=idx)
            startedT = pd.Series(data=[0, 0], index=idx)
            endedT = pd.Series(data=[0, 0], index=idx)
        for ts in idx:
            p = Point("jmeter").time(ts.to_pydatetime())
            p.tag(test_title_tag, test_title)
            p.tag("backend_listener", "perforge")
            p.tag("transaction", "internal")
            p.field("minAT", float(at_min.loc[ts]))
            p.field("maxAT", float(at_max.loc[ts]))
            p.field("meanAT", float(at_mean.loc[ts]))
            p.field("startedT", float(startedT.loc[ts]))
            p.field("endedT", float(endedT.loc[ts]))
            points.append(p)

        # Lightweight events for test discovery
        if write_events and not df.empty:
            try:
                start_ts = df.index.min()
                end_ts = df.index.max()
                for ts, typ in [(start_ts, "start"), (end_ts, "end")]:
                    ep = Point("events").time(ts.to_pydatetime())
                    ep.tag(test_title_tag, test_title)
                    ep.tag("backend_listener", "perforge")
                    # Keep compatibility and add BL-like fields
                    ep.field("text", str(test_title))
                    points.append(ep)
                    # JMeter-style annotation event
                    jp = Point("events").time(ts.to_pydatetime())
                    jp.tag(test_title_tag, test_title)
                    jp.tag("backend_listener", "perforge")
                    jp.tag("title", "ApacheJMeter")
                    jp.field("text", f"{test_title} {'started' if typ == 'start' else 'ended'}")
                    points.append(jp)
            except Exception:
                # Non-fatal: event enrichment should not block writes
                pass

        try:
            written = self._write_points(points)
        except Exception as er:
            # Best-effort rollback: delete points of this upload by predicate and time range
            try:
                self._rollback_delete(test_title_tag, test_title, start_dt, stop_dt)
            except Exception:
                # Non-fatal: preserve original write error
                pass
            raise
        return {"points_written": written}

    # -------------------- Internals --------------------
    def _rollback_delete(self, test_title_tag: str, test_title: str, start_dt, stop_dt) -> None:
        """Best-effort rollback for the current upload.

        Deletes from the "jmeter" and "events" measurements where
        backend_listener="perforge" and the test title tag matches. Note that InfluxDB
        treats the "stop" bound as exclusive.
        """
        if not self.influxdb_connection:
            return
        try:
            delete_api = self.influxdb_connection.delete_api()
            predicates = [
                f'"backend_listener"="perforge" AND "{test_title_tag}"="{test_title}"',
            ]
            for predicate in predicates:
                try:
                    delete_api.delete(start=start_dt, stop=stop_dt, predicate=predicate, bucket=self.bucket, org=self.org_id)
                except Exception:
                    # Ignore individual predicate failures; proceed with others
                    pass
        except Exception:
            # Swallow rollback errors; caller handles original write exception
            pass

    def _write_points(self, points: List[Point], chunk_size: int = 5000) -> int:
        """Write points synchronously in chunks.

        Returns the number of points successfully submitted to the write API.
        Raises the underlying error on failure (rollback is performed by caller).
        """
        if not points:
            return 0
        if not self.influxdb_connection:
            raise RuntimeError("InfluxDB connection is not initialized")

        written = 0
        write_api = self.influxdb_connection.write_api(write_options=SYNCHRONOUS)
        try:
            for i in range(0, len(points), chunk_size):
                chunk = points[i:i + chunk_size]
                write_api.write(bucket=self.bucket, org=self.org_id, record=chunk)
                written += len(chunk)
        except Exception as er:
            logging.error(ErrorMessages.ER00052.value.format(self.name))
            logging.error(er)
            raise
        return written
