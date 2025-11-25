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
import json
from sqlalchemy import text
from app.schema_migrations.base import BaseMigration

log = logging.getLogger("app.migrations")


class CreateProjectSettingsTable(BaseMigration):
    """Create project_settings table and populate default settings for existing projects."""

    name = "project_settings: create table and initialize defaults"

    def apply(self, connection, inspector):
        table_name = 'project_settings'

        # Check if table already exists
        if table_name in inspector.get_table_names():
            return

        log.info(f"Applying migration: Creating table '{table_name}'")

        # Create the table
        connection.execute(text(f"""
            CREATE TABLE {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                category VARCHAR(50) NOT NULL,
                key VARCHAR(100) NOT NULL,
                value TEXT NOT NULL,
                value_type VARCHAR(20) NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                CONSTRAINT uq_project_category_key UNIQUE (project_id, category, key)
            )
        """))

        # Create index for faster queries
        connection.execute(text(f"""
            CREATE INDEX idx_project_settings_project_category
            ON {table_name}(project_id, category)
        """))

        log.info(f"Table '{table_name}' created successfully")

        # Initialize default settings for all existing projects
        self._initialize_defaults_for_existing_projects(connection)

    def _initialize_defaults_for_existing_projects(self, connection):
        """Populate default settings for all existing projects."""

        # Import here to avoid circular dependencies during app startup
        from app.backend.components.settings.settings_defaults import get_all_defaults

        log.info("Initializing default settings for existing projects...")

        # Get all existing projects
        result = connection.execute(text("SELECT id, name FROM projects"))
        projects = result.fetchall()

        if not projects:
            log.info("No existing projects found, skipping default settings initialization")
            return

        log.info(f"Found {len(projects)} existing projects")

        # Get all default settings
        all_defaults = get_all_defaults()

        # Prepare batch insert data
        settings_to_insert = []

        for project in projects:
            project_id = project[0]
            project_name = project[1]

            for category, category_settings in all_defaults.items():
                for key, setting_config in category_settings.items():
                    value = setting_config['value']
                    value_type = setting_config['type']
                    description = setting_config.get('description', '')

                    # Serialize value based on type
                    if value_type in ('list', 'dict'):
                        serialized_value = json.dumps(value)
                    else:
                        serialized_value = str(value)

                    settings_to_insert.append({
                        'project_id': project_id,
                        'category': category,
                        'key': key,
                        'value': serialized_value,
                        'value_type': value_type,
                        'description': description
                    })

            log.info(f"  Prepared {len(all_defaults['ml_analysis']) + len(all_defaults['transaction_status']) + len(all_defaults['data_aggregation'])} settings for project '{project_name}' (ID: {project_id})")

        # Batch insert all settings
        if settings_to_insert:
            log.info(f"Inserting {len(settings_to_insert)} default settings...")

            connection.execute(
                text("""
                    INSERT INTO project_settings
                    (project_id, category, key, value, value_type, description)
                    VALUES
                    (:project_id, :category, :key, :value, :value_type, :description)
                """),
                settings_to_insert
            )

            log.info(f"✓ Successfully initialized default settings for {len(projects)} projects")
        else:
            log.info("No settings to insert")


# Export list of migrations for this table
MIGRATIONS = [
    CreateProjectSettingsTable(),
]
