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
from app.backend.pydantic_models import GraphModel


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

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def save(cls, schema_name, data):
        try:
            instance = cls(**GraphModel(**data).model_dump())
            instance.__table__.schema = schema_name
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
            return [GraphModel(**config.to_dict()).model_dump() for config in query]
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_id(cls, schema_name, id):
        cls.__table__.schema = schema_name
        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            return GraphModel.model_validate(config.to_dict()).model_dump()
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def update(cls, schema_name, data):
        cls.__table__.schema = schema_name
        try:
            validated_data = GraphModel(**data)
            config         = db.session.query(cls).filter_by(id=validated_data.id).one_or_none()
            if config:
                for key, value in validated_data.model_dump().items():
                    setattr(config, key, value)

                db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def count(cls, schema_name):
        # Reset the schema context
        cls.__table__.schema = None
        # Set the new schema
        cls.__table__.schema = schema_name
        try:
            # Use the existing session instead of creating a scoped session
            # Flask-SQLAlchemy 3.x handles sessions differently
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
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise
