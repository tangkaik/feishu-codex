"""Project-local environment loading."""

from pathlib import Path
import os


PROJECT_DIR = Path(__file__).resolve().parent
PROJECT_ENV_FILE = PROJECT_DIR / ".env"


def load_env_file(env_path: Path = PROJECT_ENV_FILE) -> bool:
    """Load KEY=VALUE lines from the project .env without overwriting process env."""
    env_path = Path(env_path).expanduser()
    if not env_path.exists():
        return False

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    return True
