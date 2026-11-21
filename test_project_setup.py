import unittest
from pathlib import Path


class ProjectSetupTests(unittest.TestCase):
    def test_readme_documents_devops(self):
        readme = Path("README.md").read_text(encoding="utf-8")
        self.assertIn("## DevOps", readme)
        self.assertIn("docker compose", readme)

    def test_environment_template_exists(self):
        template = Path(".env.example").read_text(encoding="utf-8")
        for name in (
            "GEMINI_API_KEY",
            "OPENWEATHER_API_KEY",
            "ALPHA_VANTAGE_API_KEY",
            "NEWS_API_KEY",
        ):
            self.assertIn(f"{name}=", template)


if __name__ == "__main__":
    unittest.main()
