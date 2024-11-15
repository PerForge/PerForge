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

from app.config     import db
from sqlalchemy.exc import SQLAlchemyError


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

    def __init__(self, name, ai_provider, azure_url, api_version, ai_text_model, ai_image_model, token, temperature, is_default):
        self.name           = name
        self.ai_provider    = ai_provider
        self.azure_url      = azure_url
        self.api_version    = api_version
        self.ai_text_model  = ai_text_model
        self.ai_image_model = ai_image_model
        self.token          = token
        self.temperature    = temperature
        self.is_default     = is_default

    def to_dict(self):
        return {
            'id'            : self.id,
            'name'          : self.name,
            'ai_provider'   : self.ai_provider,
            'azure_url'     : self.azure_url,
            'api_version'   : self.api_version,
            'ai_text_model' : self.ai_text_model,
            'ai_image_model': self.ai_image_model,
            'token'         : self.token,
            'temperature'   : self.temperature,
            'is_default'    : self.is_default
        }

    def save(self, schema_name):
        self.__table__.schema = schema_name

        if self.is_default:
            self.reset_default_config(schema_name)
        elif not self.get_default_config(schema_name):
            self.is_default = True

        try:
            db.session.add(self)
            db.session.commit()
            return self.id
        except SQLAlchemyError:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_configs(cls, schema_name):
        cls.__table__.schema = schema_name

        try:
            query = db.session.query(cls).all()
            list  = [config.to_dict() for config in query]
            return list
        except SQLAlchemyError:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_id(cls, schema_name, id):
        cls.__table__.schema = schema_name

        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none().to_dict()
            return config
        except SQLAlchemyError:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_default_config(cls, schema_name):
        cls.__table__.schema = schema_name
        try:
            config = db.session.query(cls).filter_by(is_default=True).one_or_none().to_dict()
            return config
        except SQLAlchemyError:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def reset_default_config(cls, schema_name):
        cls.__table__.schema = schema_name

        try:
            db.session.query(cls).update({cls.is_default: False})
        except SQLAlchemyError:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def update(cls, schema_name, id, name, ai_provider, azure_url, api_version, ai_text_model, ai_image_model, token, temperature, is_default):
        cls.__table__.schema = schema_name

        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                if is_default:
                    cls.reset_default_config(schema_name)

                config.name           = name
                config.ai_provider    = ai_provider
                config.azure_url      = azure_url
                config.api_version    = api_version
                config.ai_text_model  = ai_text_model
                config.ai_image_model = ai_image_model
                config.token          = token
                config.temperature    = temperature
                config.is_default     = is_default

                db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def count(cls, schema_name):
        cls.__table__.schema = schema_name

        try:
            count = db.session.query(cls).count()
            return count
        except SQLAlchemyError:
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
        except SQLAlchemyError:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise