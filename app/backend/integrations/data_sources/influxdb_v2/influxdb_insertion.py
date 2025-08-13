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
InfluxDB V2 insertion module.

This module encapsulates InfluxDB V2 write logic for uploading aggregated JMeter
results and lightweight events used for test discovery. It mirrors configuration
handling from `influxdb_extraction.py` but focuses on point construction and
writes.
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
    """
    InfluxDB V2 insertion implementation, encapsulating configuration, client lifecycle,
    point building, and synchronous batched writes.
    """

    def __init__(self, project: int, id: int | None = None):
        super().__init__(project)
        self.id: int | None = None
        self.name: str | None = None
        self.url: str | None = None
        self.org_id: str | None = None
        self.token: str | None = None
        self.timeout: int | None = None
        self.bucket: str | None = None
        self.listener: str | None = None
        self.test_title_tag_name: str | None = None
        self.tmz: str | None = None

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
        """
        Build and write all points derived from a normalized JMeter samples DataFrame.

        Expected DataFrame columns (normalized):
        - timestamp (datetime64[ns, UTC])
        - label (str)
        - elapsed (float)
        - success (bool)
        - bytes (int)
        - sentBytes (int)
        - responseCode (str)
        - responseMessage (str)
        - allThreads (int)

        Returns: { "points_written": int }
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

        # Ensure required columns exist (accept either a 'timestamp' column or a proper DatetimeIndex)
        if not isinstance(df.index, pd.DatetimeIndex) or df.index.name != "timestamp":
            if "timestamp" not in df.columns:
                raise ValueError("DataFrame must have a 'timestamp' column")
        for col in ["label", "elapsed", "success"]:
            if col not in getattr(df, "columns", []):
                raise ValueError(f"DataFrame must have a '{col}' column")

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

        # statut tag derived from success
        df["statut"] = np.where(df["success"].astype(bool), "ok", "ko")

        points: List[Point] = []
        test_title_tag = self.test_title_tag_name or "testTitle"
        # Time bounds for this upload (used for rollback and events). Influx delete stop is exclusive.
        start_dt = df.index.min().to_pydatetime()
        stop_dt = df.index.max().to_pydatetime() + timedelta(seconds=1)

        # Per-transaction aggregates for statut all and ko
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
                p.tag("application", "perforge")
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

        # Response code counts per transaction (failures only to match JMeter)
        if "responseCode" in df.columns:
            failed = df[df["success"] == False] if "success" in df.columns else df
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
                    p.tag("application", "perforge")
                    p.tag("transaction", str(row["label"]))
                    # Normalize responseCode to match backend listener (integers as strings, empty -> '0')
                    rc_raw = row.get("responseCode", "")
                    rc_str = "0"
                    if pd.notna(rc_raw):
                        rc_s = str(rc_raw).strip()
                        if rc_s.lower() not in ("", "nan", "none", "null"):
                            try:
                                rc_str = str(int(float(rc_s)))
                            except Exception:
                                rc_str = rc_s
                    # Clean responseMessage (avoid literal 'nan')
                    rm_raw = row.get("responseMessage", "")
                    rm_str = "" if (pd.isna(rm_raw) or str(rm_raw).strip().lower() in ("nan", "none", "null")) else str(rm_raw)
                    p.tag("responseCode", rc_str)
                    p.tag("responseMessage", rm_str)
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
                    p.tag("application", "perforge")
                    p.tag("transaction", "all")
                    # Normalize responseCode as above
                    rc_raw = row.get("responseCode", "")
                    rc_str = "0"
                    if pd.notna(rc_raw):
                        rc_s = str(rc_raw).strip()
                        if rc_s.lower() not in ("", "nan", "none", "null"):
                            try:
                                rc_str = str(int(float(rc_s)))
                            except Exception:
                                rc_str = rc_s
                    rm_raw = row.get("responseMessage", "")
                    rm_str = "" if (pd.isna(rm_raw) or str(rm_raw).strip().lower() in ("nan", "none", "null")) else str(rm_raw)
                    p.tag("responseCode", rc_str)
                    p.tag("responseMessage", rm_str)
                    p.field("count", float(row["count"]))
                    points.append(p)

        # Active threads series: emit one "jmeter" point per window with transaction="internal"
        if "allThreads" in df.columns and not df["allThreads"].isna().all():
            at_series = df["allThreads"].astype(float)
            at_max = at_series.resample(aggregation_window).max().fillna(0).astype(int)
            at_mean = at_series.resample(aggregation_window).mean().fillna(0.0).astype(float)
            at_min = at_series.resample(aggregation_window).min().fillna(0).astype(int)
            # startedT / endedT approximated from positive/negative diffs within the window
            def _started(s: pd.Series) -> int:
                d = s.diff().fillna(0)
                return int(np.maximum(d, 0).sum())
            def _ended(s: pd.Series) -> int:
                d = s.diff().fillna(0)
                return int(np.maximum(-d, 0).sum())
            startedT = at_series.groupby(pd.Grouper(freq=aggregation_window)).apply(_started).reindex(at_max.index, fill_value=0)
            endedT = at_series.groupby(pd.Grouper(freq=aggregation_window)).apply(_ended).reindex(at_max.index, fill_value=0)
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
            p.tag("application", "perforge")
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
                    ep.tag("application", "perforge")
                    # keep compatibility and add BL-like fields
                    ep.field("text", str(test_title))
                    points.append(ep)
                    # JMeter-style annotation event
                    jp = Point("events").time(ts.to_pydatetime())
                    jp.tag(test_title_tag, test_title)
                    jp.tag("application", "perforge")
                    jp.tag("title", "ApacheJMeter")
                    jp.field("text", f"{test_title} {'started' if typ == 'start' else 'ended'}")
                    points.append(jp)
            except Exception:
                # Non-fatal; continue
                pass

        try:
            written = self._write_points(points)
        except Exception as er:
            # Best-effort rollback: delete points for this upload by predicate and time range
            try:
                self._rollback_delete(test_title_tag, test_title, start_dt, stop_dt)
            except Exception:
                # Non-fatal; original exception will be raised
                pass
            raise
        return {"points_written": written}

    # -------------------- Internals --------------------
    def _rollback_delete(self, test_title_tag: str, test_title: str, start_dt, stop_dt) -> None:
        """Best-effort delete for points belonging to the current upload.

        Deletes from measurements 'jmeter' and 'events' where application="perforge"
        and test title tag matches. Stop is exclusive.
        """
        if not self.influxdb_connection:
            return
        try:
            delete_api = self.influxdb_connection.delete_api()
            predicates = [
                f'_measurement="jmeter" AND "application"="perforge" AND "{test_title_tag}"="{test_title}"',
                f'_measurement="events" AND "application"="perforge" AND "{test_title_tag}"="{test_title}"',
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
