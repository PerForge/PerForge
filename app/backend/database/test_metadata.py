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

from app.config import db


class DBTestMetadata(db.Model):
    __tablename__ = 'test_metadata'
    test_title    = db.Column(db.Text, primary_key=True, unique=True)
    application   = db.Column(db.Text)
    tool          = db.Column(db.Text)
    start_time    = db.Column(db.DateTime(timezone=True), nullable=False)
    end_time      = db.Column(db.DateTime(timezone=True), nullable=False)
    duration      = db.Column(db.BigInteger)
    max_threads   = db.Column(db.Float)
    tags          = db.Column(db.Text)

    def __init__(self, test_title, application=None, tool=None, start_time=None, end_time=None, duration=None, max_threads=None, tags=None):
        self.test_title  = test_title
        self.application = application
        self.tool        = tool
        self.start_time  = start_time
        self.end_time    = end_time
        self.duration    = duration
        self.max_threads = max_threads
        self.tags        = tags