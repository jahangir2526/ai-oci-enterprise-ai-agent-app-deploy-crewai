"""Start the local API server with ``python main.py``."""

import sys
from pathlib import Path


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
    from ai_oci_enterprise_ai_hosted_deployment_crewai.main import run

    run()
