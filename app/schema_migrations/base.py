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

from abc import ABC, abstractmethod
from sqlalchemy import inspect


class BaseMigration(ABC):
    """Abstract migration unit.

    Each concrete migration encapsulates changes for a single table or concern.
    Implement `apply()` to be idempotent and safe to run multiple times.
    """

    name: str = "base"

    @abstractmethod
    def apply(self, connection, inspector):
        """Apply the migration.

        Parameters:
            connection: SQLAlchemy connection
            inspector: SQLAlchemy Inspector (may be stale after DDL; refresh as needed)
        """
        raise NotImplementedError

    @staticmethod
    def refresh_inspector(connection):
        """Create a fresh inspector to avoid stale schema cache after DDL."""
        return inspect(connection)
