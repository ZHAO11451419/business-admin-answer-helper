# BAH GPU IMAGE
FROM vllm/vllm-openai:v0.8.5@sha256:6cf9808ca8810fc6c3fd0451c2e7784fb224590d81f7db338e7eaf3c02a33d33

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/backend:/app
ENV HF_HOME=/root/.cache/huggingface
ENV VLLM_HOST=127.0.0.1
ENV VLLM_PORT=8000
ENV API_HOST=0.0.0.0
ENV API_PORT=8080

WORKDIR /app

COPY backend /app/backend
COPY scripts /app/scripts
COPY configs /app/configs
COPY inference /app/inference

# Do not install/upgrade vLLM here. The pinned base image owns the vLLM/PyTorch/CUDA stack.
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    httpx \
    pydantic \
    pydantic-settings \
    python-dotenv \
    huggingface_hub

EXPOSE 8080
ENTRYPOINT ["/app/inference/entrypoint.sh"]
