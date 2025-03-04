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

from decouple         import config
from flask_sqlalchemy import SQLAlchemy


basedir     = os.path.abspath(os.path.dirname(__file__))
# Configure SQLAlchemy with optimized connection pooling settings
db = SQLAlchemy(engine_options={
    'pool_size': 10,  # Default number of connections to maintain
    'max_overflow': 20,  # Allow up to this many extra connections when pool_size is reached
    'pool_timeout': 30,  # Seconds to wait before giving up on getting a connection
    'pool_recycle': 300,  # Recycle connections after 5 minutes to avoid stale connections
    'pool_pre_ping': True  # Check connection validity before using it from the pool
})

class Config:

    CSRF_ENABLED = True
    SECRET_KEY   = config('SECRET_KEY', default='S#perS3crEt_007')