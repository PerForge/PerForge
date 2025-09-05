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


class TemplateDataAddAISwitches(BaseMigration):
    name = "template_data: add ai switches"

    def apply(self, connection, inspector):
        table_name = 'template_data'
        try:
            columns = [c['name'] for c in inspector.get_columns(table_name)]
        except Exception:
            return

        if 'ai_graph_switch' not in columns:
            log.info(f"Applying migration: Adding column 'ai_graph_switch' to table '{table_name}'")
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN ai_graph_switch INTEGER DEFAULT 0"))
            log.info("Migration for 'ai_graph_switch' applied successfully.")
            inspector = self.refresh_inspector(connection)
            columns = [c['name'] for c in inspector.get_columns(table_name)]

        if 'ai_to_graphs_switch' not in columns:
            log.info(f"Applying migration: Adding column 'ai_to_graphs_switch' to table '{table_name}'")
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN ai_to_graphs_switch INTEGER DEFAULT 0"))
            log.info("Migration for 'ai_to_graphs_switch' applied successfully.")


# Export list of migrations for this table
MIGRATIONS = [
    TemplateDataAddAISwitches(),
]
