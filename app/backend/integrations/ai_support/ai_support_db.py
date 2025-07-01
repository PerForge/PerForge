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
from app.backend.pydantic_models import AISupportModel


class DBAISupport(db.Model):
    __tablename__  = 'ai_support'
    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id     = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    name           = db.Column(db.String(120), nullable=False)
    ai_provider    = db.Column(db.String(120), nullable=False)
    azure_url      = db.Column(db.String(120))
    api_version    = db.Column(db.String(120))
    ai_text_model  = db.Column(db.String(120), nullable=False)
    ai_image_model = db.Column(db.String(120), nullable=False)
    token          = db.Column(db.Integer, db.ForeignKey('secrets.id', ondelete='SET NULL'))
    temperature    = db.Column(db.Float, nullable=False)
    is_default     = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def save(cls, project_id, data):
        try:
            data['project_id'] = project_id
            validated_data = AISupportModel(**data)
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
            valid_configs = []
            for config in query:
                config_dict    = config.to_dict()
                validated_data = AISupportModel(**config_dict)
                valid_configs.append(validated_data.model_dump())
            return valid_configs
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_id(cls, project_id, id):
        try:
            config = db.session.query(cls).filter_by(project_id=project_id, id=id).one_or_none()
            if config:
                config_dict    = config.to_dict()
                validated_data = AISupportModel(**config_dict)
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
                config_dict    = config.to_dict()
                validated_data = AISupportModel(**config_dict)
                return validated_data.model_dump()
            return None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def reset_default_config(cls, project_id):
        try:
            db.session.query(cls).filter_by(project_id=project_id).update({cls.is_default: False})
            db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def update(cls, project_id, data):
        try:
            data['project_id'] = project_id
            validated_data = AISupportModel(**data)
            config = db.session.query(cls).filter_by(project_id=project_id, id=validated_data.id).one_or_none()
            if not config:
                return

            if validated_data.is_default:
                cls.reset_default_config(project_id)
            elif not cls.get_default_config(project_id, validated_data.id):
                validated_data.is_default = True

            for key, value in validated_data.model_dump(exclude={'project_id'}).items():
                setattr(config, key, value)

            db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def count(cls, project_id):
        try:
            return db.session.query(cls).filter_by(project_id=project_id).count()
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def delete(cls, project_id, id):
        try:
            config = db.session.query(cls).filter_by(project_id=project_id, id=id).one_or_none()
            if config:
                is_default_deleted = config.is_default
                db.session.delete(config)
                db.session.commit()
                if is_default_deleted:
                    new_default_config = db.session.query(cls).filter_by(project_id=project_id).first()
                    if new_default_config:
                        new_default_config.is_default = True
                        db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise
