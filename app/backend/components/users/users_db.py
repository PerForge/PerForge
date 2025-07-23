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

import traceback
import logging

from app.config                  import db
from app.backend.pydantic_models import UsersModel
from flask_login                 import UserMixin


class DBUsers(db.Model, UserMixin):

    __tablename__  = 'users'
    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user           = db.Column(db.String(120), unique=True, nullable=False)
    password       = db.Column(db.String(500), nullable=False)
    is_admin       = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def save(cls, data):
        try:
            validated_data = UsersModel(**data)
            instance = cls(**validated_data.model_dump())
            db.session.add(instance)
            db.session.commit()
            return instance.id
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def check_admin_exists(cls):
        try:
            admin_user = db.session.query(cls).filter_by(is_admin=True).one_or_none()
            if admin_user:
                return True
            else:
                return False
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_id(cls, id):
        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                config_dict = config.to_dict()
                validated_data = UsersModel(**config_dict)
                return validated_data.model_dump()
            return None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_username(cls, user):
        try:
            config = db.session.query(cls).filter_by(user=user).one_or_none()
            if config:
                config_dict = config.to_dict()
                validated_data = UsersModel(**config_dict)
                return validated_data.model_dump()
            return None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise
