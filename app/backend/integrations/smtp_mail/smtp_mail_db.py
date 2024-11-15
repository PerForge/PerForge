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


class DBSMTPMail(db.Model):
    __tablename__ = 'smtp_mail'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name          = db.Column(db.String(120), nullable=False)
    server        = db.Column(db.String(120), nullable=False)
    port          = db.Column(db.Integer, nullable=False)
    use_ssl       = db.Column(db.Boolean, default=False)
    use_tls       = db.Column(db.Boolean, default=False)
    username      = db.Column(db.String(120), nullable=False)
    token         = db.Column(db.Integer, db.ForeignKey('public.secrets.id', ondelete='SET NULL'))
    is_default    = db.Column(db.Boolean, default=False)
    recipients    = db.relationship('DBSMTPMailRecipient', backref='smtp_mail', cascade='all, delete-orphan', lazy=True)

    def __init__(self, name, server, port, use_ssl, use_tls, username, token, is_default, recipients):
        self.name       = name
        self.server     = server
        self.port       = port
        self.use_ssl    = use_ssl
        self.use_tls    = use_tls
        self.username   = username
        self.token      = token
        self.is_default = is_default
        self.recipients = recipients

    def to_dict(self):
        return {
            'id'        : self.id,
            'name'      : self.name,
            'server'    : self.server,
            'port'      : self.port,
            'use_ssl'   : self.use_ssl,
            'use_tls'   : self.use_tls,
            'username'  : self.username,
            'token'     : self.token,
            'is_default': self.is_default,
            'recipients': [recipient.to_dict() for recipient in self.recipients]
        }

    def save(self, schema_name):
        self.__table__.schema = schema_name
        for recipient in self.recipients:
            recipient.__table__.schema = schema_name

        if self.is_default:
            self.reset_default_config(schema_name)
        elif not self.get_default_config(schema_name):
            self.is_default = True

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
        DBSMTPMailRecipient.__table__.schema = schema_name

        try:
            query = db.session.query(cls).options(joinedload(cls.recipients)).all()
            list  = [config.to_dict() for config in query]
            return list
        except SQLAlchemyError:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_id(cls, schema_name, id):
        cls.__table__.schema                 = schema_name
        DBSMTPMailRecipient.__table__.schema = schema_name

        try:
            config = db.session.query(cls).options(joinedload(cls.recipients)).filter_by(id=id).one_or_none().to_dict()
            return config
        except SQLAlchemyError:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_default_config(cls, schema_name):
        cls.__table__.schema                 = schema_name
        DBSMTPMailRecipient.__table__.schema = schema_name

        try:
            config = db.session.query(cls).filter_by(is_default=True).one_or_none().to_dict()
            return config
        except SQLAlchemyError:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def reset_default_config(cls, schema_name):
        cls.__table__.schema                 = schema_name
        DBSMTPMailRecipient.__table__.schema = schema_name

        try:
            db.session.query(cls).update({cls.is_default: False})
        except SQLAlchemyError:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def update(cls, schema_name, id, name, server, port, use_ssl, use_tls, username, token, is_default, recipients):
        cls.__table__.schema                 = schema_name
        DBSMTPMailRecipient.__table__.schema = schema_name

        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                if is_default:
                    cls.reset_default_config(schema_name)

                config.name       = name
                config.server     = server
                config.port       = port
                config.use_ssl    = use_ssl
                config.use_tls    = use_tls
                config.username   = username
                config.token      = token
                config.is_default = is_default
                config.recipients.clear()

                for recipients_data in recipients:
                    recipient = DBSMTPMailRecipient(
                        email        = recipients_data,
                        smtp_mail_id = config.id
                    )
                    config.recipients.append(recipient)

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
        cls.__table__.schema                 = schema_name
        DBSMTPMailRecipient.__table__.schema = schema_name

        try:
            config = db.session.query(cls).filter_by(id=id).one_or_none()
            if config:
                db.session.delete(config)
                db.session.commit()
                if config.is_default:
                    new_default_config = db.session.query(cls).first()
                    if new_default_config:
                        new_default_config.is_default = True
                        db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise


class DBSMTPMailRecipient(db.Model):
    __tablename__ = 'smtp_mail_recipients'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email         = db.Column(db.String(120), nullable=False)
    smtp_mail_id  = db.Column(db.Integer, db.ForeignKey('smtp_mail.id', ondelete='CASCADE'), nullable=False)

    def __init__(self, email, smtp_mail_id):
        self.email        = email
        self.smtp_mail_id = smtp_mail_id

    def to_dict(self):
        return {
            'id'          : self.id,
            'email'       : self.email,
            'smtp_mail_id': self.smtp_mail_id
        }