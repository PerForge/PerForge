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

from app.config                                import db
from app.backend.database.ai_support           import DBAISupport
from app.backend.database.atlassian_confluence import DBAtlassianConfluence
from app.backend.database.atlassian_jira       import DBAtlassianJira
from app.backend.database.azure_wiki           import DBAzureWiki
from app.backend.database.grafana              import DBGrafana, DBGrafanaDashboards
from app.backend.database.graphs               import DBGraphs
from app.backend.database.influxdb             import DBInfluxdb
from app.backend.database.nfrs                 import DBNFRs, DBNFRRows
from app.backend.database.prompts              import DBPrompts
from app.backend.database.smtp_mail            import DBSMTPMail, DBSMTPMailRecipient
from app.backend.database.template_groups      import DBTemplateGroups, DBTemplateGroupData
from app.backend.database.templates            import DBTemplates, DBTemplateData
from app.backend.database.secrets              import DBSecrets
from sqlalchemy                                import text, MetaData
from sqlalchemy.exc                            import IntegrityError
from itertools                                 import chain


class DBProjects(db.Model):

    __tablename__  = 'projects'
    __table_args__ = {'schema': 'public'}
    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name           = db.Column(db.String(120), unique=True, nullable=False)

    def __init__(self, name):
        self.name = name

    def to_dict(self):
        return {
            'id'  : self.id,
            'name': self.name
        }

    def save(self):
        db.session.add(self)
        try:
            db.session.commit()
            self.create_schema()
            self.create_all_tables()
            return self.id
        except IntegrityError:
            db.session.rollback()
            raise

    def create_schema(self):
        create_schema_query = text(f'CREATE SCHEMA IF NOT EXISTS "{self.name}"')
        try:
            db.session.execute(create_schema_query)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise

    def create_all_tables(self):
        metadata = MetaData(schema=self.name)
        tables = [
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
            table.schema   = self.name
            table.metadata = metadata

        try:
            metadata.create_all(bind=db.engine, tables=tables, checkfirst=True)
        except Exception as e:
            raise RuntimeError(f"Failed to create tables for schema {self.name}: {e}")

    @classmethod
    def get_configs(cls):
        query = db.session.query(cls).all()
        list  = [config.to_dict() for config in query]
        return list

    @classmethod
    def get_config_by_id(cls, id):
        config = db.session.query(cls).filter_by(id=id).one_or_none().to_dict()
        return config

    @classmethod
    def get_project_stats(cls, id):
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

    @classmethod
    def get_project_output_configs(cls, id):
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

    @classmethod
    def delete(cls, id):
        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                schema_name = config.name
                db.session.delete(config)
                db.session.commit()
                cls.drop_schema(schema_name)
        except IntegrityError:
            db.session.rollback()
            raise

    @staticmethod
    def drop_schema(schema_name):
        drop_schema_query = text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
        try:
            db.session.execute(drop_schema_query)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise