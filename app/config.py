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

from decouple import config


basedir     = os.path.abspath(os.path.dirname(__file__))
config_path = "./app/data/config.json"

class Config:
    CSRF_ENABLED                   = True
    SECRET_KEY                     = config('SECRET_KEY', default='S#perS3crEt_007')
    database_path                  = os.path.join(basedir, 'db.sqlite3')
    SQLALCHEMY_DATABASE_URI        = f'sqlite:///{database_path}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False