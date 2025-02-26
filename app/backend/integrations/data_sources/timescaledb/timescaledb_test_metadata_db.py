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

from app.config import db
from app.backend.pydantic_models import TestMetadataModel


class DBTestMetadata(db.Model):
    __tablename__ = 'test_metadata'
    test_title    = db.Column(db.String(120), primary_key=True, unique=True)
    application   = db.Column(db.String(120), nullable=False)
    tool          = db.Column(db.String(120), nullable=False)
    start_time    = db.Column(db.BigInteger, nullable=False)
    end_time      = db.Column(db.BigInteger, nullable=False)
    duration      = db.Column(db.BigInteger, nullable=False)
    max_threads   = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def get_all_metadata(cls, schema_name):
        cls.__table__.schema = schema_name
        try:
            records = db.session.query(cls).all()
            validated_records = []
            for record in records:
                validated = TestMetadataModel(**record.to_dict())
                validated_records.append(validated.model_dump())
            return validated_records
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise