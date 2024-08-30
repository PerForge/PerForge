import os

from app.backend                 import pkg
from app.backend.pydantic_models import PromptModel


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

    def get_prompts_by_place(self, place):
        filtered_prompts = [
            prompt for prompt in self.default_prompts if prompt['place'] == place
        ] + [
            prompt for prompt in self.custom_prompts if prompt['place'] == place
        ]
        return filtered_prompts

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

    def save_custom_prompt(project, form):
        validated_form           = PromptModel.model_validate(form).model_dump()
        config_data              = pkg.get_project_config(project)
        prompt_id                = validated_form.get("id")
        existing_prompt_index    = next((index for index, p in enumerate(config_data["prompts"]) if p["id"] == prompt_id), None)
        validated_form["prompt"] = validated_form.get("prompt").replace('"', "'").replace('\r', '')
        if existing_prompt_index is None:
            validated_form["id"] = pkg.generate_unique_id()
            config_data["prompts"].append(validated_form)
        else:
            config_data["prompts"][existing_prompt_index] = validated_form
        pkg.save_new_data(project, config_data)
        return validated_form.get("id")

    def delete_custom_prompt(project, id):
        data           = pkg.get_project_config(project)
        prompt_deleted = False
        for idx, obj in enumerate(data["prompts"]):
            if obj["id"] == id:
                data["prompts"].pop(idx)
                prompt_deleted = True
                break
        if prompt_deleted:
            for graph in data.get("graphs", []):
                if graph.get("prompt_id") == id:
                    graph["prompt_id"] = ""
            for template in data.get("templates", []):
                if template.get("template_prompt_id") == id:
                    template["template_prompt_id"] = ""
                if template.get("aggregated_prompt_id") == id:
                    template["aggregated_prompt_id"] = ""
            for template_group in data.get("template_groups", []):
                if template_group.get("prompt_id") == id:
                    template_group["prompt_id"] = ""
        pkg.save_new_data(project, data)