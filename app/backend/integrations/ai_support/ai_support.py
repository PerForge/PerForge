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
from typing import List, Optional, Dict, Any

from app.backend.integrations.integration              import Integration
from app.backend.components.prompts.prompts_db         import DBPrompts
from app.backend.integrations.ai_support.ai_support_db import DBAISupport
from app.backend.components.secrets.secrets_db         import DBSecrets
from app.backend.integrations.ai_support.providers.provider_factory import ProviderFactory
from app.backend.integrations.ai_support.providers.provider_base import AIProvider

from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


class AISupport(Integration):
    """
    AISupport class that provides AI analysis capabilities using LangChain.
    Supports multiple AI providers through a provider factory architecture.
    """

    # Flag to enable/disable conversation memory
    ENABLE_CONVERSATION_MEMORY = False

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

        # Get system prompt from database
        prompt_config = DBPrompts.get_config_by_id(id=system_prompt)
        self.system_prompt = prompt_config["prompt"] or "You are a skilled Performance Analyst with strong data analysis expertise. Please help analyze the performance test results."

        # Set configuration at the end of initialization
        self.set_config(id)

    def __str__(self) -> str:
        return f'Integration id is {self.id}'

    def set_config(self, id: Optional[str]) -> None:
        """
        Set the AI configuration based on the provided ID or default configuration.

        Args:
            id: Configuration ID to use, or None to use default
        """
        # Get default config ID if none provided
        id = id if id else DBAISupport.get_default_config(schema_name=self.schema_name)["id"]
        config = DBAISupport.get_config_by_id(schema_name=self.schema_name, id=id)

        if config['id']:
            self.name = config["name"]
            self.ai_provider = config["ai_provider"]
            self.ai_text_model = config["ai_text_model"]
            self.ai_image_model = config["ai_image_model"]
            self.temperature = config["temperature"]

            # Get token from secrets database
            self.token = DBSecrets.get_config_by_id(id=config["token"])["value"]

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

    def _initialize_langchain(self) -> None:
        """Initialize LangChain components based on memory configuration."""
        
        # Define a function to process results and track tokens
        def _process_response(response):
            # Track token usage
            if hasattr(self.ai_obj, '_track_token_usage'):
                self.ai_obj._track_token_usage(response)
            return response.content if hasattr(response, 'content') else response
        
        if self.ENABLE_CONVERSATION_MEMORY:
            # Initialize with conversation memory
            self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

            # Create a prompt template that includes the chat history
            prompt_template = ChatPromptTemplate.from_template(
                "{chat_history}\nHuman: {prompt}\nAI:"
            )

            # Create the chain using the pipe syntax with token tracking
            self.chain = (
                {
                    "chat_history": lambda x: self.memory.load_memory_variables({})["chat_history"],
                    "prompt": RunnablePassthrough()
                }
                | prompt_template
                | self.ai_obj.get_model_for_chain()
                | _process_response  # Add token tracking before string parsing
                | StrOutputParser()
            )

            # Create a function to update memory after each run
            def _update_memory(prompt, response):
                self.memory.save_context({"input": prompt}, {"output": response})
                return response

            # Add memory updating to the chain
            self.run_chain = lambda prompt: _update_memory(prompt, self.chain.invoke(prompt))

            logging.info("AI Support initialized with conversation memory enabled")
        else:
            # Initialize without conversation memory - simpler chain
            prompt_template = PromptTemplate.from_template("{prompt}")

            # Create the chain using the pipe syntax with token tracking
            self.chain = (
                prompt_template 
                | self.ai_obj.get_model_for_chain() 
                | _process_response  # Add token tracking before string parsing
                | StrOutputParser()
            )

            # Simple run function that just invokes the chain
            self.run_chain = lambda prompt: self.chain.invoke(prompt)

            logging.info("AI Support initialized with conversation memory disabled")

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
        if not self.models_created or not self.ai_obj:
            return "Error: AI models not initialized"

        if not prompt_id or not graph:
            return ""

        prompt_value = DBPrompts.get_config_by_id(id=prompt_id)["prompt"]

        # Use the AI object directly for image analysis since LangChain doesn't handle images well
        response = self.ai_obj.analyze_graph(graph, prompt_value)

        # If memory is enabled, save this interaction to memory
        if self.ENABLE_CONVERSATION_MEMORY and hasattr(self, 'memory'):
            self.memory.save_context(
                {"input": f"[Graph Analysis Request: {name}] {prompt_value}"},
                {"output": response}
            )

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
            prompt_value = DBPrompts.get_config_by_id(id=prompt_id)["prompt"]
            prompt_value = prompt_value + "\n\n" + str(data)

            # Use the chain with or without memory
            result = self.run_chain(prompt_value)
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

    def create_template_summary(self, prompt_id: str, nfr_summary: str, ml_anomalies: Optional[str] = None) -> str:
        """
        Create a summary based on all analyses and NFR results.

        Args:
            prompt_id: ID of the prompt to use for summary
            nfr_summary: NFR analysis summary
            ml_anomalies: Optional ML anomalies data

        Returns:
            Generated summary
        """
        if not self.models_created:
            return "Error: AI failed to initialize."

        prompt_value = DBPrompts.get_config_by_id(id=prompt_id)["prompt"]

        # Replace placeholders with actual data
        prompt_value = prompt_value.replace("[aggregated_data_analysis]", self.prepare_list_of_analysis(self.aggregated_data_analysis))
        prompt_value = prompt_value.replace("[graphs_analysis]", self.prepare_list_of_analysis(self.graph_analysis))
        prompt_value = prompt_value.replace("[nfr_summary]", nfr_summary)

        if ml_anomalies:
            prompt_value = prompt_value.replace("[ml_anomalies]", str(ml_anomalies))

        # Use the chain with or without memory
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

        prompt_value = DBPrompts.get_config_by_id(id=prompt_id)["prompt"]

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
        if self.ENABLE_CONVERSATION_MEMORY and hasattr(self, 'memory'):
            self.memory.clear()
            logging.info("Conversation memory cleared")
