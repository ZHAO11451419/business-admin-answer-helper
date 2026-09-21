# This image contains both vLLM and the BAH FastAPI gateway.
# Pin VLLM_IMAGE to a tested vLLM tag/digest for production reproducibility.
ARG VLLM_IMAGE=vllm/vllm-openai:latest
FROM ${VLLM_IMAGE}

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY scripts /app/scripts
COPY inference /app/inference

ENV PYTHONPATH=/app/backend:/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/root/.cache/huggingface
ENV PUBLIC_PORT=8080

EXPOSE 8080

ENTRYPOINT ["/app/inference/entrypoint.sh"]
