# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS runtime
WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PRL_MAX_ROWS_FULL=300000 \
    PRL_SAMPLE_N=200000
COPY --from=builder /opt/venv /opt/venv
COPY . .
RUN useradd --system --uid 10001 --create-home appuser \
    && chown -R appuser:appuser /app
USER appuser
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health',timeout=4).status==200 else 1)"
CMD ["sh","-c","streamlit run app.py --server.address=0.0.0.0 --server.headless=true --server.port=${PORT:-8501}"]