from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).parents[1]


class ProjectFilesTests(unittest.TestCase):
    def test_workflows_use_verified_action_majors_and_no_named_secrets(self):
        workflows = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / ".github" / "workflows").glob("*.yml"))
        for action in (
            "actions/checkout@v7", "actions/setup-python@v7", "actions/configure-pages@v6",
            "actions/upload-pages-artifact@v5", "actions/deploy-pages@v5",
        ):
            self.assertIn(action, workflows)
        self.assertIn("cron:", workflows)
        self.assertIn("python -m unittest discover", workflows)
        self.assertNotIn("secrets.", workflows)

    def test_refresh_cli_is_runnable(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "refresh.py"), "--help"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("--config", result.stdout)
        self.assertIn("--data", result.stdout)
        self.assertIn("--report", result.stdout)

    def test_readme_and_license_exist(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Local use", readme)
        self.assertIn("Data and ranking", readme)
        self.assertIn("Source failures", readme)
        self.assertTrue((ROOT / "LICENSE").is_file())


if __name__ == "__main__":
    unittest.main()
