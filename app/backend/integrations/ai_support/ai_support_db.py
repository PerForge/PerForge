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
    name           = db.Column(db.String(120), nullable=False)
    ai_provider    = db.Column(db.String(120), nullable=False)
    azure_url      = db.Column(db.String(120))
    api_version    = db.Column(db.String(120))
    ai_text_model  = db.Column(db.String(120), nullable=False)
    ai_image_model = db.Column(db.String(120), nullable=False)
    token          = db.Column(db.Integer, db.ForeignKey('public.secrets.id', ondelete='SET NULL'))
    temperature    = db.Column(db.Float, nullable=False)
    is_default     = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def save(cls, schema_name, data):
        try:
            validated_data = AISupportModel(**data)
            instance = cls(**validated_data.model_dump())
            instance.__table__.schema = schema_name

            if instance.is_default:
                cls.reset_default_config(schema_name)
            elif not cls.get_default_config(schema_name):
                instance.is_default = True

            db.session.add(instance)
            db.session.commit()
            return instance.id
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_configs(cls, schema_name):
        cls.__table__.schema = schema_name
        try:
            query = db.session.query(cls).all()
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
    def get_config_by_id(cls, schema_name, id):
        cls.__table__.schema = schema_name
        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                config_dict    = config.to_dict()
                validated_data = AISupportModel(**config_dict)
                return validated_data.model_dump()
            return None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_default_config(cls, schema_name):
        cls.__table__.schema = schema_name
        try:
            config = db.session.query(cls).filter_by(is_default=True).one_or_none()
            if config:
                config_dict    = config.to_dict()
                validated_data = AISupportModel(**config_dict)
                return validated_data.model_dump()
            return None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def reset_default_config(cls, schema_name):
        cls.__table__.schema = schema_name

        try:
            db.session.query(cls).update({cls.is_default: False})
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def update(cls, schema_name, data):
        cls.__table__.schema = schema_name
        try:
            validated_data = AISupportModel(**data)
            config         = db.session.query(cls).filter_by(id=validated_data.id).one_or_none()
            if validated_data.is_default:
                cls.reset_default_config(schema_name)

            for key, value in validated_data.model_dump().items():
                setattr(config, key, value)

            db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def count(cls, schema_name):
        cls.__table__.schema = schema_name

        try:
            count = db.session.query(cls).count()
            return count
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def delete(cls, schema_name, id):
        cls.__table__.schema = schema_name

        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                db.session.delete(config)
                db.session.commit()
                if config.is_default:
                    new_default_config = db.session.query(cls).first()
                    if new_default_config:
                        new_default_config.is_default = True
                        db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise
