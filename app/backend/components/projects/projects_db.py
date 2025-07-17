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
from app.backend.components.templates.templates_db                         import DBTemplates
from app.backend.components.secrets.secrets_db                             import DBSecrets
from app.backend.components.nfrs.nfrs_db                                   import DBNFRs
from app.backend.components.prompts.prompts_db                             import DBPrompts
from app.backend.integrations.data_sources.influxdb_v2.influxdb_db         import DBInfluxdb
from app.backend.integrations.smtp_mail.smtp_mail_db                       import DBSMTPMail
from app.backend.integrations.ai_support.ai_support_db                     import DBAISupport
from app.backend.integrations.atlassian_confluence.atlassian_confluence_db import DBAtlassianConfluence
from app.backend.integrations.atlassian_jira.atlassian_jira_db             import DBAtlassianJira
from app.backend.integrations.azure_wiki.azure_wiki_db                     import DBAzureWiki
from app.backend.integrations.grafana.grafana_db                           import DBGrafana
from app.backend.pydantic_models                                           import ProjectModel


class DBProjects(db.Model):

    __tablename__  = 'projects'
    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name           = db.Column(db.String(120), unique=True, nullable=False)

    # Relationships for cascading deletes
    graphs                         = db.relationship('DBGraphs', backref='project', cascade='all, delete-orphan', lazy=True)
    templates                      = db.relationship('DBTemplates', backref='project', cascade='all, delete-orphan', lazy=True)
    secrets                        = db.relationship('DBSecrets', backref='project', cascade='all, delete-orphan', lazy=True)
    nfrs                           = db.relationship('DBNFRs', backref='project', cascade='all, delete-orphan', lazy=True)
    prompts                        = db.relationship('DBPrompts', backref='project', cascade='all, delete-orphan', lazy=True)
    influxdb_configs               = db.relationship('DBInfluxdb', backref='project', cascade='all, delete-orphan', lazy=True)
    smtp_mail_configs              = db.relationship('DBSMTPMail', backref='project', cascade='all, delete-orphan', lazy=True)
    ai_support_configs             = db.relationship('DBAISupport', backref='project', cascade='all, delete-orphan', lazy=True)
    atlassian_confluence_configs   = db.relationship('DBAtlassianConfluence', backref='project', cascade='all, delete-orphan', lazy=True)
    atlassian_jira_configs         = db.relationship('DBAtlassianJira', backref='project', cascade='all, delete-orphan', lazy=True)
    azure_wiki_configs             = db.relationship('DBAzureWiki', backref='project', cascade='all, delete-orphan', lazy=True)
    grafana_configs                = db.relationship('DBGrafana', backref='project', cascade='all, delete-orphan', lazy=True)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def save(cls, data):
        try:
            validated_data = ProjectModel(**data)
            instance = cls(**validated_data.model_dump())
            db.session.add(instance)
            db.session.commit()
            return instance.id
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def update(cls, data):
        try:
            validated_data = ProjectModel(**data)
            config = db.session.query(cls).filter_by(id=validated_data.id).one_or_none()
            if config:
                config.name = validated_data.name
                db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_configs(cls):
        try:
            query = db.session.query(cls).all()
            valid_configs = []
            for config in query:
                config_dict = config.to_dict()
                validated_data = ProjectModel(**config_dict)
                valid_configs.append(validated_data.model_dump())
            return valid_configs
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_id(cls, id):
        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                config_dict = config.to_dict()
                validated_data = ProjectModel(**config_dict)
                return validated_data.model_dump()
            return None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_project_stats(cls, project_id):
        try:
            integration_models = [
                DBAISupport, DBAtlassianConfluence, DBAtlassianJira,
                DBAzureWiki, DBGrafana, DBInfluxdb, DBSMTPMail
            ]
            integrations_count = sum(model.count(project_id) for model in integration_models)
            project_stats = {
                "integrations": integrations_count,
                "graphs"      : DBGraphs.count(project_id),
                "nfrs"        : DBNFRs.count(project_id),
                "templates"   : DBTemplates.count(project_id),
                "secrets"     : DBSecrets.count(project_id),
                "prompts"     : DBPrompts.count(project_id)
            }
            return project_stats
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_project_output_configs(cls, project_id):
        try:
            integration_models = [
                DBAtlassianConfluence, DBAtlassianJira,
                DBAzureWiki, DBSMTPMail
            ]
            integration_types = {
                DBAtlassianConfluence: 'atlassian_confluence',
                DBAtlassianJira: 'atlassian_jira',
                DBAzureWiki: 'azure_wiki',
                DBSMTPMail: 'smtp_mail'
            }
            output_configs = []
            for model in integration_models:
                configs = model.get_configs(project_id)
                for config in configs:
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
                db.session.delete(config)
                db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise
