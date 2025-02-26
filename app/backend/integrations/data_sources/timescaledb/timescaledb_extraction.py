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

import logging
import pandas as pd

from app.backend.integrations.data_sources.base_extraction                                      import DataExtractionBase
from app.backend.errors                                                                         import ErrorMessages
from typing                                                                                     import List, Dict, Any
from app.backend.integrations.data_sources.timescaledb.timescaledb_test_metadata_db                       import DBTestMetadata


class TimeScaleDB(DataExtractionBase):

    def __init__(self, project, id = None):
        super().__init__(project)

    def _fetch_test_log(self) -> List[Dict[str, Any]]:
        try:
            records = DBTestMetadata.get_all_metadata(schema_name=self.schema_name)
            df = pd.DataFrame(records)
            sorted_df = df.sort_values(by='start_time')
            return sorted_df.to_dict(orient='records')
        except Exception as er:
            logging.error(ErrorMessages.ER00057.value.format(self.schema_name))
            logging.error(er)
            return []