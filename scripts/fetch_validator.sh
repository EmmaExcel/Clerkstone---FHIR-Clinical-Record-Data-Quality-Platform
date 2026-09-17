#!/usr/bin/env bash
# Download the HL7 FHIR validator jar into validator/ (gitignored).
# Pinned to a specific release for reproducibility — bump deliberately.
# The UK Core package (hl7.fhir.uk.core.r4) is resolved by the validator itself
# from the FHIR package registry on first use.
set -euo pipefail

VALIDATOR_VERSION="${VALIDATOR_VERSION:-6.10.4}"

DIR="$(cd "$(dirname "$0")/../validator" && pwd)"
JAR="$DIR/validator_cli.jar"

if [ -f "$JAR" ]; then
  echo "validator_cli.jar already present: $JAR"
  exit 0
fi

echo "Downloading HL7 FHIR validator ${VALIDATOR_VERSION} (validator_cli.jar)…"
curl -fL -o "$JAR" \
  "https://github.com/hapifhir/org.hl7.fhir.core/releases/download/${VALIDATOR_VERSION}/validator_cli.jar"
echo "Downloaded $JAR"
echo
echo "Run the sidecar with:"
echo "  cd validator && UKCORE_PACKAGE_VERSION=hl7.fhir.uk.core.r4@2.4.0 uvicorn app:app --host 0.0.0.0 --port 8080"
