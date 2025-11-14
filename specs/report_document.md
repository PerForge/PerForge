# ReportDocument Specification (v1.0)

## Table of Contents
- [Overview](#overview)
- [Versioning](#versioning)
- [Core Object: ReportDocument](#core-object-reportdocument)
- [ReportTest](#reporttest)
- [Dataset](#dataset)
- [Chart](#chart)
- [Section (Presentation-lite)](#section-presentation-lite)
- [Error](#error)
- [IDs & References](#ids--references)
- [Validation](#validation)
- [Architecture: Classes & Responsibilities](#architecture-classes--responsibilities)
  - [ReportingBase (existing)](#reportingbase-existing)
  - [ReportDocumentBuilder (new)](#reportdocumentbuilder-new)
  - [ReportDocument Models (lightweight)](#reportdocument-models-lightweight)
- [Recommended Module Layout](#recommended-module-layout)
- [Builder API (v1)](#builder-api-v1)
- [Domain-to-Document Conversion Helpers](#domain-to-document-conversion-helpers)
- [Integration Flow in ReportingBase](#integration-flow-in-reportingbase)
- [ID and Reference Rules](#id-and-reference-rules)
- [Rendering Guidelines (short)](#rendering-guidelines-short)
- [Minimal Example](#minimal-example)
- [Decisions](#decisions)
- [ML: Per-Transaction Anomaly Detection (Approach & Required Changes)](#ml-per-transaction-anomaly-detection-approach--required-changes)
  - [Objectives](#objectives)
  - [Data requirements (normalized schema)](#data-requirements-normalized-schema)
  - [Algorithm (per-transaction)](#algorithm-per-transaction)
  - [Output (ReportDocument integration)](#output-reportdocument-integration)
  - [Engine changes (non-breaking, additive)](#engine-changes-non-breaking-additive)
  - [Integration points & responsibilities](#integration-points--responsibilities)
  - [Scoring and severity](#scoring-and-severity)
  - [Performance considerations](#performance-considerations)

## Overview
- **Purpose**: Canonical, versioned JSON representation of a generated report used by all integrations (PDF, Email, Confluence, Jira, etc.).
- **Scope**: Data, charts, insights (NFR/ML/AI), light presentation structure (sections/blocks), assets, and provenance.
- **Compatibility**: Renderers consume this document and map it to their mediums; data collection/analysis code builds it.

## Versioning
- **schemaVersion**: Semantic version for the document schema (e.g., "1.0").
- **generatorVersion**: Application version that produced the document.
- Backward compatibility is maintained across minor versions; breaking changes bump major.

## Core Object: ReportDocument
Fields:
- `schemaVersion` (string, required)
- `generatorVersion` (string)
- `reportId` (string, required)
- `project` (object)
  - `id` (string|number)
- `createdAt` (string, ISO-8601, required)
- `timeWindow` (object)
  - `start` (string, ISO-8601)
  - `end` (string, ISO-8601)
- `parameters` (object): user/template parameters, switches, theme
  - `theme` (string: "dark"|"light")
  - `ai` (boolean)
  - `ml` (boolean)
  - `nfrs` (boolean)
- `provenance` (object): data sources, environment
  - `sources` (array of { provider, details })
- `tests` (array of ReportTest)
- `datasets` (array of Dataset)
- `charts` (array of Chart)
- `sections` (array of Section)
- `errors` (array of Error)

## ReportTest
- `id` (string, required)
- `title` (string, required)
- `baselineTitle` (string, optional)
- `summary` (object, optional)

## Dataset
- `id` (string, required)
- `type` (string, enum: `table` | `timeseries` | `events`, required)
- `name` (string)
- `unit` (string, optional): default unit for values
- `dimensions` (array of strings, optional)
- Table form:
  - `columns` (array of { name, type, unit? })
  - `rows` (array of arrays)
- Timeseries form:
  - `series` (array of { label?, points: [{ t: ISO-8601, value: number, meta?: object }] })
- Events form:
  - `events` (array of { t: ISO-8601, type: string, severity?: string, message?: string, meta?: object })

## Chart
- `id` (string, required)
- `kind` (string, enum: `line` | `bar` | `scatter` | `heatmap`, required)
- `dataRef` (string, dataset id)
- `title` (string)
- `encodings` (object, optional): x, y, color, facet
- `theme` (string, optional)
- `rendered` (array of RenderedAsset)
  - RenderedAsset (v1 inline-only): { role: `figure`|`thumbnail`|`email`, storage: "inline", dataUri: string, width?: number, height?: number, mime?: string }

## Section (Presentation-lite)
- `id` (string, required)
- `title` (string)
- `blocks` (array of Block, required)
- Block types:
  - `Heading` { type: "Heading", text: string, level?: 1..4 }
  - `Paragraph` { type: "Paragraph", text: string }
  - `Callout` { type: "Callout", text: string, tone?: `info`|`warning`|`success`|`danger` }
  - `TableRef` { type: "TableRef", datasetId: string }
  - `ChartRef` { type: "ChartRef", chartId: string }
  - `List` { type: "List", items: string[] }

## Error
- `code` (string)
- `message` (string)
- `context` (object)

## IDs & References
- All cross-references use stable `id` fields. Renderers must validate existence and ignore dangling refs.

## Validation
- JSON Schema at `specs/report_document.schema.json` validates shape and enum values.

## Architecture: Classes & Responsibilities

### ReportingBase (existing)
- Orchestrates the end-to-end report generation.
- Reads template configuration and determines section/block order.
- Collects data (via DataProvider/TestData) and prepares metrics needed for charts.
- Renders charts (e.g., Plotly) and obtains in-memory PNG bytes.
- Delegates JSON assembly to the builder and hands the final document to integrations (PDF/Email/etc.).

### ReportDocumentBuilder (new)
- Responsibility: build the canonical ReportDocument JSON in-memory.
- Adds tests, datasets, charts (inline base64), and sections in the requested order.
- Ensures id uniqueness and that references (TableRef/ChartRef) point to existing items.
- Produces a dict that conforms to `report_document.schema.json` via `build()`.

### ReportDocument Models (lightweight)
- Optional Python dataclasses/TypedDicts to describe shapes (Dataset, Chart, Section, Blocks, Test).
- Keep enums/constants (dataset types, chart kinds, block types) colocated for clarity.

## Recommended Module Layout

```
app/backend/integrations/report_document/
  models.py     # dataclasses/TypedDicts for Document, Test, Dataset, Chart, Section, Blocks
  builder.py    # ReportDocumentBuilder with add_* methods and build()
  constants.py  # optional enums/ids
  validate.py   # optional schema validation helpers
```

## Builder API (v1)

```python
class ReportDocumentBuilder:
    def __init__(self, *, schema_version: str, generator_version: str, report_id: str,
                 project_id, created_at: str, parameters: dict | None = None): ...

    # Tests
    def add_test(self, *, id: str, title: str, baseline_title: str | None = None,
                 summary: dict | None = None) -> None: ...

    # Datasets
    def add_dataset_table(self, *, id: str, name: str | None, columns: list[dict],
                          rows: list[list], unit: str | None = None,
                          dimensions: list[str] | None = None) -> None: ...

    def add_dataset_timeseries(self, *, id: str, name: str | None,
                               series: list[dict], unit: str | None = None,
                               dimensions: list[str] | None = None) -> None: ...

    def add_dataset_events(self, *, id: str, name: str | None,
                           events: list[dict]) -> None: ...

    # Charts (inline-only images in v1)
    def add_chart_from_bytes(self, *, id: str, kind: str, data_ref: str,
                             title: str | None, bytes: bytes,
                             mime: str = "image/png", width: int | None = None,
                             height: int | None = None, role: str = "figure") -> None: ...

    # Sections
    def add_section(self, *, id: str, title: str | None, blocks: list[dict]) -> None: ...

    # Finalize
    def build(self) -> dict: ...
```

Notes:
- `add_chart_from_bytes` converts bytes → base64 data URL and stores it in `rendered[].dataUri` with `storage: "inline"`.
- The builder only assembles data; it does not read from data sources nor render images.

## Domain-to-Document Conversion Helpers

These helpers live on the domain side (MetricsTable/BaseTestData) and return Python structures that match the ReportDocument dataset shape. They do not serialize to JSON; the builder or caller will.

```python
class MetricsTable:
    def to_table_dataset(self) -> tuple[list[dict], list[list]]:
        """
        Convert this MetricsTable into a table dataset payload.

        Returns:
            columns: list of column descriptors following the spec, e.g.
                [
                  {"name": "transaction", "type": "string"},
                  {"name": "avg_rt_ms", "type": "number", "unit": "ms"},
                  ...
                ]
            rows: list of row arrays, each starting with the scope (e.g., transaction/page),
                  followed by numeric values aligned with columns order.
        Notes:
            - The first column MUST be the scope (e.g., transaction/page).
            - Only numeric metrics are emitted as number-typed columns; non-numeric fields are ignored.
            - Units are optional and included when available.
        """
        ...


class BaseTestData:
    def to_report_datasets(self) -> list[dict]:
        """
        Convert all loaded MetricsTable instances into ReportDocument dataset dicts.

        Returns:
            A list of dataset dicts, each shaped like:
                {
                  "id": str,                 # e.g., f"tbl_{self.test_type}_{table_name}"
                  "type": "table",          # v1 produces table datasets from MetricsTable
                  "name": str | None,
                  "columns": list[dict],     # from MetricsTable.to_table_dataset()[0]
                  "rows": list[list],        # from MetricsTable.to_table_dataset()[1]
                  "unit": str | None,        # optional default unit
                  "dimensions": list[str] | None
                }
        Notes:
            - This method should iterate get_all_tables() (or its cache) and call MetricsTable.to_table_dataset().
            - ID strategy should guarantee uniqueness (e.g., include test id/name and table_name).
            - This method returns Python dicts; serialization happens later.
        """
        ...
```

## Integration Flow in ReportingBase

1. Initialize builder at the start of generation with metadata (schemaVersion, generatorVersion, reportId, project.id, createdAt, parameters).
2. For each test: collect data, then `add_test(...)` and add any datasets produced by TestData objects.
3. When rendering charts: call rendering to get PNG bytes, then `add_chart_from_bytes(...)` (inline-only).
4. Convert template-defined order to sections/blocks and `add_section(...)` accordingly.
5. Call `build()` to obtain the final ReportDocument dict and pass it to the integration renderer.

## ID and Reference Rules

- All ids must be unique within their collections (`tests`, `datasets`, `charts`, `sections`).
- Blocks use ids to reference data: `TableRef.datasetId` and `ChartRef.chartId` must refer to existing items.
- Tests are descriptive (`id`, `title`, `baselineTitle`) and do not reference datasets/charts directly in v1.
- The builder SHOULD validate references and raise a clear error if unresolved.

## Rendering Guidelines (short)
- PDF: map Sections/Blocks; embed images from `rendered[].dataUri`.
- Email: use `rendered[].dataUri` directly in `<img>` tags.
- Confluence/Jira: for v1, use `rendered[].dataUri`; future versions may upload assets and reference URLs.

## Minimal Example
```json
{
  "schemaVersion": "1.0",
  "generatorVersion": "2.1.X",
  "reportId": "rep_123",
  "project": { "id": 42 },
  "createdAt": "2025-11-06T09:55:00Z",
  "parameters": { "theme": "dark", "ai": true, "ml": true, "nfrs": true },
  "tests": [
    { "id": "t1", "title": "LoadTest A", "baselineTitle": "LoadTest A-1" }
  ],
  "datasets": [
    {
      "id": "tbl_agg_1",
      "type": "table",
      "name": "Aggregated Transactions",
      "columns": [
        { "name": "transaction", "type": "string" },
        { "name": "avg_rt_ms", "type": "number", "unit": "ms" },
        { "name": "p90_rt_ms", "type": "number", "unit": "ms" },
        { "name": "error_rate_pct", "type": "number", "unit": "%" }
      ],
      "rows": [
        ["checkout", 532.1, 880.5, 0.25],
        ["search", 210.8, 390.2, 0.0]
      ],

    }
  ],
  "charts": [
    {
      "id": "ch_rt_1",
      "kind": "line",
      "dataRef": "tbl_agg_1",
      "title": "Response Time by Transaction",
      "rendered": [{ "role": "figure", "storage": "inline", "dataUri": "data:image/png;base64,....", "width": 1200, "height": 600, "mime": "image/png" }]
    }
  ],
  "sections": [
    {
      "id": "sec_overview",
      "title": "Overview",
      "blocks": [
        { "type": "Heading", "text": "Executive Summary", "level": 2 },
        { "type": "Paragraph", "text": "Performance is stable with minor anomalies." },
        { "type": "ChartRef", "chartId": "ch_rt_1" },
        { "type": "TableRef", "datasetId": "tbl_agg_1" },

      ]
    }
  ]
}
```

## Decisions
- **Template migration**: Move renderers directly to Sections/Blocks and populate concrete values in blocks. No dual-writing of `${...}` placeholders; we move values, not parameters.
- **API exposure**: Do not expose the ReportDocument via API in v1. The document remains in-memory and is passed directly to integrations. Storage decisions are deferred.
