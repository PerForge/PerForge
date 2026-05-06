# Copyright Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>
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
ImportService - validates and persists a project export payload.

Two-phase workflow
------------------
1. check_conflicts(data, target_project_id)
   Returns a list of human-readable conflict descriptions.
   No data is written.

2. execute_import(data, target_project_id)
   Upserts all entities in dependency order, remapping all internal
   numeric IDs so references stay consistent in the target database.

Import order (respects FK deps)
--------------------------------
1.  Secrets            (no deps)
2.  Global prompts     (no deps, project_id stays NULL)
3.  Project prompts    (no deps)
4.  NFRs               (no deps)
5.  Grafana            (token → secrets)
6.  InfluxDB           (token → secrets)
7.  AI Support         (token → secrets)
8.  Confluence         (token → secrets)
9.  Jira               (token → secrets)
10. Azure Wiki         (token → secrets)
11. SMTP Mail          (token → secrets)
12. Graphs             (prompt_id → prompts, grafana_id / dash_id → grafana)
13. Templates          (nfr, prompt IDs, graph IDs in data rows)
14. Template Groups    (prompt_id, template_id in data rows)
15. Settings           (upsert by category + key)
"""

import logging
import traceback
from typing import Optional

from sqlalchemy.orm import joinedload

from app.config import db
from app.backend.components.secrets.secrets_db                             import DBSecrets
from app.backend.components.prompts.prompts_db                             import DBPrompts
from app.backend.components.graphs.graphs_db                               import DBGraphs
from app.backend.components.nfrs.nfrs_db                                   import DBNFRs
from app.backend.components.templates.templates_db                         import DBTemplates, DBTemplateData
from app.backend.components.templates.template_groups_db                   import DBTemplateGroups, DBTemplateGroupData
from app.backend.components.settings.settings_db                           import DBProjectSettings
from app.backend.integrations.data_sources.influxdb_v2.influxdb_db         import DBInfluxdb
from app.backend.integrations.grafana.grafana_db                           import DBGrafana, DBGrafanaDashboards
from app.backend.integrations.ai_support.ai_support_db                     import DBAISupport
from app.backend.integrations.atlassian_confluence.atlassian_confluence_db import DBAtlassianConfluence
from app.backend.integrations.atlassian_jira.atlassian_jira_db             import DBAtlassianJira
from app.backend.integrations.azure_wiki.azure_wiki_db                     import DBAzureWiki
from app.backend.integrations.smtp_mail.smtp_mail_db                       import DBSMTPMail, DBSMTPMailRecipient


class ImportService:
    """Validates and persists a project export payload."""

    # ------------------------------------------------------------------
    # Phase 1 – conflict detection (read-only)
    # ------------------------------------------------------------------

    @classmethod
    def check_conflicts(cls, data: dict, target_project_id: int) -> list:
        """
        Dry-run: identify entities that would be overridden.

        Args:
            data: Parsed export JSON payload.
            target_project_id: ID of the project that will receive the data.

        Returns:
            List of dicts:  [{"type": "...", "name": "..."}, ...]
        """
        conflicts = []

        from sqlalchemy import or_
        conflicts += cls._conflicts_for(
            data.get("secrets", []),
            db.session.query(DBSecrets).filter(
                or_(DBSecrets.project_id == target_project_id, DBSecrets.project_id.is_(None))
            ).all(),
            "Secret",
            name_field="key"
        )
        conflicts += cls._conflicts_for(
            data.get("global_prompts", []),
            db.session.query(DBPrompts).filter(
                DBPrompts.type == "custom",
                DBPrompts.project_id.is_(None)
            ).all(),
            "Global Prompt"
        )
        conflicts += cls._conflicts_for(
            data.get("project_prompts", []),
            db.session.query(DBPrompts).filter(
                DBPrompts.type == "custom",
                DBPrompts.project_id == target_project_id
            ).all(),
            "Prompt"
        )
        conflicts += cls._conflicts_for(
            data.get("graphs", []),
            db.session.query(DBGraphs).filter(DBGraphs.project_id == target_project_id).all(),
            "Graph"
        )
        conflicts += cls._conflicts_for(
            data.get("nfrs", []),
            db.session.query(DBNFRs).filter(DBNFRs.project_id == target_project_id).all(),
            "NFR"
        )
        conflicts += cls._conflicts_for(
            data.get("templates", []),
            db.session.query(DBTemplates).filter(DBTemplates.project_id == target_project_id).all(),
            "Template"
        )
        conflicts += cls._conflicts_for(
            data.get("template_groups", []),
            db.session.query(DBTemplateGroups).filter(DBTemplateGroups.project_id == target_project_id).all(),
            "Template Group"
        )

        integrations = data.get("integrations", {})
        conflicts += cls._conflicts_for(
            integrations.get("influxdb", []),
            db.session.query(DBInfluxdb).filter(DBInfluxdb.project_id == target_project_id).all(),
            "InfluxDB"
        )
        conflicts += cls._conflicts_for(
            integrations.get("grafana", []),
            db.session.query(DBGrafana).filter(DBGrafana.project_id == target_project_id).all(),
            "Grafana"
        )
        conflicts += cls._conflicts_for(
            integrations.get("ai_support", []),
            db.session.query(DBAISupport).filter(DBAISupport.project_id == target_project_id).all(),
            "AI Support"
        )
        conflicts += cls._conflicts_for(
            integrations.get("atlassian_confluence", []),
            db.session.query(DBAtlassianConfluence).filter(DBAtlassianConfluence.project_id == target_project_id).all(),
            "Atlassian Confluence"
        )
        conflicts += cls._conflicts_for(
            integrations.get("atlassian_jira", []),
            db.session.query(DBAtlassianJira).filter(DBAtlassianJira.project_id == target_project_id).all(),
            "Atlassian Jira"
        )
        conflicts += cls._conflicts_for(
            integrations.get("azure_wiki", []),
            db.session.query(DBAzureWiki).filter(DBAzureWiki.project_id == target_project_id).all(),
            "Azure Wiki"
        )
        conflicts += cls._conflicts_for(
            integrations.get("smtp_mail", []),
            db.session.query(DBSMTPMail).filter(DBSMTPMail.project_id == target_project_id).all(),
            "SMTP Mail"
        )

        return conflicts

    @staticmethod
    def _conflicts_for(incoming: list, existing_records: list, entity_type: str, name_field: str = "name") -> list:
        """Return conflict entries for any incoming item whose identifier matches an existing record."""
        existing_names = {getattr(r, name_field) for r in existing_records}
        return [
            {"type": entity_type, "name": item[name_field]}
            for item in incoming
            if item.get(name_field) in existing_names
        ]

    # ------------------------------------------------------------------
    # Phase 2 – execute import (writes to DB)
    # ------------------------------------------------------------------

    @classmethod
    def execute_import(cls, data: dict, target_project_id: int) -> dict:
        """
        Persist all entities from the export payload into target_project_id.

        Existing entities with matching names are fully replaced.
        All internal IDs are remapped.

        Args:
            data: Parsed export JSON payload.
            target_project_id: ID of the destination project.

        Returns:
            Summary dict with counts per entity type.
        """
        summary = {}
        try:
            secret_id_map     = cls._import_secrets(data.get("secrets", []), target_project_id)
            summary["secrets"] = len(secret_id_map)

            global_prompt_map = cls._import_prompts(data.get("global_prompts", []), None)
            project_prompt_map = cls._import_prompts(data.get("project_prompts", []), target_project_id)
            prompt_id_map = {**global_prompt_map, **project_prompt_map}
            summary["prompts"] = len(prompt_id_map)

            nfr_id_map = cls._import_nfrs(data.get("nfrs", []), target_project_id)
            summary["nfrs"] = len(nfr_id_map)

            grafana_id_map, dashboard_id_map = cls._import_grafana(
                data.get("integrations", {}).get("grafana", []),
                target_project_id, secret_id_map
            )
            summary["grafana"] = len(grafana_id_map)

            cls._import_influxdb(
                data.get("integrations", {}).get("influxdb", []),
                target_project_id, secret_id_map
            )
            summary["influxdb"] = len(data.get("integrations", {}).get("influxdb", []))

            cls._import_ai_support(
                data.get("integrations", {}).get("ai_support", []),
                target_project_id, secret_id_map
            )
            cls._import_atlassian_confluence(
                data.get("integrations", {}).get("atlassian_confluence", []),
                target_project_id, secret_id_map
            )
            cls._import_atlassian_jira(
                data.get("integrations", {}).get("atlassian_jira", []),
                target_project_id, secret_id_map
            )
            cls._import_azure_wiki(
                data.get("integrations", {}).get("azure_wiki", []),
                target_project_id, secret_id_map
            )
            cls._import_smtp_mail(
                data.get("integrations", {}).get("smtp_mail", []),
                target_project_id, secret_id_map
            )

            graph_id_map = cls._import_graphs(
                data.get("graphs", []),
                target_project_id, prompt_id_map, grafana_id_map, dashboard_id_map
            )
            summary["graphs"] = len(graph_id_map)

            cls._import_templates(
                data.get("templates", []),
                target_project_id, nfr_id_map, prompt_id_map, graph_id_map
            )
            summary["templates"] = len(data.get("templates", []))

            cls._import_template_groups(
                data.get("template_groups", []),
                target_project_id, prompt_id_map
            )
            summary["template_groups"] = len(data.get("template_groups", []))

            cls._import_settings(data.get("settings", []), target_project_id)
            summary["settings"] = len(data.get("settings", []))

            db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(traceback.format_exc())
            raise

        return summary

    # ------------------------------------------------------------------
    # Entity-level import helpers
    # ------------------------------------------------------------------

    @classmethod
    def _import_secrets(cls, items: list, project_id: int) -> dict:
        """Upsert secrets; return {old_id → new_id} map."""
        id_map = {}
        for item in items:
            old_id = item.get("id")
            existing = db.session.query(DBSecrets).filter(
                DBSecrets.project_id == project_id,
                DBSecrets.key == item["key"]
            ).one_or_none()
            if existing:
                existing.value = item["value"]
                db.session.flush()
                id_map[old_id] = existing.id
            else:
                new_obj = DBSecrets(
                    key=item["key"],
                    value=item["value"],
                    project_id=project_id
                )
                db.session.add(new_obj)
                db.session.flush()
                id_map[old_id] = new_obj.id
        return id_map

    @classmethod
    def _import_prompts(cls, items: list, project_id: Optional[int]) -> dict:
        """Upsert custom prompts; return {old_id → new_id} map."""
        id_map = {}
        for item in items:
            old_id = item.get("id")
            query = db.session.query(DBPrompts).filter(
                DBPrompts.type == "custom",
                DBPrompts.name == item["name"]
            )
            if project_id is None:
                query = query.filter(DBPrompts.project_id.is_(None))
            else:
                query = query.filter(DBPrompts.project_id == project_id)
            existing = query.one_or_none()
            if existing:
                existing.place  = item.get("place", existing.place)
                existing.prompt = item.get("prompt", existing.prompt)
                db.session.flush()
                id_map[old_id] = existing.id
            else:
                new_obj = DBPrompts(
                    name=item["name"],
                    type="custom",
                    place=item.get("place", ""),
                    prompt=item.get("prompt", ""),
                    project_id=project_id
                )
                db.session.add(new_obj)
                db.session.flush()
                id_map[old_id] = new_obj.id
        return id_map

    @classmethod
    def _import_nfrs(cls, items: list, project_id: int) -> dict:
        """Upsert NFRs (including rows); return {old_id → new_id} map."""
        id_map = {}
        for item in items:
            old_id = item.get("id")
            existing = db.session.query(DBNFRs).filter(
                DBNFRs.project_id == project_id,
                DBNFRs.name == item["name"]
            ).options(joinedload(DBNFRs.rows)).one_or_none()
            if existing:
                existing.rows.clear()
                for row in item.get("rows", []):
                    existing.rows.append(cls._make_nfr_row(row))
                db.session.flush()
                id_map[old_id] = existing.id
            else:
                new_obj = DBNFRs(name=item["name"], project_id=project_id)
                for row in item.get("rows", []):
                    new_obj.rows.append(cls._make_nfr_row(row))
                db.session.add(new_obj)
                db.session.flush()
                id_map[old_id] = new_obj.id
        return id_map

    @staticmethod
    def _make_nfr_row(row: dict):
        from app.backend.components.nfrs.nfrs_db import DBNFRRows
        return DBNFRRows(
            regex=row.get("regex", False),
            scope=row.get("scope", ""),
            metric=row.get("metric", ""),
            operation=row.get("operation", ""),
            threshold=row.get("threshold", 0.0),
        )

    @classmethod
    def _import_grafana(cls, items: list, project_id: int, secret_id_map: dict):
        """Upsert Grafana integrations; return ({old_grafana_id → new_id}, {old_dash_id → new_id})."""
        grafana_id_map = {}
        dashboard_id_map = {}
        for item in items:
            old_id = item.get("id")
            token = secret_id_map.get(item.get("token"))
            existing = db.session.query(DBGrafana).filter(
                DBGrafana.project_id == project_id,
                DBGrafana.name == item["name"]
            ).options(joinedload(DBGrafana.dashboards)).one_or_none()

            old_dashboards = item.get("dashboards", [])

            if existing:
                # Track old dashboard → new position mapping
                old_dash_ids = [d.get("id") for d in old_dashboards]
                existing.server              = item.get("server", existing.server)
                existing.org_id             = item.get("org_id", existing.org_id)
                existing.token              = token
                existing.test_title         = item.get("test_title", existing.test_title)
                existing.baseline_test_title = item.get("baseline_test_title", existing.baseline_test_title)
                existing.is_default         = item.get("is_default", existing.is_default)
                existing.dashboards.clear()
                db.session.flush()

                for old_dash_id, dash in zip(old_dash_ids, old_dashboards):
                    new_dash = DBGrafanaDashboards(
                        content=dash.get("content", ""),
                        grafana_id=existing.id
                    )
                    db.session.add(new_dash)
                    db.session.flush()
                    if old_dash_id:
                        dashboard_id_map[old_dash_id] = new_dash.id

                grafana_id_map[old_id] = existing.id
            else:
                new_obj = DBGrafana(
                    project_id=project_id,
                    name=item["name"],
                    server=item.get("server", ""),
                    org_id=item.get("org_id", ""),
                    token=token,
                    test_title=item.get("test_title", ""),
                    baseline_test_title=item.get("baseline_test_title", ""),
                    is_default=item.get("is_default", False),
                )
                db.session.add(new_obj)
                db.session.flush()
                grafana_id_map[old_id] = new_obj.id

                for dash in old_dashboards:
                    old_dash_id = dash.get("id")
                    new_dash = DBGrafanaDashboards(
                        content=dash.get("content", ""),
                        grafana_id=new_obj.id
                    )
                    db.session.add(new_dash)
                    db.session.flush()
                    if old_dash_id:
                        dashboard_id_map[old_dash_id] = new_dash.id

        return grafana_id_map, dashboard_id_map

    @classmethod
    def _import_influxdb(cls, items: list, project_id: int, secret_id_map: dict):
        """Upsert InfluxDB integrations."""
        import json as _json
        for item in items:
            token = secret_id_map.get(item.get("token"))
            existing = db.session.query(DBInfluxdb).filter(
                DBInfluxdb.project_id == project_id,
                DBInfluxdb.name == item["name"]
            ).one_or_none()
            custom_vars = item.get("custom_vars")
            if isinstance(custom_vars, list):
                custom_vars = ",".join(str(v) for v in custom_vars)
            custom_filter_tags = item.get("custom_filter_tags")
            if isinstance(custom_filter_tags, list):
                custom_filter_tags = _json.dumps(custom_filter_tags)

            fields = dict(
                url=item.get("url", ""),
                org_id=item.get("org_id", ""),
                token=token,
                timeout=item.get("timeout", 60000),
                bucket=item.get("bucket", ""),
                listener=item.get("listener", ""),
                tmz=item.get("tmz", "UTC"),
                test_title_tag_name=item.get("test_title_tag_name", "testTitle"),
                regex=item.get("regex"),
                bucket_regex_bool=item.get("bucket_regex_bool", False),
                custom_vars=custom_vars,
                multi_node_tag=item.get("multi_node_tag"),
                custom_filter_tags=custom_filter_tags,
                start_time_offset_minutes=item.get("start_time_offset_minutes", 0),
                is_default=item.get("is_default", False),
            )
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
                db.session.flush()
            else:
                new_obj = DBInfluxdb(project_id=project_id, name=item["name"], **fields)
                db.session.add(new_obj)
                db.session.flush()

    @classmethod
    def _import_ai_support(cls, items: list, project_id: int, secret_id_map: dict):
        """Upsert AI Support integrations."""
        for item in items:
            token = secret_id_map.get(item.get("token"))
            existing = db.session.query(DBAISupport).filter(
                DBAISupport.project_id == project_id,
                DBAISupport.name == item["name"]
            ).one_or_none()
            fields = dict(
                ai_provider=item.get("ai_provider", ""),
                azure_url=item.get("azure_url"),
                base_url=item.get("base_url"),
                api_version=item.get("api_version"),
                ai_text_model=item.get("ai_text_model", ""),
                ai_image_model=item.get("ai_image_model", ""),
                token=token,
                temperature=item.get("temperature", 0.0),
                conversation_memory=item.get("conversation_memory", False),
                is_default=item.get("is_default", False),
            )
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
                db.session.flush()
            else:
                new_obj = DBAISupport(project_id=project_id, name=item["name"], **fields)
                db.session.add(new_obj)
                db.session.flush()

    @classmethod
    def _import_atlassian_confluence(cls, items: list, project_id: int, secret_id_map: dict):
        """Upsert Atlassian Confluence integrations."""
        for item in items:
            token = secret_id_map.get(item.get("token"))
            existing = db.session.query(DBAtlassianConfluence).filter(
                DBAtlassianConfluence.project_id == project_id,
                DBAtlassianConfluence.name == item["name"]
            ).one_or_none()
            fields = dict(
                email=item.get("email", ""),
                token=token,
                token_type=item.get("token_type", ""),
                org_url=item.get("org_url", ""),
                space_key=item.get("space_key", ""),
                parent_id=item.get("parent_id", ""),
                is_default=item.get("is_default", False),
            )
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
                db.session.flush()
            else:
                new_obj = DBAtlassianConfluence(project_id=project_id, name=item["name"], **fields)
                db.session.add(new_obj)
                db.session.flush()

    @classmethod
    def _import_atlassian_jira(cls, items: list, project_id: int, secret_id_map: dict):
        """Upsert Atlassian Jira integrations."""
        for item in items:
            token = secret_id_map.get(item.get("token"))
            existing = db.session.query(DBAtlassianJira).filter(
                DBAtlassianJira.project_id == project_id,
                DBAtlassianJira.name == item["name"]
            ).one_or_none()
            fields = dict(
                email=item.get("email", ""),
                token=token,
                token_type=item.get("token_type", ""),
                org_url=item.get("org_url", ""),
                jira_project_key=item.get("jira_project_key", ""),
                epic_field=item.get("epic_field"),
                epic_name=item.get("epic_name"),
                is_default=item.get("is_default", False),
            )
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
                db.session.flush()
            else:
                new_obj = DBAtlassianJira(project_id=project_id, name=item["name"], **fields)
                db.session.add(new_obj)
                db.session.flush()

    @classmethod
    def _import_azure_wiki(cls, items: list, project_id: int, secret_id_map: dict):
        """Upsert Azure Wiki integrations."""
        for item in items:
            token = secret_id_map.get(item.get("token"))
            existing = db.session.query(DBAzureWiki).filter(
                DBAzureWiki.project_id == project_id,
                DBAzureWiki.name == item["name"]
            ).one_or_none()
            fields = dict(
                token=token,
                org_url=item.get("org_url", ""),
                azure_project_id=item.get("azure_project_id", ""),
                identifier=item.get("identifier", ""),
                path_to_report=item.get("path_to_report", ""),
                is_default=item.get("is_default", False),
            )
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
                db.session.flush()
            else:
                new_obj = DBAzureWiki(project_id=project_id, name=item["name"], **fields)
                db.session.add(new_obj)
                db.session.flush()

    @classmethod
    def _import_smtp_mail(cls, items: list, project_id: int, secret_id_map: dict):
        """Upsert SMTP Mail integrations (including recipients)."""
        for item in items:
            token = secret_id_map.get(item.get("token"))
            existing = db.session.query(DBSMTPMail).filter(
                DBSMTPMail.project_id == project_id,
                DBSMTPMail.name == item["name"]
            ).options(joinedload(DBSMTPMail.recipients)).one_or_none()
            fields = dict(
                server=item.get("server", ""),
                port=item.get("port", 587),
                use_ssl=item.get("use_ssl", False),
                use_tls=item.get("use_tls", False),
                username=item.get("username", ""),
                token=token,
                is_default=item.get("is_default", False),
            )
            recipients_data = item.get("recipients", [])
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
                existing.recipients.clear()
                for rec in recipients_data:
                    existing.recipients.append(DBSMTPMailRecipient(email=rec.get("email", "")))
                db.session.flush()
            else:
                new_obj = DBSMTPMail(project_id=project_id, name=item["name"], **fields)
                for rec in recipients_data:
                    new_obj.recipients.append(DBSMTPMailRecipient(email=rec.get("email", "")))
                db.session.add(new_obj)
                db.session.flush()

    @classmethod
    def _import_graphs(
        cls, items: list, project_id: int,
        prompt_id_map: dict, grafana_id_map: dict, dashboard_id_map: dict
    ) -> dict:
        """Upsert custom graphs; return {old_id → new_id} map."""
        id_map = {}
        for item in items:
            old_id = item.get("id")
            prompt_id   = prompt_id_map.get(item.get("prompt_id"))
            grafana_id  = grafana_id_map.get(item.get("grafana_id"))
            dash_id     = dashboard_id_map.get(item.get("dash_id"))
            existing = db.session.query(DBGraphs).filter(
                DBGraphs.project_id == project_id,
                DBGraphs.name == item["name"]
            ).one_or_none()
            fields = dict(
                type=item.get("type", "custom"),
                grafana_id=grafana_id,
                dash_id=dash_id,
                view_panel=item.get("view_panel"),
                width=item.get("width", 1000),
                height=item.get("height", 500),
                custom_vars=item.get("custom_vars"),
                prompt_id=prompt_id,
            )
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
                db.session.flush()
                id_map[old_id] = existing.id
            else:
                new_obj = DBGraphs(project_id=project_id, name=item["name"], **fields)
                db.session.add(new_obj)
                db.session.flush()
                id_map[old_id] = new_obj.id
        return id_map

    @classmethod
    def _import_templates(
        cls, items: list, project_id: int,
        nfr_id_map: dict, prompt_id_map: dict, graph_id_map: dict
    ):
        """Upsert templates (including template_data rows)."""
        for item in items:
            nfr_id               = nfr_id_map.get(item.get("nfr"))
            template_prompt_id   = prompt_id_map.get(item.get("template_prompt_id"))
            aggregated_prompt_id = prompt_id_map.get(item.get("aggregated_prompt_id"))
            system_prompt_id     = prompt_id_map.get(item.get("system_prompt_id"))

            existing = db.session.query(DBTemplates).filter(
                DBTemplates.project_id == project_id,
                DBTemplates.name == item["name"]
            ).options(joinedload(DBTemplates.data)).one_or_none()

            data_rows = []
            for row in item.get("data", []):
                graph_id = graph_id_map.get(row.get("graph_id"))
                data_rows.append(DBTemplateData(
                    type=row.get("type", ""),
                    content=row.get("content"),
                    graph_id=graph_id,
                    ai_graph_switch=row.get("ai_graph_switch", False),
                    ai_to_graphs_switch=row.get("ai_to_graphs_switch", False),
                ))

            fields = dict(
                title=item.get("title", ""),
                nfr=nfr_id,
                ai_switch=item.get("ai_switch", False),
                ai_aggregated_data_switch=item.get("ai_aggregated_data_switch", False),
                nfrs_switch=item.get("nfrs_switch", False),
                ml_switch=item.get("ml_switch", False),
                template_prompt_id=template_prompt_id,
                aggregated_prompt_id=aggregated_prompt_id,
                system_prompt_id=system_prompt_id,
            )
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
                existing.data.clear()
                for row_obj in data_rows:
                    existing.data.append(row_obj)
                db.session.flush()
            else:
                new_obj = DBTemplates(project_id=project_id, name=item["name"], **fields)
                for row_obj in data_rows:
                    new_obj.data.append(row_obj)
                db.session.add(new_obj)
                db.session.flush()

    @classmethod
    def _import_template_groups(
        cls, items: list, project_id: int, prompt_id_map: dict
    ):
        """Upsert template groups (including group_data rows).

        Note: template_id references in group data are not remapped because
        template groups may reference templates by their DB ID which exists
        in the current project scope after templates were imported.
        We build a name→new_id map for templates in this project first.
        """
        # Build name → new template id map for templates in this project
        template_name_to_id = {
            t.name: t.id
            for t in db.session.query(DBTemplates).filter(
                DBTemplates.project_id == project_id
            ).all()
        }

        for item in items:
            prompt_id = prompt_id_map.get(item.get("prompt_id"))
            existing = db.session.query(DBTemplateGroups).filter(
                DBTemplateGroups.project_id == project_id,
                DBTemplateGroups.name == item["name"]
            ).options(joinedload(DBTemplateGroups.data)).one_or_none()

            data_rows = []
            for row in item.get("data", []):
                # Try to resolve template_id via the name stored in content field
                # (export stores template name as content when type == 'template')
                template_id = None
                if row.get("type") == "template" and row.get("content"):
                    template_id = template_name_to_id.get(row["content"])
                data_rows.append(DBTemplateGroupData(
                    type=row.get("type", ""),
                    content=row.get("content"),
                    template_id=template_id,
                ))

            fields = dict(
                title=item.get("title", ""),
                ai_summary=item.get("ai_summary", False),
                prompt_id=prompt_id,
            )
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
                existing.data.clear()
                for row_obj in data_rows:
                    existing.data.append(row_obj)
                db.session.flush()
            else:
                new_obj = DBTemplateGroups(project_id=project_id, name=item["name"], **fields)
                for row_obj in data_rows:
                    new_obj.data.append(row_obj)
                db.session.add(new_obj)
                db.session.flush()

    @classmethod
    def _import_settings(cls, items: list, project_id: int):
        """Upsert project settings (by category + key)."""
        for item in items:
            existing = db.session.query(DBProjectSettings).filter_by(
                project_id=project_id,
                category=item.get("category"),
                key=item.get("key")
            ).one_or_none()

            import json as _json
            value_type = item.get("value_type", "string")
            raw_value = item.get("value")
            if value_type in ("list", "dict"):
                serialized = _json.dumps(raw_value)
            else:
                serialized = str(raw_value) if raw_value is not None else ""

            if existing:
                existing.value       = serialized
                existing.value_type  = value_type
                existing.description = item.get("description", existing.description)
                db.session.flush()
            else:
                new_obj = DBProjectSettings(
                    project_id=project_id,
                    category=item.get("category", ""),
                    key=item.get("key", ""),
                    value=serialized,
                    value_type=value_type,
                    description=item.get("description"),
                )
                db.session.add(new_obj)
                db.session.flush()
