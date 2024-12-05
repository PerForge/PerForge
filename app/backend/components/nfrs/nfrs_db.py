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
from app.backend.pydantic_models import NFRsModel
from sqlalchemy.orm              import joinedload


class DBNFRs(db.Model):
    __tablename__ = 'nfrs'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name          = db.Column(db.String(120), nullable=False)
    rows          = db.relationship('DBNFRRows', backref='nfrs', cascade='all, delete-orphan', lazy=True)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def save(cls, schema_name, data):
        try:
            validated_data            = NFRsModel(**data)
            instance                  = cls(**validated_data.model_dump(exclude={'rows'}))
            instance.__table__.schema = schema_name

            for row_data in validated_data.rows:
                row_dict = row_data.model_dump()
                row      = DBNFRRows(**row_dict)
                instance.rows.append(row)

            db.session.add(instance)
            db.session.commit()
            return instance.id
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_configs(cls, schema_name):
        cls.__table__.schema       = schema_name
        DBNFRRows.__table__.schema = schema_name
        try:
            query         = db.session.query(cls).options(joinedload(cls.rows)).all()
            valid_configs = []

            for config in query:
                config_dict         = config.to_dict()
                config_dict['rows'] = [row.to_dict() for row in config.rows]
                validated_data      = NFRsModel(**config_dict)
                valid_configs.append(validated_data.model_dump())
            return valid_configs
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_id(cls, schema_name, id):
        cls.__table__.schema       = schema_name
        DBNFRRows.__table__.schema = schema_name
        try:
            config              = db.session.query(cls).options(joinedload(cls.rows)).filter_by(id=id).one_or_none()
            config_dict         = config.to_dict()
            config_dict['rows'] = [row.to_dict() for row in config.rows]
            validated_data      = NFRsModel(**config_dict)
            return validated_data.model_dump()
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def update(cls, schema_name, data):
        cls.__table__.schema       = schema_name
        DBNFRRows.__table__.schema = schema_name
        try:
            validated_data = NFRsModel(**data)
            config         = db.session.query(cls).filter_by(id=validated_data.id).one_or_none()
            exclude_fields = {'rows'}

            for field, value in validated_data.model_dump().items():
                if field not in exclude_fields:
                    setattr(config, field, value)

            config.rows.clear()
            for row_data in validated_data.rows:
                row_dict = row_data.model_dump()
                row      = DBNFRRows(**row_dict)
                config.rows.append(row)
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
        cls.__table__.schema       = schema_name
        DBNFRRows.__table__.schema = schema_name
        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                db.session.delete(config)
                db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise


class DBNFRRows(db.Model):
    __tablename__ = 'nfr_rows'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    regex         = db.Column(db.Boolean, default=False)
    scope         = db.Column(db.String(500), nullable=False)
    metric        = db.Column(db.String(120), nullable=False)
    operation     = db.Column(db.String(120), nullable=False)
    threshold     = db.Column(db.Integer, nullable=False)
    weight        = db.Column(db.Integer)
    nfr_id        = db.Column(db.Integer, db.ForeignKey('nfrs.id', ondelete='CASCADE'), nullable=False)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}