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

from app.config     import db
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload


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

    def __init__(self, name, nfr, title, ai_switch, ai_aggregated_data_switch, ai_graph_switch, ai_to_graphs_switch, nfrs_switch, template_prompt_id, aggregated_prompt_id, system_prompt_id, data):
        self.name                      = name
        self.nfr                       = nfr
        self.title                     = title
        self.ai_switch                 = ai_switch
        self.ai_aggregated_data_switch = ai_aggregated_data_switch
        self.ai_graph_switch           = ai_graph_switch
        self.ai_to_graphs_switch       = ai_to_graphs_switch
        self.nfrs_switch               = nfrs_switch
        self.template_prompt_id        = template_prompt_id
        self.aggregated_prompt_id      = aggregated_prompt_id
        self.system_prompt_id          = system_prompt_id
        self.data                      = data

    def to_dict(self):
        return {
            'id'                       : self.id,
            'name'                     : self.name,
            'nfr'                      : self.nfr,
            'title'                    : self.title,
            'ai_switch'                : self.ai_switch,
            'ai_aggregated_data_switch': self.ai_aggregated_data_switch,
            'ai_graph_switch'          : self.ai_graph_switch,
            'ai_to_graphs_switch'      : self.ai_to_graphs_switch,
            'nfrs_switch'              : self.nfrs_switch,
            'template_prompt_id'       : self.template_prompt_id,
            'aggregated_prompt_id'     : self.aggregated_prompt_id,
            'system_prompt_id'         : self.system_prompt_id,
            'data'                     : [record.to_dict() for record in self.data]
        }

    def save(self, schema_name):
        self.__table__.schema = schema_name
        for record in self.data:
            record.__table__.schema = schema_name
        try:
            db.session.add(self)
            db.session.commit()
            return self.id
        except IntegrityError:
            db.session.rollback()
            raise

    @classmethod
    def get_configs(cls, schema_name):
        cls.__table__.schema            = schema_name
        DBTemplateData.__table__.schema = schema_name

        query = db.session.query(cls).options(joinedload(cls.data)).all()
        list  = [config.to_dict() for config in query]
        return list

    @classmethod
    def get_config_by_id(cls, schema_name, id):
        cls.__table__.schema            = schema_name
        DBTemplateData.__table__.schema = schema_name

        config = db.session.query(cls).options(joinedload(cls.data)).filter_by(id=id).one_or_none().to_dict()
        return config

    @classmethod
    def update(cls, schema_name, id, name, nfr, title, ai_switch, ai_aggregated_data_switch, ai_graph_switch, ai_to_graphs_switch, nfrs_switch, template_prompt_id, aggregated_prompt_id, system_prompt_id, data):
        cls.__table__.schema            = schema_name
        DBTemplateData.__table__.schema = schema_name

        config = db.session.query(cls).filter_by(id=id).one_or_none()
        if config:
            config.name                      = name
            config.nfr                       = nfr
            config.title                     = title
            config.ai_switch                 = ai_switch
            config.ai_aggregated_data_switch = ai_aggregated_data_switch
            config.ai_graph_switch           = ai_graph_switch
            config.ai_to_graphs_switch       = ai_to_graphs_switch
            config.nfrs_switch               = nfrs_switch
            config.template_prompt_id        = template_prompt_id
            config.aggregated_prompt_id      = aggregated_prompt_id
            config.system_prompt_id          = system_prompt_id
            config.data.clear()

            for records_data in data:
                record = DBTemplateData(
                    type        = records_data['type'],
                    content     = records_data['content'],
                    graph_id    = records_data['graph_id'],
                    template_id = config.id
                )
                config.data.append(record)

            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                raise

    @classmethod
    def count(cls, schema_name):
        cls.__table__.schema = schema_name
        count                = db.session.query(cls).count()
        return count

    @classmethod
    def delete(cls, schema_name, id):
        cls.__table__.schema            = schema_name
        DBTemplateData.__table__.schema = schema_name

        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                db.session.delete(config)
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            raise e


class DBTemplateData(db.Model):
    __tablename__ = 'template_data'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type          = db.Column(db.String(120), nullable=False)
    content       = db.Column(db.Text)
    graph_id      = db.Column(db.Integer, db.ForeignKey('graphs.id', ondelete='CASCADE'))
    template_id   = db.Column(db.Integer, db.ForeignKey('templates.id', ondelete='CASCADE'), nullable=False)

    def __init__(self, type, content, graph_id, template_id):
        self.type        = type
        self.content     = content
        self.graph_id    = graph_id
        self.template_id = template_id

    def to_dict(self):
        return {
            'id'         : self.id,
            'type'       : self.type,
            'content'    : self.content,
            'graph_id'   : self.graph_id,
            'template_id': self.template_id
        }