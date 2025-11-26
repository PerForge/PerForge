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

import base64
import logging
from typing import Any, Dict, List, Union

from anthropic import Anthropic
from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel

from app.backend.integrations.ai_support.providers.provider_base import AIProvider


class AnthropicProvider(AIProvider):
    """Anthropic provider implementation built on Claude 3 models."""

    def __init__(
        self,
        ai_text_model: str,
        ai_image_model: str,
        token: str,
        temperature: float,
        system_prompt: str,
    ):
        super().__init__(system_prompt)

        self._temperature = temperature
        self._text_model_name = ai_text_model
        self._image_model_name = ai_image_model or ai_text_model

        try:
            # LangChain chat models for chain compatibility
            self.text_llm = ChatAnthropic(
                model=self._text_model_name,
                anthropic_api_key=token,
                temperature=temperature,
                max_tokens=4096,
            )

            self.image_llm = ChatAnthropic(
                model=self._image_model_name,
                anthropic_api_key=token,
                temperature=temperature,
                max_tokens=2048,
            )

            # Native client for fine-grained control over multimodal prompts
            self.client = Anthropic(api_key=token)

            self.models_created = True
            self.provider_name = "anthropic"
        except Exception as er:
            self._handle_initialization_error(er)

    def _detect_image_format(self, image_data: bytes) -> str:
        if image_data.startswith(b"\xff\xd8\xff"):
            return "jpeg"
        if image_data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        if image_data.startswith(b"GIF87a") or image_data.startswith(b"GIF89a"):
            return "gif"
        if image_data.startswith(b"RIFF") and image_data[8:12] == b"WEBP":
            return "webp"
        if image_data.startswith(b"BM"):
            return "bmp"
        if image_data.startswith(b"\x00\x00\x01\x00"):
            return "ico"
        logging.warning("Image format could not be detected, defaulting to jpeg")
        return "jpeg"

    @staticmethod
    def _extract_text_content(content: Union[str, List[Any]]) -> str:
        if isinstance(content, str):
            return content
        parts: List[str] = []
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    text_value = item.get("text") or item.get("content")
                    if text_value:
                        parts.append(str(text_value))
                else:
                    text_value = getattr(item, "text", None)
                    if text_value:
                        parts.append(str(text_value))
        return "".join(parts)

    def _record_usage(self, usage: Union[Dict[str, Any], Any, None]) -> None:
        try:
            if not usage:
                return
            if isinstance(usage, dict):
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                total_tokens = usage.get("total_tokens")
            else:
                input_tokens = getattr(usage, "input_tokens", 0)
                output_tokens = getattr(usage, "output_tokens", 0)
                total_tokens = getattr(usage, "total_tokens", None)
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            self.total_tokens = total_tokens or (self.input_tokens + self.output_tokens)
        except Exception as er:
            logging.warning(f"Error tracking token usage for Anthropic: {str(er)}")

    def analyze_graph(self, graph: bytes, prompt: str) -> str:
        if not self.models_created:
            return self._get_initialization_error_message()

        try:
            image_format = self._detect_image_format(graph)
            graph_b64 = base64.b64encode(graph).decode("utf-8")

            response = self.client.messages.create(
                model=self._image_model_name,
                temperature=self._temperature,
                max_tokens=1024,
                system=self.system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": f"image/{image_format}",
                                    "data": graph_b64,
                                },
                            },
                        ],
                    }
                ],
            )

            self._record_usage(getattr(response, "usage", None))
            text_output = self._extract_text_content(getattr(response, "content", []))
            return text_output or ""
        except Exception as er:
            return self._handle_request_error(er, prompt)

    def send_prompt(self, prompt: str) -> str:
        if not self.models_created:
            return self._get_initialization_error_message()

        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt),
            ]
            response = self.text_llm.invoke(messages)
            self._track_token_usage(response)
            return self._extract_text_content(response.content)
        except Exception as er:
            return self._handle_request_error(er, prompt)

    def get_model_for_chain(self) -> BaseChatModel:
        return self.text_llm

    def invoke(self, prompt: Union[str, List[Dict[str, Any]]], **kwargs: Any) -> Any:
        response = self.text_llm.invoke(prompt, **kwargs)
        self._track_token_usage(response)
        return response

    def __call__(self, prompt: Union[str, List[Dict[str, Any]]], **kwargs: Any) -> Any:
        return self.invoke(prompt, **kwargs)
