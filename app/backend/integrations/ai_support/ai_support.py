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
import traceback

from app.backend.integrations.integration              import Integration
from app.backend.integrations.ai_support.gemini_ai     import GeminiAI
from app.backend.integrations.ai_support.open_ai       import ChatGPTAI
from app.backend.components.prompts.prompts_db         import DBPrompts
from app.backend.integrations.ai_support.ai_support_db import DBAISupport
from app.backend.components.secrets.secrets_db         import DBSecrets


class AISupport(Integration):

    def __init__(self, project, system_prompt, id = None):
        super().__init__(project)
        self.models_created           = False
        self.graph_analysis           = []
        self.aggregated_data_analysis = []
        self.summary                  = []
        self.system_prompt            = DBPrompts.get_config_by_id(id=system_prompt)["prompt"] or "You are a skilled Performance Analyst with strong data analysis expertise. Please help analyze the performance test results."
        self.set_config(id) # Should be in the end

    def __str__(self):
        return f'Integration id is {self.id}'

    def set_config(self, id):
        id = id if id else DBAISupport.get_default_config(schema_name=self.schema_name)["id"]
        config = DBAISupport.get_config_by_id(schema_name=self.schema_name, id=id)
        if config['id']:
            self.name           = config["name"]
            self.ai_provider    = config["ai_provider"]
            self.ai_text_model  = config["ai_text_model"]
            self.ai_image_model = config["ai_image_model"]
            self.token          = DBSecrets.get_config_by_id(id=config["token"])["value"]
            self.temperature    = config["temperature"]
            if self.ai_provider == "gemini":
                self.ai_obj         = GeminiAI(ai_text_model=self.ai_text_model, ai_image_model=self.ai_image_model, token=self.token, temperature=self.temperature, system_prompt=self.system_prompt)
                self.models_created = True
            if self.ai_provider == "openai":
                self.ai_obj         = ChatGPTAI(ai_provider=self.ai_provider, ai_text_model=self.ai_text_model, ai_image_model=self.ai_image_model, token=self.token, temperature=self.temperature, system_prompt=self.system_prompt)
                self.models_created = True
            if self.ai_provider == "azure_openai":
                self.azure_url      = config["azure_url"]
                self.api_version    = config["api_version"]
                self.ai_obj         = ChatGPTAI(ai_provider=self.ai_provider, ai_text_model=self.ai_text_model, ai_image_model=self.ai_image_model, token=self.token, temperature=self.temperature, system_prompt=self.system_prompt, azure_url=self.azure_url, api_version=self.api_version)
                self.models_created = True
        else:
            logging.warning("There's no AI integration configured, or you're attempting to send a request from an unsupported location.")

    def analyze_graph(self, name, graph, prompt_id):
        if not self.models_created: return ""
        if not prompt_id or not graph: return ""
        prompt_value = DBPrompts.get_config_by_id(id=prompt_id)["prompt"]
        response     = self.ai_obj.analyze_graph(graph, prompt_value)
        self.graph_analysis.append(name)
        self.graph_analysis.append(response)
        return response

    def analyze_aggregated_data(self, data, prompt_id):
        if self.models_created:
            try:
                prompt_value = DBPrompts.get_config_by_id(id=prompt_id)["prompt"]
                prompt_value = prompt_value + "\n\n" + str(data)
                result       = self.ai_obj.send_prompt(prompt_value)
                self.aggregated_data_analysis.append(result)
            except Exception as er:
                logging.warning("An error occurred: " + str(er))
                err_info = traceback.format_exc()
                logging.warning("Detailed error info: " + err_info)

    def prepare_list_of_analysis(self, list):
        result = ""
        for obj in list:
            result += obj
            result += "\n\n"
        return str(result)

    def create_template_summary(self, prompt_id, nfr_summary):
        if not self.models_created:
            return "Error: AI failed to initialize."
        prompt_value = DBPrompts.get_config_by_id(id=prompt_id)["prompt"]
        prompt_value = prompt_value.replace("[aggregated_data_analysis]", self.prepare_list_of_analysis(self.aggregated_data_analysis))
        prompt_value = prompt_value.replace("[graphs_analysis]", self.prepare_list_of_analysis(self.graph_analysis))
        prompt_value = prompt_value.replace("[nfr_summary]", nfr_summary)
        result       = self.ai_obj.send_prompt(prompt_value)
        self.summary.append(result)
        return result

    def create_template_group_summary(self, prompt_id):
        if not self.models_created:
            return "Error: AI failed to initialize."
        prompt_value = DBPrompts.get_config_by_id(id=prompt_id)["prompt"]
        for text in self.summary:
            prompt_value = prompt_value + "\n" + text
        result = self.ai_obj.send_prompt(prompt_value)
        return result