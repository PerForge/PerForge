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


class GraphsAddTypeRelaxNulls(BaseMigration):
    name = "graphs: add type + relax nulls"

    def apply(self, connection, inspector):
        graphs_table = 'graphs'
        try:
            graphs_columns = inspector.get_columns(graphs_table)
            graphs_cols_by_name = {c['name']: c for c in graphs_columns}
        except Exception:
            return

        need_add_type = bool(graphs_columns) and 'type' not in graphs_cols_by_name
        need_relax_nulls = False
        for col in ('project_id', 'grafana_id', 'dash_id', 'view_panel'):
            if col in graphs_cols_by_name and graphs_cols_by_name[col].get('nullable') is False:
                need_relax_nulls = True
                break

        if not (need_add_type or need_relax_nulls):
            # Still ensure classification is correct below
            pass
        else:
            log.info(
                f"Applying migration for '{graphs_table}': add_type={need_add_type}, "
                f"relax_nulls={need_relax_nulls} (SQLite-only path)"
            )

            # SQLite: rebuild table pattern
            prev_fk = None
            try:
                prev_fk = connection.execute(text('PRAGMA foreign_keys')).scalar()
                connection.execute(text('PRAGMA foreign_keys=OFF'))
                with connection.begin():
                    # ensure clean temp table
                    connection.execute(text('DROP TABLE IF EXISTS graphs_new'))
                    create_sql = text(
                """
                CREATE TABLE IF NOT EXISTS graphs_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    name VARCHAR(120) NOT NULL,
                    type VARCHAR(20) NOT NULL DEFAULT 'custom',
                    grafana_id INTEGER,
                    dash_id INTEGER,
                    view_panel INTEGER,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    custom_vars VARCHAR(500),
                    prompt_id INTEGER,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY(grafana_id) REFERENCES grafana(id) ON DELETE CASCADE,
                    FOREIGN KEY(dash_id) REFERENCES grafana_dashboards(id) ON DELETE CASCADE,
                    FOREIGN KEY(prompt_id) REFERENCES prompts(id) ON DELETE SET NULL
                )
                """
                    )
                    connection.execute(create_sql)
                    # Copy data; set type='custom' for existing rows
                    select_cols = 'id, project_id, name, grafana_id, dash_id, view_panel, width, height, custom_vars, prompt_id'
                    connection.execute(text(
                        f"INSERT INTO graphs_new (id, project_id, name, grafana_id, dash_id, view_panel, width, height, custom_vars, prompt_id, type) "
                        f"SELECT {select_cols}, CASE WHEN project_id IS NULL THEN 'default' ELSE 'custom' END as type FROM {graphs_table}"
                    ))
                    # Swap tables
                    connection.execute(text(f'DROP TABLE {graphs_table}'))
                    connection.execute(text('ALTER TABLE graphs_new RENAME TO graphs'))
                    # Indexes
                    connection.execute(text('CREATE INDEX IF NOT EXISTS ix_graphs_project_id ON graphs (project_id)'))
                    connection.execute(text('CREATE INDEX IF NOT EXISTS ix_graphs_type ON graphs (type)'))
            finally:
                # Restore original foreign_keys setting for the connection
                try:
                    if str(prev_fk) in ('1', 'ON'):
                        connection.execute(text('PRAGMA foreign_keys=ON'))
                    else:
                        connection.execute(text('PRAGMA foreign_keys=OFF'))
                except Exception:
                    pass
            log.info("Migration for 'graphs' completed via SQLite table rebuild.")

        # Ensure internal graphs correctly classified as 'default'
        try:
            inspector = self.refresh_inspector(connection)
            graphs_columns = inspector.get_columns(graphs_table)
            graphs_cols_by_name = {c['name']: c for c in graphs_columns}
            if 'type' in graphs_cols_by_name:
                connection.execute(text("UPDATE graphs SET type='default' WHERE project_id IS NULL AND (type IS NULL OR type <> 'default')"))
        except Exception:
            pass


# Export list of migrations for this table
MIGRATIONS = [
    GraphsAddTypeRelaxNulls(),
]
