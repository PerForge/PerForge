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
from sqlalchemy import inspect
from app.config import db
from app.schema_migrations.registry import MIGRATIONS

log = logging.getLogger(__name__)


class MigrationRunner:
    """Base migration orchestrator that runs all registered migrations in order."""

    def run(self):
        try:
            with db.engine.connect() as connection:
                # Apply ordered migration units from registry
                for migration in MIGRATIONS:
                    try:
                        # Create a fresh inspector for each migration to avoid stale cache
                        inspector = inspect(connection)
                        migration.apply(connection, inspector)
                        # In SQLAlchemy 2.x, DDL starts an implicit transaction (autobegin).
                        # If migrations don't manage their own transaction, commit here so changes persist.
                        if connection.in_transaction():
                            connection.commit()
                    except Exception as e:
                        migration_name = getattr(migration, 'name', migration.__class__.__name__)
                        log.warning(f"Migration '{migration_name}' failed: {e}")

        except Exception as e:
            # If the table doesn't exist yet, inspector will fail. This is okay
            # because create_all() will create it with all columns anyway.
            log.warning(f"Could not run migrations, likely because tables do not exist yet. Error: {e}")
