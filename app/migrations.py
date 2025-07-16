import logging
from sqlalchemy import inspect, text
from app.config import db

log = logging.getLogger(__name__)

def run_migrations():
    try:
        with db.engine.connect() as connection:
            inspector = inspect(db.engine)

            # --- Migration 1: Add 'ml_switch' to 'templates' table ---
            table_name = 'templates'
            column_name = 'ml_switch'
            columns = [c['name'] for c in inspector.get_columns(table_name)]

            if column_name not in columns:
                log.info(f"Applying migration: Adding column '{column_name}' to table '{table_name}'")
                # Use server_default to handle existing rows without issues.
                alter_command = text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} BOOLEAN DEFAULT FALSE")
                connection.execute(alter_command)
                log.info(f"Migration for '{column_name}' applied successfully.")

            # --- Migration 2: Drop 'type' column from 'secrets' table ---
            table_name = 'secrets'
            column_name = 'type'
            columns = [c['name'] for c in inspector.get_columns(table_name)]

            if column_name in columns:
                log.info(f"Applying migration: Dropping column '{column_name}' from table '{table_name}'")
                alter_command = text(f"ALTER TABLE {table_name} DROP COLUMN {column_name}")
                connection.execute(alter_command)
                log.info(f"Migration for dropping '{column_name}' applied successfully.")

            # --- Migration 3: Add 'conversation_memory' to 'ai_support' table ---
            table_name = 'ai_support'
            column_name = 'conversation_memory'
            columns = [c['name'] for c in inspector.get_columns(table_name)]

            if column_name not in columns:
                log.info(f"Applying migration: Adding column '{column_name}' to table '{table_name}'")
                alter_command = text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} BOOLEAN DEFAULT FALSE")
                connection.execute(alter_command)
                log.info(f"Migration for '{column_name}' applied successfully.")

            # --- Add future migrations below this line as new blocks ---

            # --- Migration 4: Drop 'app' from 'grafana' table ---
            table_name = 'grafana'
            column_name = 'app'
            columns = [c['name'] for c in inspector.get_columns(table_name)]

            if column_name in columns:
                log.info(f"Applying migration: Dropping column '{column_name}' from table '{table_name}'")
                alter_command = text(f"ALTER TABLE {table_name} DROP COLUMN {column_name}")
                connection.execute(alter_command)
                log.info(f"Migration for dropping '{column_name}' applied successfully.")

    except Exception as e:
        # If the table doesn't exist yet, inspector will fail. This is okay
        # because create_all() will create it with all columns anyway.
        log.warning(f"Could not run migrations, likely because tables do not exist yet. Error: {e}")
