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
from sqlalchemy import inspect, text
from app.config import db

log = logging.getLogger(__name__)

def run_migrations():
    try:
        with db.engine.connect() as connection:
            inspector = inspect(db.engine)

            # --- Migration: Add 'custom_vars' to 'influxdb' table ---
            table_name = 'influxdb'
            column_name = 'custom_vars'
            columns = [c['name'] for c in inspector.get_columns(table_name)]

            if column_name not in columns:
                log.info(f"Applying migration: Adding column '{column_name}' to table '{table_name}'")
                # SQLite permits adding columns at the end; VARCHAR is fine (treated as TEXT).
                # For Postgres, VARCHAR(500) is also valid.
                alter_command = text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} VARCHAR(500)")
                connection.execute(alter_command)
                log.info(f"Migration for '{column_name}' applied successfully.")

            # --- Migration: graphs table adjustments for internal/external support ---
            graphs_table = 'graphs'
            try:
                graphs_columns = inspector.get_columns(graphs_table)
                graphs_cols_by_name = {c['name']: c for c in graphs_columns}
            except Exception as e:
                graphs_columns = []
                graphs_cols_by_name = {}

            need_add_type = bool(graphs_columns) and 'type' not in graphs_cols_by_name
            # If table absent, create_all() will create with new schema; skip.
            need_relax_nulls = False
            for col in ('project_id', 'grafana_id', 'dash_id', 'view_panel'):
                if col in graphs_cols_by_name and graphs_cols_by_name[col].get('nullable') is False:
                    need_relax_nulls = True
                    break

            if need_add_type or need_relax_nulls:
                dialect = db.engine.url.get_dialect().name if hasattr(db.engine, 'url') else db.engine.name
                log.info(f"Applying migration for '{graphs_table}': add_type={need_add_type}, relax_nulls={need_relax_nulls}, dialect={dialect}")

                if dialect == 'sqlite':
                    # SQLite: rebuild table pattern
                    connection.execute(text('PRAGMA foreign_keys=OFF'))
                    connection.execute(text('BEGIN TRANSACTION'))

                    # Create new table with desired schema
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
                    existing_cols = [c['name'] for c in graphs_columns]
                    select_cols = 'id, project_id, name, grafana_id, dash_id, view_panel, width, height, custom_vars, prompt_id'
                    connection.execute(text(
                        f"INSERT INTO graphs_new (id, project_id, name, grafana_id, dash_id, view_panel, width, height, custom_vars, prompt_id, type) "
                        f"SELECT {select_cols}, CASE WHEN project_id IS NULL THEN 'default' ELSE 'custom' END as type FROM {graphs_table}"
                    ))

                    # Drop old and rename new
                    connection.execute(text(f'DROP TABLE {graphs_table}'))
                    connection.execute(text('ALTER TABLE graphs_new RENAME TO graphs'))

                    # Recreate indexes
                    connection.execute(text('CREATE INDEX IF NOT EXISTS ix_graphs_project_id ON graphs (project_id)'))
                    connection.execute(text('CREATE INDEX IF NOT EXISTS ix_graphs_type ON graphs (type)'))

                    connection.execute(text('COMMIT'))
                    connection.execute(text('PRAGMA foreign_keys=ON'))
                    log.info("Migration for 'graphs' completed via SQLite table rebuild.")
                else:
                    # Postgres/MySQL: simple ALTERs
                    if need_add_type:
                        connection.execute(text("ALTER TABLE graphs ADD COLUMN type VARCHAR(20) DEFAULT 'custom' NOT NULL"))
                        # Classify existing rows: default for global (project_id IS NULL), otherwise custom
                        connection.execute(text("UPDATE graphs SET type='default' WHERE project_id IS NULL"))
                        connection.execute(text('CREATE INDEX IF NOT EXISTS ix_graphs_type ON graphs (type)'))
                    if need_relax_nulls:
                        # Drop NOT NULLs where applicable
                        if 'project_id' in graphs_cols_by_name and graphs_cols_by_name['project_id'].get('nullable') is False:
                            connection.execute(text('ALTER TABLE graphs ALTER COLUMN project_id DROP NOT NULL'))
                        if 'grafana_id' in graphs_cols_by_name and graphs_cols_by_name['grafana_id'].get('nullable') is False:
                            connection.execute(text('ALTER TABLE graphs ALTER COLUMN grafana_id DROP NOT NULL'))
                        if 'dash_id' in graphs_cols_by_name and graphs_cols_by_name['dash_id'].get('nullable') is False:
                            connection.execute(text('ALTER TABLE graphs ALTER COLUMN dash_id DROP NOT NULL'))
                        if 'view_panel' in graphs_cols_by_name and graphs_cols_by_name['view_panel'].get('nullable') is False:
                            connection.execute(text('ALTER TABLE graphs ALTER COLUMN view_panel DROP NOT NULL'))
                    log.info("Migration for 'graphs' completed via ALTER TABLE statements.")

            # Ensure internal graphs are correctly classified as 'default'
            # even if no structural changes were needed above.
            try:
                graphs_columns = inspector.get_columns(graphs_table)
                graphs_cols_by_name = {c['name']: c for c in graphs_columns}
                if 'type' in graphs_cols_by_name:
                    connection.execute(text("UPDATE graphs SET type='default' WHERE project_id IS NULL AND (type IS NULL OR type <> 'default')"))
            except Exception:
                # If table or column doesn't exist yet, ignore.
                pass

    except Exception as e:
        # If the table doesn't exist yet, inspector will fail. This is okay
        # because create_all() will create it with all columns anyway.
        log.warning(f"Could not run migrations, likely because tables do not exist yet. Error: {e}")
