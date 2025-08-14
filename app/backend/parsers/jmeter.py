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

from __future__ import annotations

import io
import pandas as pd


def parse_uploaded_results(file_storage) -> pd.DataFrame:
    """Parse uploaded CSV or JTL (CSV/XML) into a normalized DataFrame."""
    filename = getattr(file_storage, 'filename', '') or ''
    name_lower = filename.lower()
    content = file_storage.read()
    file_storage.seek(0)

    def to_df_csv(bytes_buf: bytes) -> pd.DataFrame:
        try:
            buf = io.BytesIO(bytes_buf)
            df_local = pd.read_csv(buf)
            # Normalize headers
            cols = {c.strip(): c.strip() for c in df_local.columns}
            df_local.rename(columns=cols, inplace=True)

            # Detect timestamp column
            ts_col = None
            for cand in ["timeStamp", "timestamp", "ts", "_time"]:
                if cand in df_local.columns:
                    ts_col = cand
                    break
            if ts_col is None:
                return pd.DataFrame()

            # Detect label and success
            label_col = "label" if "label" in df_local.columns else ("lb" if "lb" in df_local.columns else None)
            success_col = "success" if "success" in df_local.columns else ("s" if "s" in df_local.columns else None)
            elapsed_col = "elapsed" if "elapsed" in df_local.columns else ("t" if "t" in df_local.columns else None)

            if label_col is None or success_col is None or elapsed_col is None:
                return pd.DataFrame()

            out = pd.DataFrame({
                "timestamp": pd.to_datetime(pd.to_numeric(df_local[ts_col], errors="coerce"), unit="ms", utc=True, errors="coerce"),
                "label": df_local[label_col].astype(str),
                "elapsed": pd.to_numeric(df_local[elapsed_col], errors="coerce"),
                "success": df_local[success_col].astype(str).str.lower().isin(["true", "1", "t", "y", "yes"]),
                "bytes": pd.to_numeric(df_local.get("bytes", df_local.get("by", 0)), errors="coerce").fillna(0).astype(int),
                "sentBytes": pd.to_numeric(df_local.get("sentBytes", df_local.get("sby", 0)), errors="coerce").fillna(0).astype(int),
                "responseCode": df_local.get("responseCode", df_local.get("rc", "")).astype(str),
                "responseMessage": df_local.get("responseMessage", df_local.get("rm", "")).astype(str),
                "allThreads": pd.to_numeric(df_local.get("allThreads", df_local.get("na", df_local.get("ng", 0))), errors="coerce").fillna(0).astype(int),
            })
            out = out.dropna(subset=["timestamp", "elapsed"]).reset_index(drop=True)
            return out
        except Exception:
            return pd.DataFrame()

    def to_df_xml(bytes_buf: bytes) -> pd.DataFrame:
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(bytes_buf)
            rows = []
            for tag in ["httpSample", "sample"]:
                for el in root.iter(tag):
                    try:
                        ts = int(el.attrib.get("ts"))
                        t = float(el.attrib.get("t"))
                        lb = el.attrib.get("lb", "")
                        s = el.attrib.get("s", "true").lower() in ("true", "1")
                        rc = el.attrib.get("rc", "")
                        rm = el.attrib.get("rm", "")
                        by = int(el.attrib.get("by", 0))
                        sby = int(el.attrib.get("sby", 0))
                        na = int(el.attrib.get("na", el.attrib.get("ng", 0)))
                        rows.append({
                            "timestamp": pd.to_datetime(ts, unit="ms", utc=True),
                            "label": lb,
                            "elapsed": t,
                            "success": s,
                            "bytes": by,
                            "sentBytes": sby,
                            "responseCode": rc,
                            "responseMessage": rm,
                            "allThreads": na,
                        })
                    except Exception:
                        continue
            return pd.DataFrame(rows)
        except Exception:
            return pd.DataFrame()

    # Try CSV first (most common for JTL)
    df = to_df_csv(content)
    if df.empty and name_lower.endswith(".jtl"):
        # Try XML fallback
        df = to_df_xml(content)
    return df if not df.empty else pd.DataFrame()
