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

from app.backend.integrations.secondary.influxdb import Influxdb
from datetime                                    import datetime


class TestObj:

    def __init__(self, test_id, project):
        self.test_id                  = test_id
        self.project                  = project
        self.influxdb_obj             = Influxdb(project=self.project).connect_to_influxdb()
        self.current_start_time       = self.influxdb_obj.get_start_time(self.test_id)
        self.current_end_time         = self.influxdb_obj.get_end_time(self.test_id)
        self.current_human_start_time = self.influxdb_obj.get_human_start_time(self.test_id)
        self.current_human_end_time   = self.influxdb_obj.get_human_end_time(self.test_id)
        self.test_name                = self.influxdb_obj.get_test_name(self.test_id, self.current_start_time, self.current_end_time)
        self.current_start_timestamp  = self.influxdb_obj.get_start_tmp(self.test_id)
        self.current_end_timestamp    = self.influxdb_obj.get_end_tmp(self.test_id)
        self.duration                 = self.calculate_duration()
        self.max_active_users         = self.influxdb_obj.get_max_active_users(self.test_id, self.current_start_time, self.current_end_time)

    def calculate_duration(self):
        datetime1          = datetime.strptime(self.current_start_time, "%Y-%m-%dT%H:%M:%SZ")
        datetime2          = datetime.strptime(self.current_end_time, "%Y-%m-%dT%H:%M:%SZ")
        difference         = datetime2 - datetime1
        seconds_difference = round(difference.total_seconds())
        return seconds_difference