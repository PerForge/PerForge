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

import os
import logging

from app.models       import db, DBMigrations
from logging.handlers import RotatingFileHandler
from flask            import Flask
from flask_login      import LoginManager
from flask_bcrypt     import Bcrypt
from flask_compress   import Compress


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

# Add the handler to the logger
logger = logging.getLogger()
logger.addHandler(handler)

flask_logger = logging.getLogger('werkzeug')  # Get flask logger
flask_logger.addFilter(IgnoreStaticRequests())  # Add custom filter to flask logger

app.config.from_object('app.config.Config')

bc = Bcrypt(app)  # flask-bcrypt

with app.app_context():
    db.create_all()
    DBMigrations.migration_1()

login_manager = LoginManager()
login_manager.init_app(app)

# # Import routing, models and Start the App
from app.views import (auth, custom, graphs, integrations, nfrs, other, projects, prompts, reporting, secrets, templates, report)