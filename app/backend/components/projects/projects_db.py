# Copyright 2024 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>
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

import traceback
import logging

from app.config                                                            import db
from app.backend.components.graphs.graphs_db                               import DBGraphs
from app.backend.components.templates.template_groups_db                   import DBTemplateGroups, DBTemplateGroupData
from app.backend.components.templates.templates_db                         import DBTemplates, DBTemplateData
from app.backend.components.secrets.secrets_db                             import DBSecrets
from app.backend.components.nfrs.nfrs_db                                   import DBNFRs, DBNFRRows
from app.backend.components.prompts.prompts_db                             import DBPrompts
from app.backend.integrations.data_sources.influxdb_v2.influxdb_db         import DBInfluxdb
from app.backend.integrations.smtp_mail.smtp_mail_db                       import DBSMTPMail, DBSMTPMailRecipient
from app.backend.integrations.ai_support.ai_support_db                     import DBAISupport
from app.backend.integrations.atlassian_confluence.atlassian_confluence_db import DBAtlassianConfluence
from app.backend.integrations.atlassian_jira.atlassian_jira_db             import DBAtlassianJira
from app.backend.integrations.azure_wiki.azure_wiki_db                     import DBAzureWiki
from app.backend.integrations.grafana.grafana_db                           import DBGrafana, DBGrafanaDashboards
from app.backend.pydantic_models                                           import ProjectModel
from sqlalchemy                                                            import text, MetaData
from itertools                                                             import chain


class DBProjects(db.Model):

    __tablename__  = 'projects'
    __table_args__ = {'schema': 'public'}
    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name           = db.Column(db.String(120), unique=True, nullable=False)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def save(cls, data):
        try:
            validated_data = ProjectModel(**data)
            instance       = cls(**validated_data.model_dump())
            db.session.add(instance)
            db.session.commit()
            DBProjects.create_schema(instance)
            DBProjects.create_all_tables(instance)
            return instance.id
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def create_schema(cls, instance):
        schema_name         = getattr(instance, 'name')
        create_schema_query = text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')
        try:
            db.session.execute(create_schema_query)
            db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def create_all_tables(cls, instance):
        schema_name = getattr(instance, 'name')
        metadata    = MetaData(schema=schema_name)
        tables      = [
            DBAISupport.__table__,
            DBAtlassianConfluence.__table__,
            DBAtlassianJira.__table__,
            DBAzureWiki.__table__,
            DBGrafana.__table__,
            DBGrafanaDashboards.__table__,
            DBGraphs.__table__,
            DBInfluxdb.__table__,
            DBNFRs.__table__,
            DBNFRRows.__table__,
            DBSMTPMail.__table__,
            DBSMTPMailRecipient.__table__,
            DBTemplateGroups.__table__,
            DBTemplateGroupData.__table__,
            DBTemplates.__table__,
            DBTemplateData.__table__
        ]

        for table in tables:
            table.schema   = schema_name
            table.metadata = metadata

        try:
            metadata.create_all(bind=db.engine, tables=tables, checkfirst=True)
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_configs(cls):
        try:
            query         = db.session.query(cls).all()
            valid_configs = []

            for config in query:
                config_dict    = config.to_dict()
                validated_data = ProjectModel(**config_dict)
                valid_configs.append(validated_data.model_dump())
            return valid_configs
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_id(cls, id):
        try:
            config         = db.session.query(cls).filter_by(id=id).one_or_none()
            config_dict    = config.to_dict()
            validated_data = ProjectModel(**config_dict)
            return validated_data.model_dump()
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_project_stats(cls, id):
        try:
            config             = cls.get_config_by_id(id)
            schema_name        = config['name']
            integration_models = [
                DBAISupport, DBAtlassianConfluence, DBAtlassianJira,
                DBAzureWiki, DBGrafana, DBInfluxdb, DBSMTPMail
            ]
            integrations_count = sum(model.count(schema_name) for model in integration_models)
            project_stats = {
                "integrations": integrations_count,
                "graphs"      : DBGraphs.count(schema_name),
                "nfrs"        : DBNFRs.count(schema_name),
                "templates"   : DBTemplates.count(schema_name),
                "secrets"     : DBSecrets.count(id),
                "prompts"     : DBPrompts.count(id)
            }
            return project_stats
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_project_output_configs(cls, id):
        try:
            config             = cls.get_config_by_id(id)
            schema_name        = config['name']
            integration_models = [
                DBAtlassianConfluence, DBAtlassianJira,
                DBAzureWiki, DBSMTPMail
            ]
            output_configs = list(chain.from_iterable(
                model.get_configs(schema_name) for model in integration_models
            ))
            return output_configs
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def delete(cls, id):
        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                schema_name = config.name
                db.session.delete(config)
                db.session.commit()
                cls.drop_schema(schema_name)
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @staticmethod
    def drop_schema(schema_name):
        drop_schema_query = text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
        try:
            db.session.execute(drop_schema_query)
            db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise