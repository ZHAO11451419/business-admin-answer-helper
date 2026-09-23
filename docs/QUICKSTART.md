# BAH Web 快速启动指南

## 前置要求

- **Docker Desktop**（已安装 WSL2 后端）
- **NVIDIA GPU**，显存至少 **8GB**（推荐 16GB+）
- NVIDIA 驱动支持 CUDA 12.x
- Hugging Face token（免费注册：https://huggingface.co/settings/tokens）

> 没有 GPU？可以用 `INFERENCE_MODE=mock` 跑通前端流程，但不会真正调用模型。

## 3 步启动

### 1. 克隆仓库

```bash
git clone https://github.com/ZHAO11451419/business-admin-answer-helper.git
cd business-admin-answer-helper
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，至少填写：

```env
HF_TOKEN=hf_你的token
VLLM_API_KEY=随便一串长密码
ADMIN_KEY=另一串长密码
```

### 3. 一键启动

```bash
docker compose up -d
```

首次启动会：
1. 拉取 vLLM v0.8.5 镜像（约 26GB，需要几分钟）
2. 下载 Qwen2.5-3B-Instruct-AWQ 模型权重（约 2GB）
3. 下载 BAH LoRA 适配器（约 50MB）
4. 启动 FastAPI 网关（端口 8080）

查看启动状态：

```bash
docker compose logs -f bah-gpu
```

看到 `Application startup complete` 就表示就绪了。

## 访问

- **API 健康检查**：http://localhost:8080/api/health
- **API 文档**：http://localhost:8080/docs

## 启动前端（另开终端）

```bash
cd frontend
npm install
cp .env.example .env.local
# 编辑 .env.local，设置 NEXT_PUBLIC_API_BASE_URL=http://localhost:8080
npm run dev
```

浏览器打开 http://localhost:3000

## 常见问题

### GPU 显存不足

8GB 显存用默认配置即可（AWQ 量化版）。如果还是 OOM，降低：

```env
GPU_MEMORY_UTILIZATION=0.75
MAX_MODEL_LEN=2048
```

### 模型下载慢/失败

设置 HuggingFace 镜像：

```env
HF_ENDPOINT=https://hf-mirror.com
```

### 查看日志

```bash
docker compose logs -f bah-gpu
```

### 停止服务

```bash
docker compose down
```

## 生产部署

详见 [docs/WEB_DEPLOYMENT.md](docs/WEB_DEPLOYMENT.md)。
