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

import google.generativeai as genai
import logging
import traceback
import time

class GeminiAI:

    def __init__(self, ai_text_model, ai_image_model, token, temperature):
        self.models_created = False  # Flag to indicate successful model creation
        try:
            genai.configure(api_key=token)
            self.model_text        = genai.GenerativeModel(ai_text_model)
            self.model_image       = genai.GenerativeModel(ai_image_model)
            self.generation_config = genai.types.GenerationConfig(
                max_output_tokens = 2048,
                temperature       = temperature)
            self.list_of_graph_analysis = []
            self.models_created         = True  # Set flag to True if models are created successfully
        except Exception as er:
            logging.warning("An error occurred: " + str(er))
            err_info = traceback.format_exc()  
            logging.warning("Detailed error info: " + err_info)

    def analyze_graph(self, graph, prompt):
        if self.models_created:
            graph = {
                'mime_type': 'image/png',
                'data': graph
            }
            for _ in range(3):
                try:
                    response = self.model_image.generate_content([graph, prompt], generation_config=self.generation_config)
                    response.resolve()
                    if response.text:
                        return response.text
                    else:
                        logging.warning("Failed to receive a response from the AI: " + response)
                except Exception as er:
                    logging.warning("An error occurred: " + str(er))
                    err_info = traceback.format_exc()
                    logging.warning("Detailed error info: " + err_info)
                time.sleep(10)
            return "Failed to receive a response from the AI (check logs)."

    def send_prompt(self, prompt):
        if not self.models_created:
            return "Error: Gemini models failed to initialize (check logs)."
        for _ in range(3):
            try:
                response = self.model_text.generate_content(prompt, generation_config=self.generation_config)
                response.resolve()
                if response.text:
                    return response.text
                else:
                    logging.warning("Failed to receive a response from the AI: " + response)
            except Exception as er:
                logging.warning("An error occurred: " + str(er))
                err_info = traceback.format_exc()
                logging.warning("Detailed error info: " + err_info)
            time.sleep(10)
        logging.warning("Promt details: " + prompt)
        return "Failed to receive a response from the AI (check logs)."