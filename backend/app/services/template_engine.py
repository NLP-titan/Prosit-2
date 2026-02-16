from pathlib import Path

from jinja2 import Environment, FileSystemLoader


class TemplateEngine:
    def __init__(self):
        template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            keep_trailing_newline=True,
        )

    async def render_scaffold(self, project_dir: Path, config: dict) -> None:
        """Render all scaffold templates into the project directory."""
        templates = {
            "Dockerfile.j2": "Dockerfile",
            "docker-compose.yml.j2": "docker-compose.yml",
            "requirements.txt.j2": "requirements.txt",
            "main_app.py.j2": "app/main.py",
            "database_setup.py.j2": "app/database.py",
            "dotenv.j2": ".env",
            "gitignore.j2": ".gitignore",
        }

        for template_name, output_path in templates.items():
            template = self.env.get_template(template_name)
            rendered = template.render(**config)

            output_file = project_dir / output_path
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(rendered)

        # Create empty __init__.py for the app package
        (project_dir / "app" / "__init__.py").touch()
