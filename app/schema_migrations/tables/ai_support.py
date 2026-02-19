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


class AddBaseUrlToAISupport(BaseMigration):
    """Add base_url column to ai_support table."""

    name = "ai_support: add base_url column"

    def apply(self, connection, inspector):
        table_name = 'ai_support'

        # Check if table exists
        if table_name not in inspector.get_table_names():
            return

        cols = [c['name'] for c in inspector.get_columns(table_name)]

        if 'base_url' not in cols:
            log.info(f"Applying migration: Adding 'base_url' column to '{table_name}'")
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN base_url VARCHAR(120)"))
        else:
            log.info(f"Column 'base_url' already exists in '{table_name}', skipping")


MIGRATIONS = [
    AddBaseUrlToAISupport(),
]
