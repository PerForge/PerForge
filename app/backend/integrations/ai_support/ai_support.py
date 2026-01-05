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
from typing import List, Optional, Any
import uuid

from app.backend.integrations.integration import Integration
from app.backend.components.prompts.prompts_db import DBPrompts
from app.backend.integrations.ai_support.ai_support_db import DBAISupport
from app.backend.components.secrets.secrets_db import DBSecrets
from app.backend.integrations.ai_support.providers.provider_factory import ProviderFactory
from app.backend.integrations.ai_support.providers.provider_base import AIProvider

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.output_parsers import StrOutputParser


class AISupport(Integration):
    """
    AISupport class that provides AI analysis capabilities using LangChain.
    Supports multiple AI providers through a provider factory architecture.
    """

    def __init__(self, project, system_prompt, id = None):
        """
        Initialize the AISupport integration.

        Args:
            project: The project context
            system_prompt: The ID of the system prompt to use
            id: Optional configuration ID
        """
        super().__init__(project)
        self.models_created: bool = False
        self.graph_analysis: List[str] = []
        self.aggregated_data_analysis: List[str] = []
        self.summary: List[str] = []
        self.ai_obj: Optional[AIProvider] = None

        # Create a unique session ID for this instance using UUID
        self.session_id: str = f"session_{project}_{uuid.uuid4().hex[:8]}"

        # Get system prompt from database
        prompt_config = DBPrompts.get_config_by_id(project_id=self.project, id=system_prompt)
        self.system_prompt = prompt_config["prompt"] or "You are a skilled Performance Analyst with strong data analysis expertise. Please help analyze the performance test results."

        # Set configuration at the end of initialization
        self.set_config(id)

    def __str__(self) -> str:
        return f'Integration id is {self.id}'

    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        if session_id not in self.store:
            self.store[session_id] = ChatMessageHistory()
        return self.store[session_id]

    def set_config(self, id: Optional[str]) -> None:
        """
        Set the AI configuration based on the provided ID or default configuration.

        Args:
            id: Configuration ID to use, or None to use default
        """
        # Get default config ID if none provided
        id = id if id else DBAISupport.get_default_config(project_id=self.project)["id"]
        config = DBAISupport.get_config_by_id(project_id=self.project, id=id)

        if config['id']:
            self.name = config["name"]
            self.ai_provider = config["ai_provider"]
            self.ai_text_model = config["ai_text_model"]
            self.ai_image_model = config["ai_image_model"]
            self.temperature = config["temperature"]
            self.conversation_memory = config["conversation_memory"]

            # Get token from secrets database
            self.token = DBSecrets.get_config_by_id(project_id=self.project, id=config["token"])["value"]

            # Common provider arguments
            provider_args = {
                "ai_text_model": self.ai_text_model,
                "ai_image_model": self.ai_image_model,
                "token": self.token,
                "temperature": self.temperature,
                "system_prompt": self.system_prompt
            }

            # Add Azure-specific arguments if needed
            if self.ai_provider == "azure_openai":
                provider_args["azure_url"] = config["azure_url"]
                provider_args["api_version"] = config["api_version"]

            # Create the provider using the factory
            self.ai_obj = ProviderFactory.create_provider(
                provider_type=self.ai_provider,
                **provider_args
            )

            if self.ai_obj:
                self.models_created = True

                # Initialize LangChain with or without memory based on flag
                self._initialize_langchain()
            else:
                logging.error(f"Failed to create provider for {self.ai_provider}")
        else:
            logging.warning("There's no AI integration configured, or you're attempting to send a request from an unsupported location.")

    def _initialize_langchain(self):
        # Initialize LangChain components based on memory configuration.

        if self.conversation_memory:
            self.store = {}

            self.prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt),
                ("placeholder", "{chat_history}"),
                ("human", "{input}"),
            ])

            chain = self.prompt | self.ai_obj | StrOutputParser()

            self.chain_with_history = RunnableWithMessageHistory(
                chain,
                self.get_session_history,
                input_messages_key="input",
                history_messages_key="chat_history",
            )
        else:
            self.prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt),
                ("human", "{input}"),
            ])
            self.chain = self.prompt | self.ai_obj | StrOutputParser()

        self.models_created = True

    def run_chain(self, prompt_value: str) -> str:
        if self.conversation_memory:
            return self.chain_with_history.invoke(
                {"input": prompt_value},
                config={"configurable": {"session_id": self.session_id}})
        else:
            return self.chain.invoke({"input": prompt_value})

    def analyze_graph(self, name: str, graph, prompt_id: str) -> str:
        """
        Analyze a graph image using AI.

        Args:
            name: Name of the graph
            graph: Binary image data of the graph
            prompt_id: ID of the prompt to use for analysis

        Returns:
            Analysis result as string
        """
        if not self.models_created:
            return "Error: AI failed to initialize."

        prompt_value = DBPrompts.get_config_by_id(project_id=self.project, id=prompt_id)["prompt"]

        # Use the AI object directly for image analysis since LangChain doesn't handle images well
        response = self.ai_obj.analyze_graph(graph, prompt_value)

        # If memory is enabled, save this interaction to memory
        if self.conversation_memory and hasattr(self, 'chain_with_history'):
            history = self.get_session_history(self.session_id)
            history.add_user_message(f"[Graph Analysis Request: {name}] {prompt_value}")
            history.add_ai_message(response)

        # Store analysis results
        self.graph_analysis.append(name)
        self.graph_analysis.append(response)

        return response

    def analyze_aggregated_data(self, data: Any, prompt_id: str) -> None:
        """
        Analyze aggregated data using AI.

        Args:
            data: Data to analyze
            prompt_id: ID of the prompt to use for analysis
        """
        if not self.models_created:
            logging.warning("Cannot analyze data: AI models not initialized")
            return

        try:
            prompt_value = DBPrompts.get_config_by_id(project_id=self.project, id=prompt_id)["prompt"]
            prompt_value = prompt_value + "\n\n" + str(data)

            # Use the chain with or without memory
            result = self.run_chain(prompt_value)

            # If memory is enabled, manually add this interaction to memory
            if self.conversation_memory and hasattr(self, 'chain_with_history'):
                history = self.get_session_history(self.session_id)
                history.add_user_message(f"[Aggregated Data Analysis Request] {prompt_value}")
                history.add_ai_message(result)

            self.aggregated_data_analysis.append(result)

        except Exception as er:
            logging.warning("An error occurred: " + str(er))
            err_info = traceback.format_exc()
            logging.warning("Detailed error info: " + err_info)

    def prepare_list_of_analysis(self, analysis_list: List[str]) -> str:
        """
        Prepare a formatted string from a list of analysis results.

        Args:
            analysis_list: List of analysis strings

        Returns:
            Formatted string with all analyses
        """
        result = ""
        for obj in analysis_list:
            result += obj
            result += "\n\n"
        return str(result)

    def run_summary_chain(self, prompt_value: str) -> str:
        """
        Run the AI chain with a pre-processed prompt and store result in summary.

        This method expects the prompt to already have all variables replaced.
        Use this when the calling code handles variable replacement.

        Args:
            prompt_value: The fully processed prompt with all variables replaced

        Returns:
            The generated summary as a string
        """
        if not self.models_created:
            return "Error: AI failed to initialize."

        result = self.run_chain(prompt_value)
        self.summary.append(result)
        return result

    def create_template_summary(self, prompt_id: str, nfr_summary: str, ml_summary: Optional[str] = None, additional_context: Optional[str] = None) -> str:
        """
        Create a summary based on all analyses and NFR results using a template prompt.

        DEPRECATED: This method is kept for backward compatibility but uses manual replacement.
        Consider using run_summary_chain() with ReportingBase.replace_variables() instead.

        Args:
            prompt_id: ID of the prompt to use for the summary.
            nfr_summary: The NFR analysis summary string.
            ml_summary: Optional ML analysis summary string.
            additional_context: Optional additional context string.

        Returns:
            The generated summary as a string.
        """
        if not self.models_created:
            return "Error: AI failed to initialize."

        prompt_template = DBPrompts.get_config_by_id(project_id=self.project, id=prompt_id)["prompt"]

        replacements = {
            "aggregated_data_analysis": self.prepare_list_of_analysis(self.aggregated_data_analysis) or "N/A",
            "graphs_analysis": self.prepare_list_of_analysis(self.graph_analysis) or "N/A",
            "nfr_summary": nfr_summary or "N/A",
            "ml_summary": ml_summary or "N/A",
            "additional_context": additional_context or "N/A"
        }

        prompt_value = prompt_template
        for key, value in replacements.items():
            placeholder = f"${{{key}}}"
            prompt_value = prompt_value.replace(placeholder, str(value))

        # Run the chain to get the final summary
        result = self.run_chain(prompt_value)
        self.summary.append(result)

        return result

    def create_template_group_summary(self, prompt_id: str) -> str:
        """
        Create a group summary based on all individual summaries.

        Args:
            prompt_id: ID of the prompt to use for group summary

        Returns:
            Generated group summary
        """
        if not self.models_created:
            return "Error: AI failed to initialize."

        prompt_value = DBPrompts.get_config_by_id(project_id=self.project, id=prompt_id)["prompt"]

        # Add all individual summaries to the prompt
        for text in self.summary:
            prompt_value = prompt_value + "\n" + text

        # Use the chain with or without memory
        result = self.run_chain(prompt_value)

        return result

    def clear_conversation_memory(self) -> None:
        """
        Clear the conversation memory if it's enabled.

        This is useful when starting a new analysis session.
        """
        if self.conversation_memory and hasattr(self, 'store'):
            if self.session_id in self.store:
                self.store[self.session_id].clear()
                logging.info(f"Conversation memory cleared for session: {self.session_id}")
