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


class GrafanaAddDefaultDashboardId(BaseMigration):
    name = "grafana: add default_dashboard_id"

    def apply(self, connection, inspector):
        table_name = 'grafana'
        try:
            columns = [c['name'] for c in inspector.get_columns(table_name)]
        except Exception:
            return

        if 'default_dashboard_id' not in columns:
            log.info(f"Applying migration: Adding column 'default_dashboard_id' to table '{table_name}'")
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN default_dashboard_id INTEGER REFERENCES grafana_dashboards(id) ON DELETE SET NULL"))
            log.info("Migration for 'default_dashboard_id' applied successfully.")


MIGRATIONS = [
    GrafanaAddDefaultDashboardId(),
]
