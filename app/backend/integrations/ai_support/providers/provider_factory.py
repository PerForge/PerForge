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
from typing import Dict, Optional, Type

from app.backend.integrations.ai_support.providers.provider_base import AIProvider
from app.backend.integrations.ai_support.providers.gemini_provider import GeminiProvider
from app.backend.integrations.ai_support.providers.open_provider import OpenAIProvider, AzureOpenAIProvider


class ProviderFactory:
    """
    Factory class for creating AI provider instances.

    This class is responsible for creating the appropriate AI provider based on
    the configuration. It makes it easy to add new providers in the future.
    """

    # Registry of available providers
    _providers = {
        "gemini": GeminiProvider,
        "openai": OpenAIProvider,
        "azure_openai": AzureOpenAIProvider
    }

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[AIProvider]) -> None:
        """
        Register a new provider with the factory.

        Args:
            name: Name of the provider
            provider_class: Provider class to register
        """
        cls._providers[name] = provider_class
        logging.info(f"Registered new AI provider: {name}")

    @classmethod
    def create_provider(cls, provider_type: str, **kwargs) -> Optional[AIProvider]:
        """
        Create a provider instance based on the provider type.

        Args:
            provider_type: Type of provider to create
            **kwargs: Arguments to pass to the provider constructor

        Returns:
            Provider instance or None if the provider type is not supported
        """
        if provider_type not in cls._providers:
            logging.warning(f"Unsupported provider type: {provider_type}")
            return None

        try:
            provider_class = cls._providers[provider_type]
            return provider_class(**kwargs)
        except Exception as e:
            logging.error(f"Failed to create provider {provider_type}: {str(e)}")
            return None

    @classmethod
    def get_available_providers(cls) -> Dict[str, Type[AIProvider]]:
        """
        Get a dictionary of available providers.

        Returns:
            Dictionary mapping provider names to provider classes
        """
        return cls._providers.copy()
