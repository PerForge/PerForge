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


class DBGraphs(db.Model):
    __tablename__ = 'graphs'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name          = db.Column(db.String(120), nullable=False)
    grafana_id    = db.Column(db.Integer, db.ForeignKey('grafana.id', ondelete='CASCADE'), nullable=False)
    dash_id       = db.Column(db.Integer, db.ForeignKey('grafana_dashboards.id', ondelete='CASCADE'), nullable=False)
    view_panel    = db.Column(db.Integer, nullable=False)
    width         = db.Column(db.Integer, nullable=False)
    height        = db.Column(db.Integer, nullable=False)
    custom_vars   = db.Column(db.String(500))
    prompt_id     = db.Column(db.Integer, db.ForeignKey('public.prompts.id', ondelete='SET NULL'))

    def __init__(self, name, grafana_id, dash_id, view_panel, width, height, custom_vars, prompt_id):
        self.name        = name
        self.grafana_id  = grafana_id
        self.dash_id     = dash_id
        self.view_panel  = view_panel
        self.width       = width
        self.height      = height
        self.custom_vars = custom_vars
        self.prompt_id   = prompt_id

    def to_dict(self):
        return {
            'id'         : self.id,
            'name'       : self.name,
            'grafana_id' : self.grafana_id,
            'dash_id'    : self.dash_id,
            'view_panel' : self.view_panel,
            'width'      : self.width,
            'height'     : self.height,
            'custom_vars': self.custom_vars,
            'prompt_id'  : self.prompt_id
        }

    def save(self, schema_name):
        self.__table__.schema = schema_name

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
    def update(cls, schema_name, id, name, grafana_id, dash_id, view_panel, width, height, custom_vars, prompt_id):
        cls.__table__.schema = schema_name

        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                config.name        = name
                config.grafana_id  = grafana_id
                config.dash_id     = dash_id
                config.view_panel  = view_panel
                config.width       = width
                config.height      = height
                config.custom_vars = custom_vars
                config.prompt_id   = prompt_id

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
            record = db.session.query(cls).filter_by(id=id).one_or_none()
            if record:
                db.session.delete(record)
                db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise