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


class DBTemplateGroups(db.Model):
    __tablename__ = 'template_groups'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name          = db.Column(db.String(120), nullable=False)
    title         = db.Column(db.String(120), nullable=False)
    ai_summary    = db.Column(db.Boolean, default=False)
    prompt_id     = db.Column(db.Integer, db.ForeignKey('public.prompts.id', ondelete='SET NULL'))
    data          = db.relationship('DBTemplateGroupData', backref='template_groups', cascade='all, delete-orphan', lazy=True)

    def __init__(self, name, title, ai_summary, prompt_id, data):
        self.name       = name
        self.title      = title
        self.ai_summary = ai_summary
        self.prompt_id  = prompt_id
        self.data       = data

    def to_dict(self):
        return {
            'id'        : self.id,
            'name'      : self.name,
            'title'     : self.title,
            'ai_summary': self.ai_summary,
            'prompt_id' : self.prompt_id,
            'data'      : [record.to_dict() for record in self.data]
        }

    def save(self, schema_name):
        self.__table__.schema = schema_name
        for record in self.data:
            record.__table__.schema = schema_name

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
        cls.__table__.schema                 = schema_name
        DBTemplateGroupData.__table__.schema = schema_name

        try:
            query = db.session.query(cls).options(joinedload(cls.data)).all()
            list  = [config.to_dict() for config in query]
            return list
        except SQLAlchemyError:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_id(cls, schema_name, id):
        cls.__table__.schema                 = schema_name
        DBTemplateGroupData.__table__.schema = schema_name

        try:
            config = db.session.query(cls).options(joinedload(cls.data)).filter_by(id=id).one_or_none().to_dict()
            return config
        except SQLAlchemyError:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def update(cls, schema_name, id, name, title, ai_summary, prompt_id, data):
        cls.__table__.schema                 = schema_name
        DBTemplateGroupData.__table__.schema = schema_name

        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                config.name       = name
                config.title      = title
                config.ai_summary = ai_summary
                config.prompt_id  = prompt_id
                config.data.clear()

                for records_data in data:
                    record = DBTemplateGroupData(
                        type              = records_data['type'],
                        content           = records_data['content'],
                        template_id       = records_data['template_id'],
                        template_group_id = config.id
                    )
                    config.data.append(record)

                db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def delete(cls, schema_name, id):
        cls.__table__.schema                 = schema_name
        DBTemplateGroupData.__table__.schema = schema_name

        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                db.session.delete(config)
                db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise


class DBTemplateGroupData(db.Model):
    __tablename__     = 'template_group_data'
    id                = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type              = db.Column(db.String(120), nullable=False)
    content           = db.Column(db.Text)
    template_id       = db.Column(db.Integer, db.ForeignKey('templates.id', ondelete='CASCADE'))
    template_group_id = db.Column(db.Integer, db.ForeignKey('template_groups.id', ondelete='CASCADE'), nullable=False)

    def __init__(self, type, content, template_id, template_group_id):
        self.type              = type
        self.content           = content
        self.template_id       = template_id
        self.template_group_id = template_group_id

    def to_dict(self):
        return {
            'id'               : self.id,
            'type'             : self.type,
            'content'          : self.content,
            'template_id'      : self.template_id,
            'template_group_id': self.template_group_id
        }