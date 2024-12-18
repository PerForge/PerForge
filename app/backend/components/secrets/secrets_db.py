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
from sqlalchemy                  import or_


class DBSecrets(db.Model):

    __tablename__  = 'secrets'
    __table_args__ = {'schema': 'public'}
    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key            = db.Column(db.String(120), unique=True, nullable=False)
    type           = db.Column(db.String(120), nullable=False)
    value          = db.Column(db.String(500), nullable=False)
    project_id     = db.Column(db.Integer, db.ForeignKey('public.projects.id', ondelete='CASCADE'))

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def save(cls, data):
        try:
            validated_data = SecretsModel(**data)
            instance       = cls(**validated_data.model_dump())
            db.session.add(instance)
            db.session.commit()
            return instance.key
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_configs(cls, id):
        try:
            query = db.session.query(cls).filter(
                or_(cls.project_id == id, cls.project_id.is_(None))
            ).all()
            valid_configs = []
            for config in query:
                config_dict    = config.to_dict()
                validated_data = SecretsModel(**config_dict)
                valid_configs.append(validated_data.model_dump())
            return valid_configs
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_id(cls, id):
        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                config_dict    = config.to_dict()
                validated_data = SecretsModel(**config_dict)
                return validated_data.model_dump()
            return None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_key(cls, key):
        try:
            config = db.session.query(cls).filter_by(key=key).one_or_none()
            if config:
                config_dict    = config.to_dict()
                validated_data = SecretsModel(**config_dict)
                return validated_data.model_dump()
            return None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def update(cls, data):
        try:
            validated_data = SecretsModel(**data)
            config         = db.session.query(cls).filter_by(id=validated_data.id).one_or_none()
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
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise
