import os

from app.backend                 import pkg


class PromptConfig:
    def __init__(self, project):
        self.project         = project
        self.default_prompts = self.get_default_prompts()
        self.custom_prompts  = self.get_custom_prompts(project)

    @staticmethod
    def get_default_prompts():
        file_path    = os.path.join("app", "backend", "components", "prompts", "prompts.yaml")
        yaml_prompts = pkg.read_from_yaml(file_path)
        return yaml_prompts['prompts']

    @staticmethod
    def get_custom_prompts(project):
        data = pkg.get_project_config(project)
        return data["prompts"]

    def get_prompt_value_by_id(self, id):
        # Search in default prompts
        for prompt in self.default_prompts:
            if prompt['id'] == id:
                return prompt['prompt']
        # Search in custom prompts
        for prompt in self.custom_prompts:
            if prompt['id'] == id:
                return prompt['prompt']
        return None