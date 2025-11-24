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

"""
Settings Service - Centralized service for managing project settings with caching.

This service provides a high-level interface for retrieving and managing project settings,
with built-in caching to minimize database queries.
"""

import logging
from typing import Dict, Any, Optional, List

from app.backend.components.settings.settings_db import DBProjectSettings
from app.backend.components.settings.settings_defaults import (
    get_all_defaults,
    get_defaults_for_category,
    ML_ANALYSIS_DEFAULTS,
    TRANSACTION_STATUS_DEFAULTS,
    DATA_AGGREGATION_DEFAULTS
)


class SettingsService:
    """Service for managing project settings with caching."""

    # Cache structure: {project_id: {category: {key: value}}}
    _cache: Dict[int, Dict[str, Dict[str, Any]]] = {}

    @classmethod
    def get_defaults(cls) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Get all default settings with metadata.

        Returns:
            Dictionary organized as {category: {key: {value, type, description, ...}}}
        """
        return get_all_defaults()

    @classmethod
    def get_project_settings(cls, project_id: int, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Get settings for a project, optionally filtered by category.
        Uses cache if available, otherwise loads from database.

        Args:
            project_id: ID of the project
            category: Optional category filter ('ml_analysis', 'transaction_status', 'data_aggregation')

        Returns:
            Dictionary of settings {key: value} or {category: {key: value}} if no category specified
        """
        # Load all settings for project into cache if not present
        if project_id not in cls._cache:
            cls._load_project_settings(project_id)

        cached_settings = cls._cache.get(project_id, {})

        if category:
            # Return settings for specific category
            return cached_settings.get(category, {})
        else:
            # Return all settings organized by category
            return cached_settings

    @classmethod
    def get_setting(cls, project_id: int, category: str, key: str, default: Any = None) -> Any:
        """
        Get a single setting value.

        Args:
            project_id: ID of the project
            category: Setting category
            key: Setting key
            default: Default value if setting not found

        Returns:
            Setting value or default if not found
        """
        category_settings = cls.get_project_settings(project_id, category)
        return category_settings.get(key, default)

    @classmethod
    def update_setting(cls, project_id: int, category: str, key: str, value: Any) -> None:
        """
        Update a single setting.

        Args:
            project_id: ID of the project
            category: Setting category
            key: Setting key
            value: New value
        """
        # Get setting metadata from defaults to determine type
        defaults = get_defaults_for_category(category)
        setting_metadata = defaults.get(key, {})
        value_type = setting_metadata.get('type', 'string')
        description = setting_metadata.get('description', '')

        # Prepare data for database
        data = {
            'project_id': project_id,
            'category': category,
            'key': key,
            'value': value,
            'value_type': value_type,
            'description': description
        }

        # Check if setting exists
        existing = DBProjectSettings.get_setting(project_id, category, key)

        if existing is not None:
            # Update existing
            DBProjectSettings.update(data)
        else:
            # Create new
            DBProjectSettings.save(data)

        # Invalidate cache for this project
        cls.clear_cache(project_id)

    @classmethod
    def update_category_settings(cls, project_id: int, category: str, settings: Dict[str, Any]) -> None:
        """
        Update multiple settings within a category.

        Args:
            project_id: ID of the project
            category: Setting category
            settings: Dictionary of {key: value} pairs to update
        """
        defaults = get_defaults_for_category(category)

        for key, value in settings.items():
            setting_metadata = defaults.get(key, {})
            value_type = setting_metadata.get('type', 'string')
            description = setting_metadata.get('description', '')

            data = {
                'project_id': project_id,
                'category': category,
                'key': key,
                'value': value,
                'value_type': value_type,
                'description': description
            }

            existing = DBProjectSettings.get_setting(project_id, category, key)

            if existing is not None:
                DBProjectSettings.update(data)
            else:
                DBProjectSettings.save(data)

        # Invalidate cache
        cls.clear_cache(project_id)

    @classmethod
    def initialize_project_settings(cls, project_id: int) -> None:
        """
        Initialize default settings for a new project.

        Args:
            project_id: ID of the newly created project
        """
        all_defaults = get_all_defaults()
        settings_to_save = []

        for category, category_settings in all_defaults.items():
            for key, setting_config in category_settings.items():
                settings_to_save.append({
                    'project_id': project_id,
                    'category': category,
                    'key': key,
                    'value': setting_config['value'],
                    'value_type': setting_config['type'],
                    'description': setting_config.get('description', '')
                })

        # Bulk save all default settings
        if settings_to_save:
            DBProjectSettings.bulk_save(settings_to_save)
            logging.info(f"Initialized {len(settings_to_save)} default settings for project {project_id}")

    @classmethod
    def reset_to_defaults(cls, project_id: int, category: Optional[str] = None) -> None:
        """
        Reset settings to defaults for a project.

        Args:
            project_id: ID of the project
            category: Optional category to reset (if None, resets all categories)
        """
        if category:
            # Reset specific category
            DBProjectSettings.delete_project_settings(project_id, category)
            defaults = get_defaults_for_category(category)

            settings_to_save = []
            for key, setting_config in defaults.items():
                settings_to_save.append({
                    'project_id': project_id,
                    'category': category,
                    'key': key,
                    'value': setting_config['value'],
                    'value_type': setting_config['type'],
                    'description': setting_config.get('description', '')
                })

            if settings_to_save:
                DBProjectSettings.bulk_save(settings_to_save)
        else:
            # Reset all categories
            DBProjectSettings.delete_project_settings(project_id)
            cls.initialize_project_settings(project_id)

        # Clear cache
        cls.clear_cache(project_id)
        logging.info(f"Reset settings to defaults for project {project_id}, category: {category or 'all'}")

    @classmethod
    def clear_cache(cls, project_id: Optional[int] = None) -> None:
        """
        Clear settings cache.

        Args:
            project_id: Optional project ID to clear cache for (if None, clears all cache)
        """
        if project_id is not None:
            if project_id in cls._cache:
                del cls._cache[project_id]
                logging.debug(f"Cleared settings cache for project {project_id}")
        else:
            cls._cache.clear()
            logging.debug("Cleared all settings cache")

    @classmethod
    def get_settings_with_metadata(cls, project_id: int, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Get settings along with their metadata (type, description, constraints).
        Useful for UI rendering.

        Args:
            project_id: ID of the project
            category: Optional category filter

        Returns:
            Dictionary with settings and their full metadata
        """
        current_settings = cls.get_project_settings(project_id, category)
        defaults = get_all_defaults()

        result = {}

        if category:
            # Single category
            category_defaults = defaults.get(category, {})
            result[category] = {}

            for key, setting_config in category_defaults.items():
                result[category][key] = {
                    'value': current_settings.get(key, setting_config['value']),
                    'type': setting_config['type'],
                    'description': setting_config.get('description', ''),
                    'min': setting_config.get('min'),
                    'max': setting_config.get('max'),
                    'options': setting_config.get('options'),
                    'default': setting_config['value']
                }
        else:
            # All categories
            for cat, cat_defaults in defaults.items():
                result[cat] = {}
                cat_settings = current_settings.get(cat, {})

                for key, setting_config in cat_defaults.items():
                    result[cat][key] = {
                        'value': cat_settings.get(key, setting_config['value']),
                        'type': setting_config['type'],
                        'description': setting_config.get('description', ''),
                        'min': setting_config.get('min'),
                        'max': setting_config.get('max'),
                        'options': setting_config.get('options'),
                        'default': setting_config['value']
                    }

        return result

    @classmethod
    def _load_project_settings(cls, project_id: int) -> None:
        """
        Load settings from database into cache.
        Merges with defaults for any missing settings.

        Args:
            project_id: ID of the project
        """
        # Get settings from database
        db_settings = DBProjectSettings.get_project_settings(project_id)

        # Organize by category
        organized_settings: Dict[str, Dict[str, Any]] = {}
        for setting in db_settings:
            category = setting['category']
            key = setting['key']
            value = setting['value']

            if category not in organized_settings:
                organized_settings[category] = {}

            organized_settings[category][key] = value

        # Merge with defaults for any missing settings
        all_defaults = get_all_defaults()
        for category, category_defaults in all_defaults.items():
            if category not in organized_settings:
                organized_settings[category] = {}

            for key, setting_config in category_defaults.items():
                if key not in organized_settings[category]:
                    # Use default value if not in database
                    organized_settings[category][key] = setting_config['value']

        # Store in cache
        cls._cache[project_id] = organized_settings
        logging.debug(f"Loaded settings for project {project_id} into cache")
