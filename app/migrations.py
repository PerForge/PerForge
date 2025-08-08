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

    except Exception as e:
        # If the table doesn't exist yet, inspector will fail. This is okay
        # because create_all() will create it with all columns anyway.
        log.warning(f"Could not run migrations, likely because tables do not exist yet. Error: {e}")
