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

import logging
import traceback
import base64
from typing import Dict, Any, Union, List

from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel

from app.backend.integrations.ai_support.providers.provider_base import AIProvider


class OllamaProvider(AIProvider):
    """
    Ollama provider that implements the AIProvider interface for Ollama models.

    This provider allows using locally hosted Ollama models for text generation
    and potentially image analysis if supported by the model.
    """

    def __init__(self, ai_text_model: str, ai_image_model: str,
                 temperature: float, system_prompt: str,
                 base_url: str = "http://localhost:11434"):
        """
        Initialize the Ollama provider.

        Args:
            ai_text_model: Model name for text generation (e.g., "llama2")
            ai_image_model: Model name for image analysis (e.g., "llava")
            temperature: Temperature setting for generation
            system_prompt: System prompt to use for all interactions
            base_url: Base URL for the Ollama API (default: http://localhost:11434)
        """
        super().__init__(system_prompt)

        try:
            # Initialize Ollama models
            self.text_llm = ChatOllama(
                model=ai_text_model,
                base_url=base_url,
                temperature=temperature
            )

            # For image analysis, we'll use the same model but handle images differently
            self.image_llm = ChatOllama(
                model=ai_image_model,
                base_url=base_url,
                temperature=temperature
            )

            # Initialize embeddings for potential future use
            # self.embeddings = OllamaEmbeddings(
            #     model=ai_text_model,
            #     base_url=base_url
            # )

            self.models_created = True
            self.provider_name = "ollama"
            self.base_url = base_url

        except Exception as er:
            self._handle_initialization_error(er)

    def analyze_graph(self, graph: bytes, prompt: str) -> str:
        """
        Analyze a graph image using an Ollama model with image capabilities.

        Args:
            graph: Binary image data
            prompt: Prompt to guide the analysis

        Returns:
            Analysis result as string
        """
        if not self.models_created:
            return self._get_initialization_error_message()

        try:
            # Encode image to base64
            graph_b64 = base64.b64encode(graph).decode('utf-8')

            # Create messages with system prompt and user prompt + image
            # Note: This format may need adjustment based on the specific Ollama model
            messages = [
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{graph_b64}"}}
                    ]
                }
            ]

            # Invoke the model using the raw API
            # This is a simplified example and may need to be adjusted
            response = self.image_llm.invoke(messages)

            return response.content

        except Exception as er:
            return self._handle_request_error(er, prompt)

    def send_prompt(self, prompt: str) -> str:
        """
        Send a text prompt to the Ollama text model.

        Args:
            prompt: Text prompt to send

        Returns:
            Response from the model
        """
        if not self.models_created:
            return self._get_initialization_error_message()

        try:
            # Create messages with system prompt and user prompt
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ]

            # Invoke the model
            response = self.text_llm.invoke(messages)

            return response.content

        except Exception as er:
            return self._handle_request_error(er, prompt)

    def get_model_for_chain(self) -> BaseChatModel:
        """
        Get the model to use in LangChain chains.

        Returns:
            The text LLM to use in chains
        """
        return self.text_llm

    def _track_token_usage(self, response):
        """Track token usage from the response if available."""
        try:
            if hasattr(response, 'response_metadata') and response.response_metadata:
                self.input_tokens += response.response_metadata.get('prompt_eval_count', 0)
                self.output_tokens += response.response_metadata.get('eval_count', 0)
                self.total_tokens += self.input_tokens + self.output_tokens
        except Exception as e:
            logging.warning(f"Error tracking token usage for Ollama: {str(e)}")

    def invoke(self, prompt: Union[str, List[Dict[str, Any]]], **kwargs: Any) -> Any:
        """
        Invoke the AI model with a prompt.

        Args:
            prompt: The prompt to send to the AI.
            **kwargs: Additional keyword arguments.

        Returns:
            The response from the AI.
        """
        response = self.text_llm.invoke(prompt, **kwargs)
        self._track_token_usage(response)
        return response

    def __call__(self, prompt: Union[str, List[Dict[str, Any]]], **kwargs: Any) -> Any:
        """
        Makes the class callable for LCEL.

        Args:
            prompt: The prompt to send to the AI.
            **kwargs: Additional keyword arguments.

        Returns:
            The response from the AI.
        """
        return self.invoke(prompt, **kwargs)
