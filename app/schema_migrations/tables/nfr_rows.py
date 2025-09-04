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


class NFRRowsNormalize(BaseMigration):
    name = "nfr_rows: drop weight, threshold FLOAT"

    def apply(self, connection, inspector):
        try:
            table_names = inspector.get_table_names()
            if 'nfr_rows' not in table_names:
                return

            nfr_columns = inspector.get_columns('nfr_rows')
            nfr_col_names = [c['name'] for c in nfr_columns]
            threshold_col = next((c for c in nfr_columns if c['name'] == 'threshold'), None)
            current_type = str(threshold_col['type']).upper() if threshold_col else ''

            needs_rebuild = False
            if 'weight' in nfr_col_names:
                needs_rebuild = True
            if not any(t in current_type for t in ['FLOAT', 'REAL', 'DOUBLE']):
                needs_rebuild = True

            if not needs_rebuild:
                return

            log.info("Applying migration (SQLite-only): Rebuild 'nfr_rows' (no 'weight', FLOAT 'threshold')")
            prev_fk = None
            try:
                prev_fk = connection.execute(text('PRAGMA foreign_keys')).scalar()
                connection.execute(text('PRAGMA foreign_keys=OFF'))
                connection.execute(text("DROP TABLE IF EXISTS nfr_rows_new"))
                connection.execute(text(
                    """
                    CREATE TABLE nfr_rows_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        regex BOOLEAN,
                        scope VARCHAR(500) NOT NULL,
                        metric VARCHAR(120) NOT NULL,
                        operation VARCHAR(120) NOT NULL,
                        threshold FLOAT NOT NULL,
                        nfr_id INTEGER NOT NULL,
                        FOREIGN KEY(nfr_id) REFERENCES nfrs(id) ON DELETE CASCADE
                    )
                    """
                ))
                connection.execute(text(
                    """
                    INSERT INTO nfr_rows_new (id, regex, scope, metric, operation, threshold, nfr_id)
                    SELECT id, regex, scope, metric, operation, threshold, nfr_id FROM nfr_rows
                    """
                ))
                connection.execute(text("DROP TABLE nfr_rows"))
                connection.execute(text("ALTER TABLE nfr_rows_new RENAME TO nfr_rows"))
            finally:
                try:
                    if str(prev_fk) in ('1', 'ON'):
                        connection.execute(text('PRAGMA foreign_keys=ON'))
                    else:
                        connection.execute(text('PRAGMA foreign_keys=OFF'))
                except Exception:
                    pass
            log.info("Migration for 'nfr_rows' applied successfully.")
        except Exception as e:
            log.warning(f"Could not rebuild 'nfr_rows'. Error: {e}")


# Export list of migrations for this table
MIGRATIONS = [
    NFRRowsNormalize(),
]
