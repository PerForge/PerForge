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
import base64
from typing import Dict, Any, Union, List

from langchain_community.chat_models import ChatLiteLLM
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel

from app.backend.integrations.ai_support.providers.provider_base import AIProvider


class LiteLLMProvider(AIProvider):
    """
    LiteLLM provider that implements the AIProvider interface for various models via LiteLLM.
    """

    def __init__(self, ai_text_model: str, ai_image_model: str, token: str,
                 temperature: float, system_prompt: str, **kwargs):
        """
        Initialize the LiteLLM provider.

        Args:
            ai_text_model: Model name for text generation (e.g., "gpt-3.5-turbo", "claude-2", "vertex_ai/gemini-pro")
            ai_image_model: Model name for image analysis
            token: API Key (will be set as env var or passed directly if supported)
            temperature: Temperature setting for generation
            system_prompt: System prompt to use for all interactions
            **kwargs: Additional arguments
        """
        super().__init__(system_prompt)

        try:
            # Initialize LiteLLM models
            # Note: LiteLLM often expects keys in environment variables, but passing api_key helps specific providers.
            # We map 'token' to 'api_key' or specific provider keys based on the model prefix if needed,
            # but ChatLiteLLM generally handles 'api_key' generic argument.

            # For some providers, we might need to set environment variables.
            # However, ChatLiteLLM accepts openai_api_key, anthropic_api_key etc. via **completion_kwargs
            # or we can pass `api_key` which LiteLLM tries to use.

            self.text_llm = ChatLiteLLM(
                model=ai_text_model,
                temperature=temperature,
                api_key=token,
            )

            self.image_llm = ChatLiteLLM(
                model=ai_image_model,
                temperature=temperature,
                api_key=token,
            )

            self.models_created = True
            self.provider_name = "litellm"
            # Initialize token tracking attributes
            self.input_tokens = 0
            self.output_tokens = 0
            self.total_tokens = 0

        except Exception as er:
            self._handle_initialization_error(er)

    def analyze_graph(self, graph: bytes, prompt: str) -> str:
        """
        Analyze a graph image using the LiteLLM Vision model.

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

            # Detect image format
            image_format = self._detect_image_format(graph)

            # Create messages with system prompt and user prompt + image
            # OpenAI-compatible format is widely supported by LiteLLM for vision
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{image_format};base64,{graph_b64}",
                        },
                    },
                ])
            ]

            # Invoke the model
            response = self.image_llm.invoke(messages)

            # Track token usage if available
            self._track_token_usage(response)

            return response.content

        except Exception as er:
            return self._handle_request_error(er, prompt)

    def _detect_image_format(self, image_data: bytes) -> str:
        """
        Detect the format of an image from its binary data.

        Args:
            image_data: Raw bytes of the image file

        Returns:
            String representing the image format ('jpeg', 'png', etc.)
        """
        # Check for common image format signatures
        if image_data.startswith(b'\xff\xd8\xff'):
            return 'jpeg'
        elif image_data.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'png'
        elif image_data.startswith(b'GIF87a') or image_data.startswith(b'GIF89a'):
            return 'gif'
        elif image_data.startswith(b'RIFF') and image_data[8:12] == b'WEBP':
            return 'webp'
        elif image_data.startswith(b'BM'):
            return 'bmp'
        elif image_data.startswith(b'\x00\x00\x01\x00'):
            return 'ico'
        else:
            # Default to jpeg if we can't detect the format
            logging.warning("Image format could not be detected, defaulting to jpeg")
            return 'jpeg'

    def send_prompt(self, prompt: str) -> str:
        """
        Send a text prompt to the LiteLLM text model.

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

            # Track token usage if available
            self._track_token_usage(response)

            return response.content

        except Exception as er:
            return self._handle_request_error(er, prompt)

    # Using base class implementation for token tracking

    def get_model_for_chain(self) -> BaseChatModel:
        """
        Get the model to use in LangChain chains.

        Returns:
            The text LLM to use in chains
        """
        return self.text_llm

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
