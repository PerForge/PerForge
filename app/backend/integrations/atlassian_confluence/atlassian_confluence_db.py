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
from app.backend.pydantic_models import AtlassianConfluenceModel


class DBAtlassianConfluence(db.Model):
    __tablename__ = 'atlassian_confluence'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id    = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    name          = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(120), nullable=False)
    token         = db.Column(db.Integer, db.ForeignKey('secrets.id', ondelete='SET NULL'))
    token_type    = db.Column(db.String(120), nullable=False)
    org_url       = db.Column(db.String(120), nullable=False)
    space_key     = db.Column(db.String(120), nullable=False)
    parent_id     = db.Column(db.String(120), nullable=False)
    is_default    = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def save(cls, project_id, data):
        try:
            data['project_id'] = project_id
            validated_data = AtlassianConfluenceModel(**data)
            instance = cls(**validated_data.model_dump())

            if instance.is_default:
                cls.reset_default_config(project_id)
            elif not cls.get_default_config(project_id):
                instance.is_default = True

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
            query = db.session.query(cls).filter_by(project_id=project_id).all()
            configs = [config.to_dict() for config in query]
            return [AtlassianConfluenceModel(**config).model_dump() for config in configs]
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_id(cls, project_id, id):
        try:
            config = db.session.query(cls).filter_by(project_id=project_id, id=id).one_or_none()
            if config:
                validated_data = AtlassianConfluenceModel(**config.to_dict())
                return validated_data.model_dump()
            return None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_default_config(cls, project_id, current_config_id=None):
        try:
            config = db.session.query(cls).filter_by(project_id=project_id, is_default=True).one_or_none()
            if config and config.id != current_config_id:
                validated_data = AtlassianConfluenceModel(**config.to_dict())
                return validated_data.model_dump()
            return None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def reset_default_config(cls, project_id):
        try:
            db.session.query(cls).filter_by(project_id=project_id).update({cls.is_default: False})
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def update(cls, project_id, data):
        try:
            data['project_id'] = project_id
            validated_data = AtlassianConfluenceModel(**data)
            config = db.session.query(cls).filter_by(project_id=project_id, id=validated_data.id).one_or_none()
            if validated_data.is_default:
                cls.reset_default_config(project_id)
            elif not cls.get_default_config(project_id, validated_data.id):
                validated_data.is_default = True

            for key, value in validated_data.model_dump().items():
                setattr(config, key, value)

            db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def count(cls, project_id):
        try:
            count = db.session.query(cls).filter_by(project_id=project_id).count()
            return count
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def delete(cls, project_id, id):
        try:
            config = db.session.query(cls).filter_by(project_id=project_id, id=id).one_or_none()
            if config:
                db.session.delete(config)
                db.session.commit()
                if config.is_default:
                    new_default_config = db.session.query(cls).filter_by(project_id=project_id).first()
                    if new_default_config:
                        new_default_config.is_default = True
                        db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise
