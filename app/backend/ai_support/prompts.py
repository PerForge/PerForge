import os

from app.backend import pkg


class Prompt:
    def __init__(self, project):
        self.project         = project
        self.default_prompts = self.get_default_prompts()
        self.custom_prompts  = self.get_custom_prompts(project)

    @staticmethod
    def get_default_prompts():
        file_path    = os.path.join("app", "data", "prompts.yaml")
        yaml_prompts = pkg.read_from_yaml(file_path)
        return yaml_prompts['prompts']

    @staticmethod
    def get_custom_prompts(project):
        pkg.validate_config(project, "prompts")
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
        pkg.validate_config(project, "prompts")
        data            = pkg.get_project_config(project)
        prompt_id       = form.get("id")
        existing_prompt = next((prompt for prompt in data["prompts"] if prompt["id"] == prompt_id), None)
        if not existing_prompt:
            form["id"] = pkg.generate_unique_id()
            data["prompts"].append(form)
        else:
            existing_prompt.update(form)
        pkg.save_new_data(project, data)
        return form.get("id")

    def delete_custom_prompt(project, id):
        pkg.validate_config(project, "prompts")
        data = pkg.get_project_config(project)
        for idx, obj in enumerate(data["prompts"]):
            if obj["id"] == id:
                data["prompts"].pop(idx)
                break
        pkg.save_new_data(project, data)