"""FHIR validator sidecar: an HTTP wrapper around the HL7 FHIR validator jar.

Receives a single resource, runs ``validator_cli.jar`` against the UK Core
package, and returns the resulting OperationOutcome. The API's ``$validate``
calls this; when the sidecar is down the API falls back to structural
validation (see app/domain/fhir/validator.py).

NOTE: the exact jar invocation should be confirmed against ``validator_cli.jar
-help`` once the jar is downloaded (scripts/fetch_validator.sh).
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Clerkstone FHIR validator sidecar")

_VALIDATOR_JAR = Path(__file__).resolve().parent / "validator_cli.jar"
# Pin the UK Core package version; override via the UKCORE_PACKAGE_VERSION env var
# (docker-compose passes it through from .env).
_UKCORE_PACKAGE = os.getenv("UKCORE_PACKAGE_VERSION", "hl7.fhir.uk.core.r4@2.4.0")


class ValidateRequest(BaseModel):
    resource: dict


@app.post("/validate")
def validate(req: ValidateRequest) -> dict:
    if not _VALIDATOR_JAR.exists():
        return {
            "resourceType": "OperationOutcome",
            "issue": [
                {
                    "severity": "error",
                    "code": "not-found",
                    "diagnostics": "validator_cli.jar not present; run scripts/fetch_validator.sh",
                }
            ],
        }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fh:
        json.dump(req.resource, fh)
        path = fh.name
    out_path = path + ".out.json"
    try:
        cmd = [
            "java", "-jar", str(_VALIDATOR_JAR), path,
            "-version", "4.0.1",
            "-ig", _UKCORE_PACKAGE,
            "-output", out_path,
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
        return _read_outcome(out_path)
    except subprocess.TimeoutExpired:
        return {"resourceType": "OperationOutcome",
                "issue": [{"severity": "error", "code": "timeout",
                           "diagnostics": "validator timed out"}]}
    finally:
        Path(path).unlink(missing_ok=True)
        Path(out_path).unlink(missing_ok=True)


def _read_outcome(path: str) -> dict:
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return {"resourceType": "OperationOutcome",
                "issue": [{"severity": "error", "code": "invalid",
                           "diagnostics": "validator produced no parseable outcome"}]}
