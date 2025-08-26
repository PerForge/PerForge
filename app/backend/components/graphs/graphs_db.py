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
import os
import yaml

from app.config                  import db
from app.backend.pydantic_models import GraphModel
from sqlalchemy                  import or_, and_


class DBGraphs(db.Model):
    __tablename__ = 'graphs'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id    = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    name          = db.Column(db.String(120), nullable=False)
    type          = db.Column(db.String(20), nullable=False, default='custom', index=True)
    grafana_id    = db.Column(db.Integer, db.ForeignKey('grafana.id', ondelete='CASCADE'), nullable=True)
    dash_id       = db.Column(db.Integer, db.ForeignKey('grafana_dashboards.id', ondelete='CASCADE'), nullable=True)
    view_panel    = db.Column(db.Integer, nullable=True)
    width         = db.Column(db.Integer, nullable=False)
    height        = db.Column(db.Integer, nullable=False)
    custom_vars   = db.Column(db.String(500))
    prompt_id     = db.Column(db.Integer, db.ForeignKey('prompts.id', ondelete='SET NULL'))

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def save(cls, project_id, data):
        try:
            data['project_id'] = project_id
            validated_data = GraphModel(**data).model_dump()
            instance = cls(**validated_data)
            instance.project_id = project_id
            db.session.add(instance)
            db.session.commit()
            return instance.id
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_configs(cls, project_id, include_defaults: bool = False):
        """
        Get graphs for a project.

        Args:
            project_id: target project id
            include_defaults: when True, also include global default graphs
                              (rows with project_id IS NULL and type == 'default')

        Returns:
            List[dict]: validated graph configs
        """
        try:
            base_query = db.session.query(cls)
            if include_defaults:
                records = base_query.filter(
                    or_(
                        cls.project_id == project_id,
                        and_(cls.project_id.is_(None), cls.type == 'default')
                    )
                ).all()
            else:
                records = base_query.filter_by(project_id=project_id).all()

            return [GraphModel(**config.to_dict()).model_dump() for config in records]
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def get_config_by_id(cls, project_id, id):
        """
        Get a graph by ID.

        Behavior:
        - If a project_id is provided, return the graph when it either belongs to that project
          or is a default graph (project_id IS NULL).
        - If project_id is None, return only default graph (project_id IS NULL).
        """
        try:
            query = db.session.query(cls)
            if project_id is None:
                config = query.filter(and_(cls.id == id, cls.project_id.is_(None))).one_or_none()
            else:
                # First fetch by id (ids are unique), then authorize by ownership or default
                cfg = query.filter_by(id=id).one_or_none()
                if cfg and (cfg.project_id == project_id or cfg.project_id is None):
                    config = cfg
                else:
                    config = None
            if config:
                return GraphModel.model_validate(config.to_dict()).model_dump()
            return None
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def update(cls, project_id, data):
        try:
            data['project_id'] = project_id
            validated_data = GraphModel(**data)
            config = db.session.query(cls).filter_by(project_id=project_id, id=validated_data.id).one_or_none()
            if config:
                for key, value in validated_data.model_dump().items():
                    setattr(config, key, value)
                db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def count(cls, project_id):
        try:
            count = db.session.query(cls).filter_by(project_id=project_id).count()
            return count
        except Exception:
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def delete(cls, project_id, id):
        try:
            config = db.session.query(cls).filter_by(project_id=project_id, id=id).one_or_none()
            if config:
                db.session.delete(config)
                db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise

    @classmethod
    def load_default_graphs_from_yaml(cls):
        """
        Reset and load default INTERNAL graphs from YAML.

        - Upserts graphs with type == 'default'
        - Removes internal graphs not present in YAML
        - Loads graphs from app/backend/components/graphs/graphs.yaml
        - For internal graphs, Grafana-related fields are not required

        Returns: number of imported graphs
        """
        try:
            file_path = os.path.join('app', 'backend', 'components', 'graphs', 'graphs.yaml')
            if not os.path.exists(file_path):
                logging.info(f"Graphs YAML not found at {file_path}; skipping import")
                db.session.commit()
                return 0

            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}

            # Prepare existing internal graphs keyed by name for upsert
            existing_graphs = db.session.query(cls).filter_by(type='default').all()
            existing_by_name = {g.name: g for g in existing_graphs}

            yaml_internal = [item for item in (data.get('graphs', []) or []) if item.get('type', 'default') == 'default']
            seen_names = set()
            created = 0
            updated = 0

            for item in yaml_internal:
                try:
                    name = item.get('name')
                    if not name:
                        continue
                    seen_names.add(name)
                    width = item.get('width', 1000)
                    height = item.get('height', 500)
                    custom_vars = item.get('custom_vars')
                    prompt_id = item.get('prompt_id')

                    if name in existing_by_name:
                        g = existing_by_name[name]
                        g.width = width
                        g.height = height
                        g.custom_vars = custom_vars
                        g.prompt_id = prompt_id
                        updated += 1
                    else:
                        # Create new internal graph (ID will be assigned, existing IDs preserved)
                        instance = cls(
                            project_id=None,
                            name=name,
                            type='default',
                            width=width,
                            height=height,
                            custom_vars=custom_vars,
                            prompt_id=prompt_id
                        )
                        db.session.add(instance)
                        created += 1
                except Exception:
                    logging.warning(f"Skipping graph due to validation/persistence error: {traceback.format_exc()}")

            # Remove internal graphs that are not present in YAML
            removed = 0
            for g in existing_graphs:
                if g.name not in seen_names:
                    db.session.delete(g)
                    removed += 1

            db.session.commit()
        except Exception:
            db.session.rollback()
            logging.warning(str(traceback.format_exc()))
            raise
