# FHIR validator sidecar — JRE (for the validator jar) + Python (for the HTTP
# wrapper). Pin both the validator jar and the UK Core package version for
# reproducibility; bump VALIDATOR_VERSION deliberately, never "latest".
ARG VALIDATOR_VERSION=6.10.4
FROM eclipse-temurin:17-jre-jammy
ARG VALIDATOR_VERSION

WORKDIR /opt/validator

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY app.py ./

# Pinned HL7 FHIR validator jar (fetched at build time; not committed).
RUN curl -fsSL -o validator_cli.jar \
      "https://github.com/hapifhir/org.hl7.fhir.core/releases/download/${VALIDATOR_VERSION}/validator_cli.jar"

ENV UKCORE_PACKAGE_VERSION=hl7.fhir.uk.core.r4@2.4.0

RUN useradd --create-home --uid 1001 validator && chown -R validator:validator /opt/validator
USER validator

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/docs')"]

CMD ["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
