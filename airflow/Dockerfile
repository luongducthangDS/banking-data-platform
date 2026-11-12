FROM apache/airflow:2.10.5-python3.11
# Business code, dbt and Great Expectations live in their own venv so their
# dependencies never clash with Airflow's pinned constraints.
USER root
RUN mkdir -p /opt/app && chown airflow: /opt/app
USER airflow
COPY requirements.txt /tmp/requirements.txt
RUN python -m venv /opt/app/venv && /opt/app/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt
