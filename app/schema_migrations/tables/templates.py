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

import logging
from sqlalchemy import text
from app.schema_migrations.base import BaseMigration

log = logging.getLogger("app.migrations")


class TemplatesDropAIGraphSwitches(BaseMigration):
    name = "templates: drop ai_graph_switch, ai_to_graphs_switch"

    def apply(self, connection, inspector):
        table_name = 'templates'
        try:
            table_names = inspector.get_table_names()
            if table_name not in table_names:
                return

            columns = inspector.get_columns(table_name)
            col_names = [c['name'] for c in columns]
            needs_rebuild = ('ai_graph_switch' in col_names) or ('ai_to_graphs_switch' in col_names)
            if not needs_rebuild:
                return

            try:
                log.info("Attempting direct DROP COLUMN on 'templates'")
                if 'ai_graph_switch' in col_names:
                    connection.execute(text(f"ALTER TABLE {table_name} DROP COLUMN ai_graph_switch"))
                if 'ai_to_graphs_switch' in col_names:
                    connection.execute(text(f"ALTER TABLE {table_name} DROP COLUMN ai_to_graphs_switch"))
                # Verify
                inspector = self.refresh_inspector(connection)
                new_cols = [c['name'] for c in inspector.get_columns(table_name)]
                if ('ai_graph_switch' not in new_cols) and ('ai_to_graphs_switch' not in new_cols):
                    log.info("Direct DROP COLUMN succeeded for 'templates'.")
                    return
                else:
                    log.info("Direct DROP COLUMN appears incomplete; skipping rebuild per request.")
                    return
            except Exception as e:
                log.info(f"Direct DROP COLUMN unsupported or failed: {e}; skipping rebuild per request.")
                return
        except Exception as e:
            log.warning(f"Could not drop columns on 'templates'. Error: {e}")


# Export list of migrations for this table
MIGRATIONS = [
    TemplatesDropAIGraphSwitches(),
]
