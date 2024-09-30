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

from abc        import ABC, abstractmethod
from app.config import config_path


class Integration(ABC):

    def __init__(self, project):
        self.project     = project
        self.config_path = config_path

    @abstractmethod
    def set_config(self):
        pass

    @abstractmethod
    def __str__(self):
        pass

    def remove_all_spaces(self, path):
        return path.replace(' ', '')

    def remove_trailing_slash(self, url):
        url = self.remove_all_spaces(url)
        if url.endswith('/'):
            return url[:-1]
        return url
    
    def ensure_leading_slash(self, path):
        url = self.remove_all_spaces(url)
        if not path.startswith('/'):
            return '/' + path
        return path