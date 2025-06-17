# Copyright 2024 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>
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

import traceback
import logging

from app.config                  import db
from app.backend.pydantic_models import SecretsModel
from sqlalchemy                  import or_, UniqueConstraint


class DBSecrets(db.Model):

    __tablename__  = 'secrets'
    __table_args__ = (UniqueConstraint('key', 'project_id', name='_key_project_uc'),)

    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key            = db.Column(db.String(120), nullable=False)
    type           = db.Column(db.String(120), nullable=False)
    value          = db.Column(db.String(500), nullable=False)
    project_id     = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), index=True)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def save(cls, project_id, data):
        try:
            validated_data = SecretsModel(**data)
            instance = cls(**validated_data.model_dump(exclude={'project_id'}))
            instance.project_id = project_id
            db.session.add(instance)
            db.session.commit()
            return instance.key
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_configs(cls, project_id):
        try:
            query = db.session.query(cls).filter(
                or_(cls.project_id == project_id, cls.project_id.is_(None))
            ).all()
            valid_configs = []
            for config in query:
                config_dict = config.to_dict()
                validated_data = SecretsModel(**config_dict)
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
                config_dict = config.to_dict()
                validated_data = SecretsModel(**config_dict)
                return validated_data.model_dump()
            return None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_key(cls, project_id, key):
        try:
            # Prioritize project-specific secret over a global one
            config = db.session.query(cls).filter(
                cls.key == key,
                or_(cls.project_id == project_id, cls.project_id.is_(None))
            ).order_by(cls.project_id.desc()).first()
            if config:
                config_dict = config.to_dict()
                validated_data = SecretsModel(**config_dict)
                return validated_data.model_dump()
            return None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def update(cls, project_id, data):
        try:
            validated_data = SecretsModel(**data)
            config = db.session.query(cls).filter_by(id=validated_data.id, project_id=project_id).one_or_none()
            if config:
                # Exclude id and project_id from being updated
                for key, value in validated_data.model_dump(exclude={'id', 'project_id'}).items():
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
    def delete(cls, project_id, id):
        try:
            # Only allow deleting secrets that belong to the project
            config = db.session.query(cls).filter_by(id=id, project_id=project_id).one_or_none()
            if config:
                db.session.delete(config)
                db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise
