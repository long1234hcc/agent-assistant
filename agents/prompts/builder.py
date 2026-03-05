from jinja2 import Environment, FileSystemLoader
import os


class PromptBuilder:
    def __init__(self, template_dir: str = None):
        if template_dir is None:
            # Tự động tìm đúng folder dù chạy từ đâu
            template_dir = os.path.join(
                os.path.dirname(__file__),  # folder hiện tại = prompts/
                "templates"
            )
        self.env = Environment(
            loader=FileSystemLoader(template_dir)
        )

    def build_system_prompt(self, **kwargs) -> str:

        template = self.env.get_template("system.j2")
        return template.render(**kwargs)
