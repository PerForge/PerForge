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

import yaml
import os
import traceback
import logging

from app.config     import db
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy     import or_


class DBPrompts(db.Model):
    __tablename__  = 'prompts'
    __table_args__ = {'schema': 'public'}
    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name           = db.Column(db.String(120), nullable=False)
    type           = db.Column(db.String(120), nullable=False)
    place          = db.Column(db.String(120), nullable=False)
    prompt         = db.Column(db.Text, nullable=False)
    project_id     = db.Column(db.Integer, db.ForeignKey('public.projects.id', ondelete='CASCADE'))

    def __init__(self, name, type, place, prompt, project_id):
        self.name       = name
        self.type       = type
        self.place      = place
        self.prompt     = prompt
        self.project_id = project_id

    def to_dict(self):
        return {
            'id'        : self.id,
            'name'      : self.name,
            'type'      : self.type,
            'place'     : self.place,
            'prompt'    : self.prompt,
            'project_id': self.project_id
        }

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
            return self.id
        except SQLAlchemyError:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_configs(cls, project_id):
        try:
            default_query = db.session.query(cls).filter(cls.type == "default").all()
            custom_query  = db.session.query(cls).filter(
                cls.type == "custom",
                or_(cls.project_id == project_id, cls.project_id.is_(None))
            ).all()

            default_list = [config.to_dict() for config in default_query]
            custom_list  = [config.to_dict() for config in custom_query]

            return default_list, custom_list
        except SQLAlchemyError:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_configs_by_place(cls, project_id, place):
        try:
            query  = db.session.query(cls).filter(
                cls.place == place,
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
    def update(cls, id, name, type, place, prompt_text, project_id):
        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                config.name       = name
                config.type       = type
                config.place      = place
                config.prompt     = prompt_text
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

    @classmethod
    def load_default_prompts_from_yaml(cls):
        file_path = os.path.join("app", "data", "prompts.yaml")
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)

        for item in data.get('prompts', []):
            prompt = cls.query.get(item['id'])
            if prompt:
                prompt.name   = item['name']
                prompt.type   = item['type']
                prompt.place  = item['place']
                prompt.prompt = item['prompt']
            else:
                prompt = cls(
                    name       = item['name'],
                    project_id = None,
                    type       = item['type'],
                    place      = item['place'],
                    prompt     = item['prompt']
                )
                db.session.add(prompt)

        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise