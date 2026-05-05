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
ExportService - collects all project configuration into a serialisable dict.

Exported entities
-----------------
Project-scoped
  secrets, custom prompts, graphs (type=custom), NFRs,
  templates (+template_data), template_groups (+template_group_data),
  project_settings, integrations (influxdb, grafana+dashboards,
  ai_support, atlassian_confluence, atlassian_jira, azure_wiki, smtp_mail)

Global (project_id IS NULL)
  custom prompts with no project assignment

Excluded (system-managed, loaded from YAML on startup)
  default prompts (type='default'), default graphs (type='default')
"""

import logging
import traceback
from datetime import datetime, timezone

from app.backend.components.secrets.secrets_db                             import DBSecrets
from app.backend.components.prompts.prompts_db                             import DBPrompts
from app.backend.components.graphs.graphs_db                               import DBGraphs
from app.backend.components.nfrs.nfrs_db                                   import DBNFRs
from app.backend.components.templates.templates_db                         import DBTemplates
from app.backend.components.templates.template_groups_db                   import DBTemplateGroups
from app.backend.components.settings.settings_db                           import DBProjectSettings
from app.backend.integrations.data_sources.influxdb_v2.influxdb_db         import DBInfluxdb
from app.backend.integrations.grafana.grafana_db                           import DBGrafana
from app.backend.integrations.ai_support.ai_support_db                     import DBAISupport
from app.backend.integrations.atlassian_confluence.atlassian_confluence_db import DBAtlassianConfluence
from app.backend.integrations.atlassian_jira.atlassian_jira_db             import DBAtlassianJira
from app.backend.integrations.azure_wiki.azure_wiki_db                     import DBAzureWiki
from app.backend.integrations.smtp_mail.smtp_mail_db                       import DBSMTPMail
from app.backend.components.projects.projects_db                           import DBProjects
from app.config                                                            import db


EXPORT_VERSION = "1.0"


class ExportService:
    """Collects all project configuration into a portable JSON-compatible dict."""

    @classmethod
    def export_project(cls, project_id: int) -> dict:
        """
        Build a full export payload for the given project.

        Args:
            project_id: ID of the project to export.

        Returns:
            dict with all configuration data.

        Raises:
            ValueError: if the project does not exist.
        """
        project = DBProjects.get_config_by_id(id=project_id)
        if not project:
            raise ValueError(f"Project with ID {project_id} not found")

        payload = {
            "version": EXPORT_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "project_name": project["name"],
            "secrets": cls._export_secrets(project_id),
            "global_prompts": cls._export_global_prompts(),
            "project_prompts": cls._export_project_prompts(project_id),
            "graphs": cls._export_graphs(project_id),
            "nfrs": cls._export_nfrs(project_id),
            "templates": cls._export_templates(project_id),
            "template_groups": cls._export_template_groups(project_id),
            "settings": cls._export_settings(project_id),
            "integrations": {
                "influxdb": cls._export_influxdb(project_id),
                "grafana": cls._export_grafana(project_id),
                "ai_support": cls._export_ai_support(project_id),
                "atlassian_confluence": cls._export_atlassian_confluence(project_id),
                "atlassian_jira": cls._export_atlassian_jira(project_id),
                "azure_wiki": cls._export_azure_wiki(project_id),
                "smtp_mail": cls._export_smtp_mail(project_id),
            },
        }
        return payload

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @classmethod
    def _export_secrets(cls, project_id: int) -> list:
        """Export secrets visible to the project with values masked for security."""
        from sqlalchemy import or_
        try:
            records = db.session.query(DBSecrets).filter(
                or_(DBSecrets.project_id == project_id, DBSecrets.project_id.is_(None))
            ).all()
            result = []
            for r in records:
                d = r.to_dict()
                d["value"] = "secret value"
                result.append(d)
            return result
        except Exception:
            logging.warning(traceback.format_exc())
            return []

    @classmethod
    def _export_global_prompts(cls) -> list:
        """Export custom prompts with no project (globally shared)."""
        try:
            records = db.session.query(DBPrompts).filter(
                DBPrompts.type == "custom",
                DBPrompts.project_id.is_(None)
            ).all()
            return [r.to_dict() for r in records]
        except Exception:
            logging.warning(traceback.format_exc())
            return []

    @classmethod
    def _export_project_prompts(cls, project_id: int) -> list:
        """Export custom prompts that belong to the project."""
        try:
            records = db.session.query(DBPrompts).filter(
                DBPrompts.type == "custom",
                DBPrompts.project_id == project_id
            ).all()
            return [r.to_dict() for r in records]
        except Exception:
            logging.warning(traceback.format_exc())
            return []

    @classmethod
    def _export_graphs(cls, project_id: int) -> list:
        """Export custom (non-default) graphs that belong to the project."""
        try:
            records = db.session.query(DBGraphs).filter(
                DBGraphs.project_id == project_id,
                DBGraphs.type == "custom"
            ).all()
            return [r.to_dict() for r in records]
        except Exception:
            logging.warning(traceback.format_exc())
            return []

    @classmethod
    def _export_nfrs(cls, project_id: int) -> list:
        """Export NFRs (including their rows) for the project."""
        try:
            return DBNFRs.get_configs(project_id)
        except Exception:
            logging.warning(traceback.format_exc())
            return []

    @classmethod
    def _export_templates(cls, project_id: int) -> list:
        """Export templates (including their data rows) for the project."""
        try:
            return DBTemplates.get_configs(project_id)
        except Exception:
            logging.warning(traceback.format_exc())
            return []

    @classmethod
    def _export_template_groups(cls, project_id: int) -> list:
        """Export template groups (including their data rows) for the project."""
        try:
            return DBTemplateGroups.get_configs(project_id)
        except Exception:
            logging.warning(traceback.format_exc())
            return []

    @classmethod
    def _export_settings(cls, project_id: int) -> list:
        """Export project settings as a flat list of {category, key, value, value_type, description}."""
        try:
            return DBProjectSettings.get_project_settings(project_id)
        except Exception:
            logging.warning(traceback.format_exc())
            return []

    @classmethod
    def _export_influxdb(cls, project_id: int) -> list:
        """Export InfluxDB integrations for the project."""
        try:
            return DBInfluxdb.get_configs(project_id)
        except Exception:
            logging.warning(traceback.format_exc())
            return []

    @classmethod
    def _export_grafana(cls, project_id: int) -> list:
        """Export Grafana integrations (including dashboards) for the project."""
        try:
            return DBGrafana.get_configs(project_id)
        except Exception:
            logging.warning(traceback.format_exc())
            return []

    @classmethod
    def _export_ai_support(cls, project_id: int) -> list:
        """Export AI Support integrations for the project."""
        try:
            return DBAISupport.get_configs(project_id)
        except Exception:
            logging.warning(traceback.format_exc())
            return []

    @classmethod
    def _export_atlassian_confluence(cls, project_id: int) -> list:
        """Export Atlassian Confluence integrations for the project."""
        try:
            return DBAtlassianConfluence.get_configs(project_id)
        except Exception:
            logging.warning(traceback.format_exc())
            return []

    @classmethod
    def _export_atlassian_jira(cls, project_id: int) -> list:
        """Export Atlassian Jira integrations for the project."""
        try:
            return DBAtlassianJira.get_configs(project_id)
        except Exception:
            logging.warning(traceback.format_exc())
            return []

    @classmethod
    def _export_azure_wiki(cls, project_id: int) -> list:
        """Export Azure Wiki integrations for the project."""
        try:
            return DBAzureWiki.get_configs(project_id)
        except Exception:
            logging.warning(traceback.format_exc())
            return []

    @classmethod
    def _export_smtp_mail(cls, project_id: int) -> list:
        """Export SMTP Mail integrations (including recipients) for the project."""
        try:
            return DBSMTPMail.get_configs(project_id)
        except Exception:
            logging.warning(traceback.format_exc())
            return []
