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

import os
import logging

from app.config                                  import db
from app.backend.components.users.users_db       import DBUsers
from app.backend.components.secrets.secrets_db   import DBSecrets
from app.backend.components.projects.projects_db import DBProjects
from app.backend.components.prompts.prompts_db   import DBPrompts
from app.backend.components.graphs.graphs_db     import DBGraphs
from app.backend.components.nfrs.nfrs_db         import DBNFRs, DBNFRRows
from app.backend.components.templates.templates_db import DBTemplates, DBTemplateData
from app.backend.components.templates.template_groups_db import DBTemplateGroups, DBTemplateGroupData
from app.backend.integrations.ai_support.ai_support_db import DBAISupport
from app.backend.integrations.atlassian_confluence.atlassian_confluence_db import DBAtlassianConfluence
from app.backend.integrations.atlassian_jira.atlassian_jira_db import DBAtlassianJira
from app.backend.integrations.azure_wiki.azure_wiki_db import DBAzureWiki
from app.backend.integrations.grafana.grafana_db import DBGrafana, DBGrafanaDashboards
from app.backend.integrations.data_sources.influxdb_v2.influxdb_db import DBInfluxdb
from app.backend.integrations.smtp_mail.smtp_mail_db import DBSMTPMail, DBSMTPMailRecipient
from logging.handlers                            import RotatingFileHandler
from flask                                       import Flask
from flask_login                                 import LoginManager
from flask_bcrypt                                import Bcrypt
from flask_compress                              import Compress

from app.api                                     import register_blueprints
from app.migrations                              import run_migrations

# Grabs the folder where the script runs.
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
# Enable compression
Compress(app)
# Minimum response size in bytes to apply gzip compression
app.config['COMPRESS_MIN_SIZE'] = 500

# Setup database
database_directory = os.path.join(basedir, "data")
app.config['SQLALCHEMY_DATABASE_URI']        = 'sqlite:///'+database_directory+'/database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


class IgnoreStaticRequests(logging.Filter):

    def filter(self, record):
        return 'GET /static/' not in record.getMessage()

log_directory = os.path.join(basedir, "logs")
log_file = os.path.join(log_directory, "info.log")

if not os.path.exists(log_directory):
    os.makedirs(log_directory)

handler = RotatingFileHandler(
    filename=log_file, maxBytes=1024 * 1024 * 50, backupCount=1
)

handler.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

# Configure logging
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addFilter(IgnoreStaticRequests())
# Also send werkzeug logs to the file
werkzeug_logger.addHandler(handler)

app.config.from_object('app.config.Config')

bc = Bcrypt(app)  # flask-bcrypt

with app.app_context():
    db.metadata.create_all(bind=db.engine, tables=[
        DBUsers.__table__,
        DBSecrets.__table__,
        DBProjects.__table__,
        DBPrompts.__table__,
        DBAISupport.__table__,
        DBAtlassianConfluence.__table__,
        DBAtlassianJira.__table__,
        DBAzureWiki.__table__,
        DBGrafana.__table__,
        DBInfluxdb.__table__,
        DBSMTPMail.__table__,
        DBNFRs.__table__,
        DBNFRRows.__table__,
        DBTemplates.__table__,
        DBTemplateData.__table__,
        DBTemplateGroups.__table__,
        DBTemplateGroupData.__table__,
        DBGraphs.__table__,
        DBGrafanaDashboards.__table__,
        DBSMTPMailRecipient.__table__
        ], checkfirst=True)

    # Run migrations to add/modify columns
    run_migrations()

    DBPrompts.load_default_prompts_from_yaml()

# Register API blueprints
register_blueprints(app)

login_manager = LoginManager()
login_manager.init_app(app)

# # Import routing, models and Start the App
from app.views import (auth, graphs, integrations, nfrs, other, projects, prompts, reporting, secrets, templates, report)
