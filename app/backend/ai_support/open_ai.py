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
import base64

from openai import OpenAI
from openai import AzureOpenAI


class ChatGPTAI:

    def __init__(self, ai_provider, ai_text_model, ai_image_model, token, temperature, azure_url = None, api_version = None):
        try:
            if ai_provider == "openai":
                self.client = OpenAI(api_key=token)
            if ai_provider == "azure_openai":
                self.client = AzureOpenAI(
                    api_key        = token,
                    api_version    = api_version,
                    azure_endpoint = azure_url
                )
            self.temperature            = temperature
            self.model_text             = ai_text_model
            self.model_image            = ai_image_model
            # self.system_prompt          = system_prompt
            self.input_tokens           = 0
            self.output_tokens          = 0
            self.list_of_graph_analysis = []
            self.models_created         = True  # Set flag to True if models are created successfully
        except Exception as er:
            self.models_created = False  # Flag to indicate successful model creation
            logging.warning("An error occurred: " + str(er))
            err_info = traceback.format_exc()  
            logging.warning("Detailed error info: " + err_info)

    def analyze_graph(self, graph, prompt):
        if self.models_created:
            try:
                graph    = base64.b64encode(graph).decode('utf-8')
                response = self.client.chat.completions.create(
                    model       = self.model_image,
                    temperature = self.temperature,
                    max_tokens  = 300,
                    messages    = [
                        {
                            "role": "system",
                            "content": "You are a skilled Performance Analyst with strong data analysis expertise. Please help analyze the performance test results."
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{graph}",
                                    },
                                },
                            ],
                        }
                    ]
                )
                if response.usage:
                    self.input_tokens  += response.usage.prompt_tokens
                    self.output_tokens += response.usage.completion_tokens
                if response.choices[0].message.content:
                    return response.choices[0].message.content
                else:
                    logging.warning("Failed to receive a response from the AI: " + response)
                    return "Failed to receive a response from the AI (check logs)."
            except Exception as er:
                logging.warning("An error occurred: " + str(er))
                err_info = traceback.format_exc()  
                logging.warning("Detailed error info: " + err_info)
                return "Failed to receive a response from the AI (check logs)."

    def send_prompt(self, prompt):
        if not self.models_created:
            return "Error: OpenAI models failed to initialize (check logs)."
        try:
            response = self.client.chat.completions.create(
                model       = self.model_text,
                temperature = self.temperature,
                messages    = [
                    {
                        "role": "system",
                        "content": self.system_prompt
                    },
                    {"role": "user", "content": prompt}
                ]
            )
            if response.usage:
                self.input_tokens  += response.usage.prompt_tokens
                self.output_tokens += response.usage.completion_tokens
            if response.choices[0].message.content:
                return response.choices[0].message.content
            else:
                logging.warning("Failed to receive a response from the AI: " + response)
                return "Failed to receive a response from the AI (check logs)."
        except Exception as er:
            logging.warning("An error occurred: " + str(er))
            err_info = traceback.format_exc()
            logging.warning("Detailed error info: " + err_info)
            return "Failed to receive a response from the AI (check logs)."