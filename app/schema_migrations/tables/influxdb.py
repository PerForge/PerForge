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


class InfluxdbAddCustomVarsRegex(BaseMigration):
    name = "influxdb: add custom_vars, regex"

    def apply(self, connection, inspector):
        table_name = 'influxdb'
        try:
            columns = [c['name'] for c in inspector.get_columns(table_name)]
        except Exception:
            # Table may not exist yet; let create_all handle schema creation
            return

        # Add custom_vars (VARCHAR(500)) if missing
        if 'custom_vars' not in columns:
            log.info(f"Applying migration: Adding column 'custom_vars' to table '{table_name}'")
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN custom_vars VARCHAR(500)"))
            log.info("Migration for 'custom_vars' applied successfully.")
            inspector = self.refresh_inspector(connection)
            columns = [c['name'] for c in inspector.get_columns(table_name)]

        # Add regex (VARCHAR(500)) if missing
        if 'regex' not in columns:
            log.info(f"Applying migration: Adding column 'regex' to table '{table_name}'")
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN regex VARCHAR(500)"))
            log.info("Migration for 'regex' applied successfully.")


# Export list of migrations for this table (supports multiple in the future)
MIGRATIONS = [
    InfluxdbAddCustomVarsRegex(),
]
