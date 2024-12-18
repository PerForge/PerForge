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
import requests
import re
import logging


def get_current_version_from_file():
    try:
        with open('version.txt', 'r') as file:
            version = file.read().strip()
        return version
    except Exception as e:
        logging.warning(f"Failed to read version from file: {e}")
        return None

def get_new_version_from_docker_hub(current_version):
    url  = "https://hub.docker.com/v2/repositories/perforge/perforge-app/tags"
    tags = []
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        tags.extend([tag['name'] for tag in data['results']])
        return tags[1]
    else:
        return current_version

def is_valid_new_version_from_docker_hub(current_version, new_version):
    # Define a regex pattern for a valid version number (e.g., "1.0.15")
    pattern = re.compile(r'^\d+\.\d+\.\d+$')
    if not pattern.match(new_version):
        return False
    # Split the version strings into their numeric components
    current_parts = list(map(int, current_version.split('.')))
    new_parts     = list(map(int, new_version.split('.')))
    # Compare the numeric components
    return new_parts > current_parts