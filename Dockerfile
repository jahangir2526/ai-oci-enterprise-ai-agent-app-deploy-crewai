FROM container-registry.oracle.com/os/oraclelinux:9-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    CREWAI_STORAGE_DIR=/tmp/crewai \
    OTEL_SDK_DISABLED=true

WORKDIR /app

RUN microdnf update -y && \
    microdnf install -y python3.11 python3.11-pip ca-certificates shadow-utils && \
    microdnf clean all && \
    rm -rf /var/cache/dnf /var/cache/yum

COPY requirements.txt .
RUN python3.11 -m pip install --no-cache-dir --upgrade pip setuptools wheel && \
    python3.11 -m pip install --no-cache-dir -r requirements.txt

COPY src ./src

RUN useradd --create-home --uid 1000 appuser && \
    install -d -m 700 -o appuser -g appuser /home/appuser/.local/share/crewai/credentials && \
    python3.11 -c "from cryptography.fernet import Fernet; open('/home/appuser/.local/share/crewai/credentials/secret.key', 'wb').write(Fernet.generate_key())" && \
    chown appuser:appuser /home/appuser/.local/share/crewai/credentials/secret.key && \
    chmod 600 /home/appuser/.local/share/crewai/credentials/secret.key && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["python3.11", "-m", "uvicorn", "ai_oci_enterprise_ai_hosted_deployment_crewai.main:app", "--host", "0.0.0.0", "--port", "8080"]
