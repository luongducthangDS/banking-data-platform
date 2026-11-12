# Image for the Python services (dq-api, assistant-api, assistant-ui).
FROM python:3.11-slim
WORKDIR /opt/project
COPY requirements.txt requirements-assistant.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-assistant.txt
COPY pipeline pipeline
COPY dq dq
COPY assistant assistant
