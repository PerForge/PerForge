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

import logging

from flask_login             import UserMixin
from flask_sqlalchemy        import SQLAlchemy
from werkzeug.datastructures import MultiDict
from sqlalchemy              import inspect, text


db = SQLAlchemy()

class Users(db.Model, UserMixin):

    __tablename__ = 'Users'
    id            = db.Column(db.Integer, primary_key=True)
    user          = db.Column(db.String(64), unique=True)
    password      = db.Column(db.String(500))
    is_admin      = db.Column(db.Boolean, default=False)

    def __init__(self, user, password, is_admin = None):
        self.user     = user
        self.password = password
        if is_admin: self.is_admin = is_admin

    def __repr__(self):
        return f'{self.id} - {self.user}'

    def save(self):
        # Inject self into db session
        db.session.add(self)
        # Commit change and save the object
        db.session.commit()
        return self

    def check_admin_exists():
        # Query the Users table for any user with is_admin set to True
        admin_user = Users.query.filter_by(is_admin=True).first()
        # If an admin user is found, return True, else return False
        if admin_user:
            return True
        else:
            return False

class Secret(db.Model):

    __tablename__ = 'Secrets'
    id            = db.Column(db.Integer, primary_key=True)
    type          = db.Column(db.String(120))
    key           = db.Column(db.String(120), unique=True)
    value         = db.Column(db.String(500))

    def __init__(self, type, value, key):
        self.type  = type
        self.key   = key
        self.value = value

    def __repr__(self):
        return f'{self.id} - {self.key}'

    def save(self):
        # Inject self into db session
        db.session.add(self)
        # Commit change and save the object
        db.session.commit()
        return self.key

    @classmethod
    def get(cls, id):
        result = db.session.query(cls).filter_by(id=id).first()
        if result:
            return MultiDict({"id":result.id,"type":result.type,"key":result.key,"value":result.value})
        else:
            return "Secret not found"

    @classmethod
    def get_by_key(cls, key):
        result = db.session.query(cls).filter_by(key=key).first()
        if result:
            return result.value
        else:
            return "Secret not found"

    @classmethod
    def if_exists(cls, id):
        result = db.session.query(cls).filter_by(id=id).first()
        if result:
            return True
        else:
            return False

    @classmethod
    def update(cls, id, new_type, new_value, new_key):
        # Query the secret by key
        secret = db.session.query(cls).filter_by(id=id).first()
        if secret:
            # Update the value
            secret.type  = new_type
            secret.value = new_value
            secret.key   = new_key
            # Commit the changes to the database
            db.session.commit()

    @classmethod
    def get_secrets(cls):
        # Query all ids and keys from the Secrets table
        secrets = db.session.query(cls.id, cls.type, cls.key).all()
        # Extract ids and keys from the result and return as a list of tuples
        return [{"id":secret.id, "type":secret.type, "key": secret.key} for secret in secrets] if secrets else []

    @classmethod
    def delete(cls, id):
        db.session.query(cls).filter_by(id=id).delete()
        db.session.commit()

    @classmethod
    def count_secrets(cls):
        return db.session.query(cls).count()


class DBMigrations:

    def migration_1():
        logging.warning('Migration number 1 has started.')
        # Check if the 'type' column already exists
        inspector = inspect(db.engine)
        columns   = [column['name'] for column in inspector.get_columns('Secrets')]

        if 'type' not in columns:
            try:
                # Add the 'type' column to the 'Secrets' table
                with db.engine.connect() as connection:
                    connection.execute(text('ALTER TABLE "Secrets" ADD COLUMN "type" VARCHAR(120)'))
                logging.warning('Successfully added "type" column to "Secrets" table.')
            except Exception as e:
                logging.error(f'Error adding "type" column to "Secrets" table: {e}')
        else:
            logging.warning('Column "type" has already exists in "Secrets" table.')