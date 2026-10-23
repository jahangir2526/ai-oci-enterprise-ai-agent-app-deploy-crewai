import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


# Keep deterministic local tests from exporting telemetry or prompting for traces.
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_TRACING_ENABLED"] = "false"


# CrewAI initializes its internal app-data directory during import. Keep that
# framework-internal test state in the operating system's temporary directory.
os.environ.setdefault(
    "CREWAI_STORAGE_DIR",
    str(Path(tempfile.gettempdir()) / "crewai-answer-studio-test"),
)

# CrewAI's trace listener also initializes its credential store during import,
# even when tracing is disabled. Redirect that framework-internal path in tests.
from crewai_core.token_manager import TokenManager


credential_path = Path(tempfile.gettempdir()) / "crewai-answer-studio-credentials"
credential_path.mkdir(parents=True, exist_ok=True)
TokenManager._get_secure_storage_path = staticmethod(lambda: credential_path)
