# Copyright 2025 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>
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
    project_id    = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    name          = db.Column(db.String(120), nullable=False)
    server        = db.Column(db.String(120), nullable=False)
    port          = db.Column(db.Integer, nullable=False)
    use_ssl       = db.Column(db.Boolean, default=False)
    use_tls       = db.Column(db.Boolean, default=False)
    username      = db.Column(db.String(120), nullable=False)
    token         = db.Column(db.Integer, db.ForeignKey('secrets.id', ondelete='SET NULL'))
    is_default    = db.Column(db.Boolean, default=False)
    recipients    = db.relationship('DBSMTPMailRecipient', backref='smtp_mail', cascade='all, delete-orphan', lazy=True)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def save(cls, project_id, data):
        try:
            data['project_id'] = project_id
            smtp_model_instance = SmtpMailModel(**data)
            instance_data = smtp_model_instance.model_dump(exclude={'recipients'})
            instance = cls(**instance_data)

            if smtp_model_instance.recipients:
                for recipient_model in smtp_model_instance.recipients:
                    instance.recipients.append(DBSMTPMailRecipient(**recipient_model.model_dump()))

            if instance.is_default:
                cls.reset_default_config(project_id)
            elif not cls.get_default_config(project_id):
                instance.is_default = True

            db.session.add(instance)
            db.session.commit()
            return instance.id
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_configs(cls, project_id):
        try:
            query = db.session.query(cls).filter_by(project_id=project_id).options(joinedload(cls.recipients)).all()
            configs = []
            for config in query:
                config_dict = config.to_dict()
                config_dict['recipients'] = [recipient.to_dict() for recipient in config.recipients]
                validated_data = SmtpMailModel(**config_dict)
                configs.append(validated_data.model_dump())
            return configs
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_id(cls, project_id, id):
        try:
            config = db.session.query(cls).filter_by(project_id=project_id, id=id).options(joinedload(cls.recipients)).one_or_none()
            if config:
                config_dict = config.to_dict()
                config_dict['recipients'] = [recipient.to_dict() for recipient in config.recipients]
                validated_data = SmtpMailModel(**config_dict)
                return validated_data.model_dump()
            return None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_default_config(cls, project_id, current_config_id=None):
        try:
            config = db.session.query(cls).filter_by(project_id=project_id, is_default=True).options(joinedload(cls.recipients)).one_or_none()
            if config and config.id != current_config_id:
                config_dict = config.to_dict()
                config_dict['recipients'] = [recipient.to_dict() for recipient in config.recipients]
                validated_data = SmtpMailModel(**config_dict)
                return validated_data.model_dump()
            return None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def reset_default_config(cls, project_id):
        try:
            db.session.query(cls).filter_by(project_id=project_id).update({cls.is_default: False})
            db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def update(cls, project_id, data):
        try:
            data['project_id'] = project_id
            validated_data = SmtpMailModel(**data)
            config = db.session.query(cls).filter_by(project_id=project_id, id=validated_data.id).one_or_none()
            if not config:
                return

            if validated_data.is_default:
                cls.reset_default_config(project_id)
            elif not cls.get_default_config(project_id, validated_data.id):
                validated_data.is_default = True

            exclude_fields = {'recipients', 'project_id'}
            for field, value in validated_data.model_dump(exclude=exclude_fields).items():
                setattr(config, field, value)

            config.recipients.clear()
            for recipient_data in validated_data.recipients:
                recipient_dict = recipient_data.model_dump()
                recipient = DBSMTPMailRecipient(**recipient_dict)
                config.recipients.append(recipient)
            db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def count(cls, project_id):
        try:
            return db.session.query(cls).filter_by(project_id=project_id).count()
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def delete(cls, project_id, id):
        try:
            config = db.session.query(cls).filter_by(project_id=project_id, id=id).one_or_none()
            if config:
                is_default_deleted = config.is_default
                db.session.delete(config)
                db.session.commit()
                if is_default_deleted:
                    new_default_config = db.session.query(cls).filter_by(project_id=project_id).first()
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
