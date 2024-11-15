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
from sqlalchemy     import or_


class DBSecrets(db.Model):

    __tablename__  = 'secrets'
    __table_args__ = {'schema': 'public'}
    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key            = db.Column(db.String(120), unique=True, nullable=False)
    type           = db.Column(db.String(120), nullable=False)
    value          = db.Column(db.String(500), nullable=False)
    project_id     = db.Column(db.Integer, db.ForeignKey('public.projects.id', ondelete='CASCADE'))

    def __init__(self, key, type, value, project_id):
        self.key        = key
        self.type       = type
        self.value      = value
        self.project_id = project_id

    def to_dict(self):
        return {
            'id'        : self.id,
            'key'       : self.key,
            'type'      : self.type,
            'value'     : self.value,
            'project_id': self.project_id
        }

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
            return self.key
        except SQLAlchemyError:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_configs(cls, project_id):
        try:
            query = db.session.query(cls).filter(
                or_(cls.project_id == project_id, cls.project_id.is_(None))
            ).all()
            list = [config.to_dict() for config in query]
            return list
        except SQLAlchemyError:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_id(cls, id):
        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none().to_dict()
            return config
        except SQLAlchemyError:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_key(cls, key):
        try:
            config = db.session.query(cls).filter_by(key=key).one_or_none().to_dict()
            return config
        except SQLAlchemyError:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def update(cls, id, key, type, value, project_id):
        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                config.key        = key
                config.type       = type
                config.value      = value
                config.project_id = project_id
                db.session.commit()
        except SQLAlchemyError:
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
        except SQLAlchemyError:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def delete(cls, id):
        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                db.session.delete(config)
                db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise