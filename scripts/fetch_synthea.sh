#!/usr/bin/env bash
# Download the Synthea simulator JAR into scripts/synthea/ (gitignored).
# Synthea is Apache-2.0 — see docs/DATA_LICENCES.md and the Walonoski et al. (2018) citation.
set -euo pipefail

BASE="$(cd "$(dirname "$0")" && pwd)"
DIR="$BASE/synthea"
mkdir -p "$DIR"
JAR="$DIR/synthea-with-dependencies.jar"

if [ -f "$JAR" ]; then
  echo "Synthea JAR already present: $JAR"
  exit 0
fi

echo "Downloading Synthea JAR (Apache-2.0)…"
curl -fL -o "$JAR" \
  "https://github.com/synthetichealth/synthea/releases/latest/download/synthea-with-dependencies.jar"
echo "Downloaded $JAR"
echo
echo "Run the simulator with, e.g.:"
echo "  java -jar $JAR -p 500 -s 42 --exporter.fhir.export true"
