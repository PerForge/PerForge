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
from app.backend.pydantic_models import TemplateModel
from sqlalchemy.orm              import joinedload


class DBTemplates(db.Model):
    __tablename__             = 'templates'
    id                        = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name                      = db.Column(db.String(120), nullable=False)
    nfr                       = db.Column(db.Integer, db.ForeignKey('nfrs.id', ondelete='SET NULL'))
    title                     = db.Column(db.String(120), nullable=False)
    ai_switch                 = db.Column(db.Boolean, default=False)
    ai_aggregated_data_switch = db.Column(db.Boolean, default=False)
    ai_graph_switch           = db.Column(db.Boolean, default=False)
    ai_to_graphs_switch       = db.Column(db.Boolean, default=False)
    nfrs_switch               = db.Column(db.Boolean, default=False)
    template_prompt_id        = db.Column(db.Integer, db.ForeignKey('public.prompts.id', ondelete='SET NULL'))
    aggregated_prompt_id      = db.Column(db.Integer, db.ForeignKey('public.prompts.id', ondelete='SET NULL'))
    system_prompt_id          = db.Column(db.Integer, db.ForeignKey('public.prompts.id', ondelete='SET NULL'))
    data                      = db.relationship('DBTemplateData', backref='templates', cascade='all, delete-orphan', lazy=True)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def save(cls, schema_name, data):
        try:
            validated_data            = TemplateModel(**data)
            instance                  = cls(**validated_data.model_dump(exclude={'data'}))
            instance.__table__.schema = schema_name

            for data_record in validated_data.data:
                data_dict = data_record.model_dump()
                record    = DBTemplateData(**data_dict)
                instance.data.append(record)

            db.session.add(instance)
            db.session.commit()
            return instance.id
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_configs(cls, schema_name):
        cls.__table__.schema            = schema_name
        DBTemplateData.__table__.schema = schema_name

        try:
            query = db.session.query(cls).options(joinedload(cls.data)).all()
            valid_configs = []
            for config in query:
                config_dict         = config.to_dict()
                config_dict['data'] = [row.to_dict() for row in config.data]
                validated_data      = TemplateModel(**config_dict)
                valid_configs.append(validated_data.model_dump())
            return valid_configs
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_id(cls, schema_name, id):
        cls.__table__.schema            = schema_name
        DBTemplateData.__table__.schema = schema_name

        try:
            config = db.session.query(cls).options(joinedload(cls.data)).filter_by(id=id).one_or_none()
            if config:
                config_dict         = config.to_dict()
                config_dict['data'] = [row.to_dict() for row in config.data]
                validated_data      = TemplateModel(**config_dict)
                return validated_data.model_dump()
            return None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def update(cls, schema_name, data):
        cls.__table__.schema            = schema_name
        DBTemplateData.__table__.schema = schema_name
        try:
            validated_data = TemplateModel(**data)
            config         = db.session.query(cls).filter_by(id=validated_data.id).one_or_none()
            exclude_fields = {'data'}

            for field, value in validated_data.model_dump().items():
                if field not in exclude_fields:
                    setattr(config, field, value)

            config.data.clear()
            for data_record in validated_data.data:
                data_dict = data_record.model_dump()
                record    = DBTemplateData(**data_dict)
                config.data.append(record)
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
        cls.__table__.schema            = schema_name
        DBTemplateData.__table__.schema = schema_name

        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                db.session.delete(config)
                db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise


class DBTemplateData(db.Model):
    __tablename__ = 'template_data'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type          = db.Column(db.String(120), nullable=False)
    content       = db.Column(db.Text)
    graph_id      = db.Column(db.Integer, db.ForeignKey('graphs.id', ondelete='CASCADE'))
    template_id   = db.Column(db.Integer, db.ForeignKey('templates.id', ondelete='CASCADE'), nullable=False)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}