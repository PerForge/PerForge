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

import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config import db
from app.backend.pydantic_models import SettingModel


class DBProjectSettings(db.Model):
    """Database model for storing project-specific settings."""

    __tablename__ = 'project_settings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Text, nullable=False)
    value_type = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('project_id', 'category', 'key', name='uq_project_category_key'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'category': self.category,
            'key': self.key,
            'value': self.value,
            'value_type': self.value_type,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def get_parsed_value(self) -> Any:
        """Parse the stored value based on its type."""
        try:
            if self.value_type == 'int':
                return int(self.value)
            elif self.value_type == 'float':
                return float(self.value)
            elif self.value_type == 'bool':
                return self.value.lower() in ('true', '1', 'yes')
            elif self.value_type == 'list':
                return json.loads(self.value)
            elif self.value_type == 'dict':
                return json.loads(self.value)
            else:  # string
                return self.value
        except (ValueError, json.JSONDecodeError) as e:
            logging.error(f"Error parsing value for {self.category}.{self.key}: {e}")
            return self.value

    @classmethod
    def save(cls, data: Dict[str, Any]) -> int:
        """
        Save a new setting to the database.

        Args:
            data: Dictionary containing setting data

        Returns:
            ID of the created setting
        """
        try:
            validated_data = SettingModel(**data)

            # Serialize value based on type
            serialized_value = cls._serialize_value(
                validated_data.value,
                validated_data.value_type
            )

            instance = cls(
                project_id=validated_data.project_id,
                category=validated_data.category,
                key=validated_data.key,
                value=serialized_value,
                value_type=validated_data.value_type,
                description=validated_data.description
            )

            db.session.add(instance)
            db.session.commit()
            return instance.id
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def update(cls, data: Dict[str, Any]) -> None:
        """
        Update an existing setting.

        Args:
            data: Dictionary containing updated setting data
        """
        try:
            validated_data = SettingModel(**data)
            setting = db.session.query(cls).filter_by(
                project_id=validated_data.project_id,
                category=validated_data.category,
                key=validated_data.key
            ).one_or_none()

            if setting:
                setting.value = cls._serialize_value(
                    validated_data.value,
                    validated_data.value_type
                )
                setting.value_type = validated_data.value_type
                setting.description = validated_data.description
                setting.updated_at = datetime.utcnow()
                db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_project_settings(cls, project_id: int, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all settings for a project, optionally filtered by category.

        Args:
            project_id: ID of the project
            category: Optional category filter

        Returns:
            List of setting dictionaries
        """
        try:
            query = db.session.query(cls).filter_by(project_id=project_id)

            if category:
                query = query.filter_by(category=category)

            settings = query.all()
            return [
                {
                    'category': s.category,
                    'key': s.key,
                    'value': s.get_parsed_value(),
                    'value_type': s.value_type,
                    'description': s.description,
                    'updated_at': s.updated_at.isoformat() if s.updated_at else None
                }
                for s in settings
            ]
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_setting(cls, project_id: int, category: str, key: str) -> Optional[Any]:
        """
        Get a single setting value.

        Args:
            project_id: ID of the project
            category: Setting category
            key: Setting key

        Returns:
            Parsed value or None if not found
        """
        try:
            setting = db.session.query(cls).filter_by(
                project_id=project_id,
                category=category,
                key=key
            ).one_or_none()

            return setting.get_parsed_value() if setting else None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            return None

    @classmethod
    def delete_project_settings(cls, project_id: int, category: Optional[str] = None) -> None:
        """
        Delete settings for a project.

        Args:
            project_id: ID of the project
            category: Optional category filter
        """
        try:
            query = db.session.query(cls).filter_by(project_id=project_id)

            if category:
                query = query.filter_by(category=category)

            query.delete()
            db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def bulk_save(cls, settings: List[Dict[str, Any]]) -> None:
        """
        Bulk save multiple settings.

        Args:
            settings: List of setting dictionaries
        """
        try:
            instances = []
            for data in settings:
                validated_data = SettingModel(**data)
                serialized_value = cls._serialize_value(
                    validated_data.value,
                    validated_data.value_type
                )

                instance = cls(
                    project_id=validated_data.project_id,
                    category=validated_data.category,
                    key=validated_data.key,
                    value=serialized_value,
                    value_type=validated_data.value_type,
                    description=validated_data.description
                )
                instances.append(instance)

            db.session.bulk_save_objects(instances)
            db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @staticmethod
    def _serialize_value(value: Any, value_type: str) -> str:
        """Serialize value to string based on type."""
        if value_type in ('list', 'dict'):
            return json.dumps(value)
        else:
            return str(value)
