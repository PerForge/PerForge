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
from typing import Dict, Any, List, Union

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel

from app.backend.integrations.ai_support.providers.provider_base import AIProvider


class GeminiProvider(AIProvider):
    """
    Gemini provider that implements the AIProvider interface for Google's Gemini models.
    """

    def __init__(self, ai_text_model: str, ai_image_model: str, token: str,
                 temperature: float, system_prompt: str):
        """
        Initialize the Gemini provider.

        Args:
            ai_text_model: Model name for text generation
            ai_image_model: Model name for image analysis
            token: API token for Google Gemini
            temperature: Temperature setting for generation
            system_prompt: System prompt to use for all interactions
        """
        super().__init__(system_prompt)

        try:
            # Initialize Gemini models
            self.text_llm = ChatGoogleGenerativeAI(
                model=ai_text_model,
                google_api_key=token,
                temperature=temperature
            )

            self.image_llm = ChatGoogleGenerativeAI(
                model=ai_image_model,
                google_api_key=token,
                temperature=temperature
            )

            # Initialize embeddings for potential future use
            # self.embeddings = GoogleGenerativeAIEmbeddings(
            #     model="models/embedding-001",
            #     google_api_key=token
            # )

            self.models_created = True
            self.provider_name = "gemini"

        except Exception as er:
            self._handle_initialization_error(er)

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

    def analyze_graph(self, graph: bytes, prompt: str) -> str:
        """
        Analyze a graph image using the Gemini Vision model.

        Args:
            graph: Binary image data
            prompt: Prompt to guide the analysis

        Returns:
            Analysis result as string
        """
        if not self.models_created:
            return self._get_initialization_error_message()

        try:
            # Detect image format
            image_format = self._detect_image_format(graph)
            # Encode image to base64
            graph_b64 = base64.b64encode(graph).decode('utf-8')

            # Create messages with system prompt and user prompt + image
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
            # Retry with a different approach if the first attempt fails
            try:
                logging.warning(f"First attempt failed, retrying with different format: {str(er)}")

                # Detect image format
                image_format = self._detect_image_format(graph)
                # Encode image to base64
                graph_b64 = base64.b64encode(graph).decode('utf-8')

                # Alternative approach for Gemini
                response = self.image_llm.invoke([
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"{self.system_prompt}\n\n{prompt}"},
                            {"type": "image_url", "image_url": f"data:image/{image_format};base64,{graph_b64}"}
                        ]
                    }
                ])

                # Track token usage if available
                self._track_token_usage(response)

                return response.content

            except Exception as retry_er:
                return self._handle_request_error(retry_er, prompt)

    def send_prompt(self, prompt: str) -> str:
        """
        Send a text prompt to the Gemini text model.

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

    def get_model_for_chain(self) -> BaseChatModel:
        """
        Get the model to use in LangChain chains.

        Returns:
            The text LLM to use in chains
        """
        return self.text_llm

    # Using base class implementation for token tracking

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


# For backward compatibility
GeminiAI = GeminiProvider
