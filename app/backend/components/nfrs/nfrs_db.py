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
from sqlalchemy.orm import joinedload


class DBNFRs(db.Model):
    __tablename__ = 'nfrs'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name          = db.Column(db.String(120), nullable=False)
    rows          = db.relationship('DBNFRRows', backref='nfrs', cascade='all, delete-orphan', lazy=True)

    def __init__(self, name, rows):
        self.name = name
        self.rows = rows

    def to_dict(self):
        return {
            'id'  : self.id,
            'name': self.name,
            'rows': [row.to_dict() for row in self.rows]
        }

    def save(self, schema_name):
        self.__table__.schema = schema_name
        for row in self.rows:
            row.__table__.schema = schema_name

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
        cls.__table__.schema       = schema_name
        DBNFRRows.__table__.schema = schema_name

        try:
            query = db.session.query(cls).options(joinedload(cls.rows)).all()
            list  = [config.to_dict() for config in query]
            return list
        except SQLAlchemyError:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_id(cls, schema_name, id):
        cls.__table__.schema       = schema_name
        DBNFRRows.__table__.schema = schema_name

        try:
            config = db.session.query(cls).options(joinedload(cls.rows)).filter_by(id=id).one_or_none().to_dict()
            return config
        except SQLAlchemyError:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def update(cls, schema_name, id, name, rows):
        cls.__table__.schema       = schema_name
        DBNFRRows.__table__.schema = schema_name

        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                config.name = name
                config.rows.clear()

                for row_data in rows:
                    row = DBNFRRows(
                        regex     = row_data['regex'],
                        scope     = row_data['scope'],
                        metric    = row_data['metric'],
                        operation = row_data['operation'],
                        threshold = row_data['threshold'],
                        weight    = row_data['weight'] if row_data['weight'] else None,
                        nfr_id    = config.id
                    )
                    config.rows.append(row)

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
        cls.__table__.schema       = schema_name
        DBNFRRows.__table__.schema = schema_name

        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                db.session.delete(config)
                db.session.commit()
        except SQLAlchemyError:
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

    def __init__(self, regex, scope, metric, operation, threshold, weight, nfr_id):
        self.regex     = regex
        self.scope     = scope
        self.metric    = metric
        self.operation = operation
        self.threshold = threshold
        self.weight    = weight
        self.nfr_id    = nfr_id

    def to_dict(self):
        return {
            'id'       : self.id,
            'regex'    : self.regex,
            'scope'    : self.scope,
            'metric'   : self.metric,
            'operation': self.operation,
            'threshold': self.threshold,
            'weight'   : self.weight,
            'nfr_id'   : self.nfr_id
        }