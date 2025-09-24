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

import yaml
import os
import traceback
import logging

from app.config import db
from app.backend.pydantic_models import PromptModel
from sqlalchemy import or_

class DBPrompts(db.Model):
    __tablename__ = 'prompts'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(120), nullable=False)
    place = db.Column(db.String(120), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), index=True)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def save(cls, data):
        try:
            validated_data = PromptModel(**data)
            instance = cls(**validated_data.model_dump())
            db.session.add(instance)
            db.session.commit()
            return instance.id
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_configs(cls, project_id):
        try:
            default_query = db.session.query(cls).filter(cls.type == "default").all()
            custom_query = db.session.query(cls).filter(
                cls.type == "custom",
                or_(cls.project_id == project_id, cls.project_id.is_(None))
            ).all()
            default_configs = [PromptModel(**config.to_dict()).model_dump() for config in default_query]
            custom_configs = [PromptModel(**config.to_dict()).model_dump() for config in custom_query]
            return default_configs, custom_configs
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_configs_by_place(cls, project_id, place):
        try:
            query = db.session.query(cls).filter(
                cls.place == place,
                or_(cls.project_id == project_id, cls.project_id.is_(None))
            ).all()

            valid_configs = []
            for config in query:
                config_dict = config.to_dict()
                validated_data = PromptModel(**config_dict)
                valid_configs.append(validated_data.model_dump())
            return valid_configs
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_id(cls, project_id, id):
        try:
            config = db.session.query(cls).filter(
                cls.id == id,
                or_(cls.project_id == project_id, cls.project_id.is_(None))
            ).one_or_none()
            if config:
                validated_data = PromptModel(**config.to_dict())
                return validated_data.model_dump()
            return None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_id_by_name(cls, project_id, name, place=None):
        try:
            base_query = db.session.query(cls.id).filter(cls.name == name)
            if place is not None:
                base_query = base_query.filter(cls.place == place)

            # Prefer project-specific prompt first
            row = base_query.filter(cls.project_id == project_id).one_or_none()
            if row:
                return row[0]

            # Fallback to global prompt (project_id is NULL)
            row = base_query.filter(cls.project_id.is_(None)).one_or_none()
            if row:
                return row[0]

            return None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def update(cls, data):
        try:
            validated_data = PromptModel(**data)
            config = db.session.query(cls).filter_by(id=validated_data.id).one_or_none()
            if config:
                for key, value in validated_data.model_dump(exclude={'id'}).items():
                    setattr(config, key, value)
                db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def count(cls, project_id):
        try:
            count = db.session.query(cls).filter(
                or_(cls.project_id == project_id, cls.project_id.is_(None))
            ).count()
            return count
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def delete(cls, id):
        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                db.session.delete(config)
                db.session.commit()
                return True
            return False
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def load_default_prompts_from_yaml(cls):
        """
        Reset and load default INTERNAL prompts from YAML.

        - Upserts prompts with type == 'default' by unique name
        - Removes internal prompts not present in YAML
        - Loads prompts from app/backend/components/prompts/prompts.yaml
        - YAML ids are ignored; DB ids are preserved on update

        Returns: number of imported prompts (not currently returned)
        """
        try:
            file_path = os.path.join('app', 'backend', 'components', 'prompts', 'prompts.yaml')
            if not os.path.exists(file_path):
                logging.info(f"Prompts YAML not found at {file_path}; skipping import")
                db.session.commit()
                return 0

            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}

            # Prepare existing internal prompts keyed by name for upsert
            existing_prompts = db.session.query(cls).filter_by(type='default').all()
            existing_by_name = {p.name: p for p in existing_prompts}

            yaml_internal = [item for item in (data.get('prompts', []) or []) if item.get('type', 'default') == 'default']
            seen_names = set()
            created = 0
            updated = 0

            for item in yaml_internal:
                try:
                    name = item.get('name')
                    if not name:
                        continue
                    seen_names.add(name)
                    place = item.get('place')
                    prompt_text = item.get('prompt')

                    if name in existing_by_name:
                        p = existing_by_name[name]
                        p.place = place
                        p.prompt = prompt_text
                        updated += 1
                    else:
                        # Create new internal prompt (ID will be assigned, existing IDs preserved)
                        instance = cls(
                            name=name,
                            type='default',
                            place=place,
                            prompt=prompt_text,
                            project_id=None
                        )
                        db.session.add(instance)
                        created += 1
                except Exception:
                    logging.warning(f"Skipping prompt due to validation/persistence error: {traceback.format_exc()}")

            # Remove internal prompts that are not present in YAML
            removed = 0
            for p in existing_prompts:
                if p.name not in seen_names:
                    db.session.delete(p)
                    removed += 1

            db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise
