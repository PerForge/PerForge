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


class DBInfluxdb(db.Model):
    __tablename__ = 'influxdb'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name          = db.Column(db.String(120), nullable=False)
    url           = db.Column(db.String(120), nullable=False)
    org_id        = db.Column(db.String(120), nullable=False)
    token         = db.Column(db.Integer, db.ForeignKey('public.secrets.id', ondelete='SET NULL'))
    timeout       = db.Column(db.Integer, nullable=False)
    bucket        = db.Column(db.String(120), nullable=False)
    listener      = db.Column(db.String(120), nullable=False)
    tmz           = db.Column(db.String(120), nullable=False)
    is_default    = db.Column(db.Boolean, default=False)

    def __init__(self, name, url, org_id, token, timeout, bucket, listener, tmz, is_default):
        self.name       = name
        self.url        = url
        self.org_id     = org_id
        self.token      = token
        self.timeout    = timeout
        self.bucket     = bucket
        self.listener   = listener
        self.tmz        = tmz
        self.is_default = is_default

    def to_dict(self):
        return {
            'id'        : self.id,
            'name'      : self.name,
            'url'       : self.url,
            'org_id'    : self.org_id,
            'token'     : self.token,
            'timeout'   : self.timeout,
            'bucket'    : self.bucket,
            'listener'  : self.listener,
            'tmz'       : self.tmz,
            'is_default': self.is_default
        }

    def save(self, schema_name):
        self.__table__.schema = schema_name
        db.session.add(self)
        try:
            db.session.commit()
            return self.id
        except IntegrityError:
            db.session.rollback()
            raise

    @classmethod
    def get_configs(cls, schema_name):
        cls.__table__.schema = schema_name
        query                = db.session.query(cls).all()
        list                 = [config.to_dict() for config in query]
        return list

    @classmethod
    def get_config_by_id(cls, schema_name, id):
        cls.__table__.schema = schema_name
        config               = db.session.query(cls).filter_by(id=id).one_or_none().to_dict()
        return config

    @classmethod
    def update(cls, schema_name, id, name, url, org_id, token, timeout, bucket, listener, tmz, is_default):
        cls.__table__.schema = schema_name
        config               = db.session.query(cls).filter_by(id=id).one_or_none()
        if config:
            config.name       = name
            config.url        = url
            config.org_id     = org_id
            config.token      = token
            config.timeout    = timeout
            config.bucket     = bucket
            config.listener   = listener
            config.tmz        = tmz
            config.is_default = is_default

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
        cls.__table__.schema = schema_name
        try:
            record = db.session.query(cls).filter_by(id=id).one_or_none()
            if record:
                db.session.delete(record)
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            raise e