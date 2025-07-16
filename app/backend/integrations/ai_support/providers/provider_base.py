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
from abc import ABC, abstractmethod
from typing import Dict

from langchain_core.language_models.chat_models import BaseChatModel


class AIProvider(ABC):
    """
    Abstract base class for AI providers.

    All AI provider implementations should inherit from this class and implement
    the required methods for compatibility with the AISupport class.
    """

    def __init__(self, system_prompt: str):
        """
        Initialize the AI provider.

        Args:
            system_prompt: System prompt to use for all interactions
        """
        self.models_created = False
        self.input_tokens = 0
        self.output_tokens = 0
        self.system_prompt = system_prompt
        self.provider_name = "base"  # Should be overridden by subclasses

    @abstractmethod
    def analyze_graph(self, graph: bytes, prompt: str) -> str:
        """
        Analyze a graph image using the AI model.

        Args:
            graph: Binary image data
            prompt: Prompt to guide the analysis

        Returns:
            Analysis result as string
        """
        pass

    @abstractmethod
    def send_prompt(self, prompt: str) -> str:
        """
        Send a text prompt to the AI model.

        Args:
            prompt: Text prompt to send

        Returns:
            Response from the model
        """
        pass

    @abstractmethod
    def get_model_for_chain(self) -> BaseChatModel:
        """
        Get the model to use in LangChain chains.

        Returns:
            The text LLM to use in chains
        """
        pass

    def _handle_initialization_error(self, error: Exception) -> None:
        """
        Handle errors during initialization.

        Args:
            error: The exception that occurred
        """
        logging.warning(f"An error occurred initializing {self.provider_name} with LangChain: {str(error)}")
        err_info = traceback.format_exc()
        logging.warning(f"Detailed error info: {err_info}")

    def _handle_request_error(self, error: Exception, prompt: str) -> str:
        """
        Handle errors during API requests.

        Args:
            error: The exception that occurred
            prompt: The prompt that was being processed

        Returns:
            Error message for the user
        """
        logging.warning(f"An error occurred with {self.provider_name}: {str(error)}")
        err_info = traceback.format_exc()
        logging.warning(f"Detailed error info: {err_info}")
        logging.warning(f"Prompt details: {prompt}")
        return f"Failed to receive a response from the AI (check logs)."

    def _get_initialization_error_message(self) -> str:
        """
        Get a standard error message for initialization failures.

        Returns:
            Error message for the user
        """
        return f"Error: {self.provider_name} models failed to initialize (check logs)."

    def _track_token_usage(self, response) -> None:
        """
        Track token usage from the response if available.

        Args:
            response: The response from the model
        """
        # Default implementation - should be overridden by subclasses if needed
        pass

    def __call__(self, prompt: str) -> Dict[str, str]:
        """
        Make the class callable for compatibility with LangChain.

        Args:
            prompt: The prompt to send

        Returns:
            Dictionary with response
        """
        response = self.send_prompt(prompt)
        return {"text": response}
