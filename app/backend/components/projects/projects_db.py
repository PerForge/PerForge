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
from app.backend.integrations.data_sources.timescaledb.timescaledb_test_metadata_db         import DBTestMetadata
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

            # Sanitize the schema name to ensure it's valid for PostgreSQL
            # PostgreSQL identifiers are limited to alphanumeric characters and underscores
            schema_name = validated_data.name
            schema_name = ''.join(c if c.isalnum() else '_' for c in schema_name)

            # Check if schema already exists
            schema_exists_query = text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema_name")
            result = db.session.execute(schema_exists_query, {"schema_name": schema_name}).fetchone()

            if result:
                raise ValueError(f"A project with name '{validated_data.name}' already exists or was previously deleted. Please use a different name.")

            # Update the name with sanitized version
            validated_data.name = schema_name

            instance = cls(**validated_data.model_dump())
            db.session.add(instance)
            db.session.commit()

            # Store the schema name before closing the session
            schema_name = instance.name
            project_id = instance.id

            # Close all existing connections to ensure clean schema creation
            db.session.close()
            db.engine.dispose()

            # Create a new session for schema operations
            try:
                # Get a fresh instance that's attached to a new session
                fresh_instance = db.session.query(cls).filter_by(id=project_id).one()
                DBProjects.create_schema(fresh_instance)
                DBProjects.create_all_tables(fresh_instance)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logging.warning(str(traceback.format_exc()))
                raise
            finally:
                db.session.close()
            
            return project_id
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def update(cls, data):
        try:
            validated_data = ProjectModel(**data)
            instance = db.session.query(cls).filter_by(id=validated_data.id).one_or_none()

            if not instance:
                raise ValueError(f"Project with ID {validated_data.id} not found")

            # Store the old schema name before updating
            old_schema_name = instance.name

            # Update only the allowed fields (currently just name)
            instance.name = validated_data.name

            # Commit the changes to the projects table
            db.session.commit()

            # If the schema name changed, we need to rename the schema
            if old_schema_name != instance.name:
                # Close all existing connections
                db.session.close()
                db.engine.dispose()

                # Rename the schema
                rename_schema_query = text(f'ALTER SCHEMA "{old_schema_name}" RENAME TO "{instance.name}"')
                db.session.execute(rename_schema_query)
                db.session.commit()

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
            DBTemplateData.__table__,
            DBTestMetadata.__table__
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
            # Close all existing database connections to ensure schema changes take effect immediately
            db.session.close()
            db.engine.dispose()

            # Use the existing session instead of creating a scoped session
            # Flask-SQLAlchemy 3.x handles sessions differently
            
            config = cls.get_config_by_id(id)
            schema_name = config['name']

            # Reset schema contexts for all models
            integration_models = [
                DBAISupport, DBAtlassianConfluence, DBAtlassianJira,
                DBAzureWiki, DBGrafana, DBInfluxdb, DBSMTPMail
            ]

            # Reset schema for all models that use schema_name
            for model in integration_models:
                model.__table__.schema = None
                model.__table__.schema = schema_name

            # Reset schema for other models
            DBGraphs.__table__.schema = None
            DBGraphs.__table__.schema = schema_name

            DBNFRs.__table__.schema = None
            DBNFRs.__table__.schema = schema_name

            DBTemplates.__table__.schema = None
            DBTemplates.__table__.schema = schema_name

            # Count items
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

            # Map each model to its integration type
            # SHOULD BE THE SAME AS REPORT REGISTRY!!!!!!!!!
            integration_types = {
                DBAtlassianConfluence: 'atlassian_confluence',
                DBAtlassianJira: 'atlassian_jira',
                DBAzureWiki: 'azure_wiki',
                DBSMTPMail: 'smtp_mail'
            }

            output_configs = []
            for model in integration_models:
                configs = model.get_configs(schema_name)
                for config in configs:
                    # Add integration_type to each config
                    config['integration_type'] = integration_types[model]
                output_configs.extend(configs)

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
