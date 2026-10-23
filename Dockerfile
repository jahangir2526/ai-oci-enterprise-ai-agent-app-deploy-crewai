FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CREWAI_STORAGE_DIR=/tmp/crewai \
    OTEL_SDK_DISABLED=true

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install -r requirements.txt

COPY src ./src
COPY main.py .

RUN useradd --create-home --uid 1000 appuser && \
    install -d -m 700 -o appuser -g appuser /home/appuser/.local/share/crewai/credentials && \
    python -c "from cryptography.fernet import Fernet; open('/home/appuser/.local/share/crewai/credentials/secret.key', 'wb').write(Fernet.generate_key())" && \
    chown appuser:appuser /home/appuser/.local/share/crewai/credentials/secret.key && \
    chmod 600 /home/appuser/.local/share/crewai/credentials/secret.key && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["python", "main.py"]
