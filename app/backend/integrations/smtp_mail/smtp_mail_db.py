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
from app.backend.pydantic_models import SmtpMailModel
from sqlalchemy.orm              import joinedload


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

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def save(cls, schema_name, data):
        try:
            validated_data            = SmtpMailModel(**data)
            instance                  = cls(**validated_data.model_dump(exclude={'recipients'}))
            instance.__table__.schema = schema_name

            for recipient_data in validated_data.recipients:
                recipient_dict             = recipient_data.model_dump()
                recipient                  = DBSMTPMailRecipient(**recipient_dict)
                instance.recipients.append(recipient)

            if instance.is_default:
                cls.reset_default_config(schema_name)
            elif not cls.get_default_config(schema_name):
                instance.is_default = True

            db.session.add(instance)
            db.session.commit()
            return instance.id
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_configs(cls, schema_name):
        cls.__table__.schema                 = schema_name
        DBSMTPMailRecipient.__table__.schema = schema_name

        try:
            query   = db.session.query(cls).options(joinedload(cls.recipients)).all()
            configs = []
            for config in query:
                config_dict               = config.to_dict()
                config_dict['recipients'] = [recipient.to_dict() for recipient in config.recipients]
                validated_data            = SmtpMailModel(**config_dict)
                configs.append(validated_data.model_dump())
            return configs
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_id(cls, schema_name, id):
        cls.__table__.schema                 = schema_name
        DBSMTPMailRecipient.__table__.schema = schema_name

        try:
            config = db.session.query(cls).options(joinedload(cls.recipients)).filter_by(id=id).one_or_none()
            if config:
                config_dict               = config.to_dict()
                config_dict['recipients'] = [recipient.to_dict() for recipient in config.recipients]
                validated_data            = SmtpMailModel(**config_dict)
                return validated_data.model_dump()
            return None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_default_config(cls, schema_name):
        cls.__table__.schema                 = schema_name
        DBSMTPMailRecipient.__table__.schema = schema_name

        try:
            config = db.session.query(cls).options(joinedload(cls.recipients)).filter_by(is_default=True).one_or_none()
            if config:
                config_dict               = config.to_dict()
                config_dict['recipients'] = [recipient.to_dict() for recipient in config.recipients]
                validated_data            = SmtpMailModel(**config_dict)
                return validated_data.model_dump()
            return None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def reset_default_config(cls, schema_name):
        cls.__table__.schema                 = schema_name
        DBSMTPMailRecipient.__table__.schema = schema_name

        try:
            db.session.query(cls).update({cls.is_default: False})
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def update(cls, schema_name, data):
        cls.__table__.schema                 = schema_name
        DBSMTPMailRecipient.__table__.schema = schema_name
        try:
            validated_data = SmtpMailModel(**data)
            config         = db.session.query(cls).filter_by(id=validated_data.id).one_or_none()
            if validated_data.is_default:
                cls.reset_default_config(schema_name)

            exclude_fields = {'recipients'}
            for field, value in validated_data.model_dump().items():
                if field not in exclude_fields:
                    setattr(config, field, value)

            config.recipients.clear()
            for recipient_data in validated_data.recipients:
                recipient_dict = recipient_data.model_dump()
                recipient      = DBSMTPMailRecipient(**recipient_dict)
                config.recipients.append(recipient)
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
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise


class DBSMTPMailRecipient(db.Model):
    __tablename__ = 'smtp_mail_recipients'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email         = db.Column(db.String(120), nullable=False)
    smtp_mail_id  = db.Column(db.Integer, db.ForeignKey('smtp_mail.id', ondelete='CASCADE'), nullable=False)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}
