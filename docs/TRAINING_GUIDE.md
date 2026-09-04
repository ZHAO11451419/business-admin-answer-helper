# Training Guide — Business Admin Answer Helper

从零训练、评估、发布 `business-admin-answer-helper` 的完整操作手册。目标基座模型：**Qwen2.5-7B-Instruct**（Apache 2.0 开源，可商用）。方法：**QLoRA**（4-bit 量化 + LoRA 适配器）。

---

## 0. 前置要求

- **数据**：`data/train.jsonl`（444 对）已在本仓库，无需准备
- **GPU**：推荐免费 Colab T4（16GB）或任意 ≥16GB 显存的 GPU
- **不需要**：任何 UPM 内部资料 / 教材原文（数据全部是原创与公开事实改写，可安全开源）

---

## 1. 方式 A（推荐）：Colab T4 一键训练

1. 打开 https://colab.research.google.com → 文件 → 上传笔记本
   - 上传本仓库 `notebooks/finetune_qwen25_colab.ipynb`
2. **Runtime → Change runtime type → T4 GPU**
3. 从上到下依次运行 cell：
   - Cell 1：安装依赖（约 1-2 分钟）
   - Cell 2：从 GitHub 下载 `train.jsonl`（444 对）
   - Cell 3：4-bit 加载 Qwen2.5-7B（QLoRA）
   - Cell 4：挂载 LoRA 适配器（仅 ~1.7% 参数可训练）
   - Cell 5：**训练**（3 epochs，T4 约 25-40 分钟）
   - Cell 6：合并适配器 → 16-bit 独立模型
   - Cell 7：实测答题（检查格式遵循）
   - Cell 8：（可选）推送到 Hugging Face
4. 训练期间如果中断：checkpoint 保存在 `outputs/business-admin-answer-helper/checkpoint-*`，可下载到本地留档

> **参数建议**：444 条数据量小，`EPOCHS=3` 起步；若验证集 loss 仍在下降，可提到 5。`LR=2e-4`、`r=16`、`lora_alpha=32` 是稳妥默认值。

---

## 2. 方式 B：本地 / 任意 GPU

```bash
pip install -U torch transformers peft trl datasets accelerate bitsandbytes

# 1) 校验 + 分层划分（生成 train/val_prepared.jsonl）
python scripts/prepare_dataset.py

# 2) 完整 QLoRA 训练
python scripts/train_lora.py \
    --model_name Qwen/Qwen2.5-7B-Instruct \
    --data data/train.jsonl \
    --output_dir outputs/business-admin-answer-helper \
    --epochs 3 --lr 2e-4 --batch_size 2 --grad_accum 8 --use_4bit
```

产物：
- `outputs/.../adapter/` — LoRA 适配器（小，可放进 GitHub 之外另行存档）
- `outputs/.../merged/` — 合并后的 16-bit 独立模型（发布用）

### 无 GPU 冒烟验证（可选）

```bash
python scripts/train_lora.py --smoke --model_name Qwen/Qwen2.5-0.5B-Instruct
```
只跑 2 步，验证"加载 → LoRA → 格式化 → 训练 → 保存"链路，任何机器可跑。

---

## 3. 评估训练效果

```bash
# 用留出的验证集（45 条）评估格式遵循率 + 计算准确率
python scripts/evaluate.py \
    --model outputs/business-admin-answer-helper/merged \
    --test data/val_prepared.jsonl --split 1.0
```

评估脚本按题型检查评分者真正看重的东西：

| 题型 | 检查项 |
|---|---|
| calculation | 有公式 / 有代入过程 / 有业务解读 / 最终数字与参考答案匹配 |
| concept | 有定义 / 有例子 |
| case | 有明确判断（should/should not）/ 有编号理由 |
| essay | 有编号小节 / 有哈佛式文内引用 |

> 参考实现：`docs/answering-guide.md` 定义了全部格式规范，evaluate.py 的正则即从其中提炼。

---

## 4. 本地演示

```bash
pip install gradio
python scripts/serve.py --model outputs/business-admin-answer-helper/merged
# 浏览器打开 http://127.0.0.1:7860
```

---

## 5. 发布到 Hugging Face

GitHub 只放代码 + 数据（`*.safetensors` 已被 `.gitignore` 忽略）。**模型权重发布到 Hugging Face**：

1. 注册/登录 https://huggingface.co
2. 创建 write 权限 token：https://huggingface.co/settings/tokens
3. 在 Colab 笔记本 Cell 8 运行（或本地执行）：

```python
from huggingface_hub import notebook_login, HfApi
notebook_login()   # 粘贴 token

REPO = "business-admin-answer-helper"
api = HfApi()
api.create_repo(repo_id=REPO, exist_ok=True)
api.upload_folder(
    folder_path="outputs/business-admin-answer-helper/merged",
    repo_id=REPO, repo_type="model",
)
```

发布后把仓库链接填进 `README.md` 的 "Model weights" 一节，本项目即完整闭环。

> 中国大陆网络建议先设置镜像：`export HF_ENDPOINT=https://hf-mirror.com`

---

## 6. 常见问题

| 问题 | 解决 |
|---|---|
| `TrainingArguments unexpected keyword 'warmup_ratio'` | 已适配：用 `warmup_steps`（脚本自动计算） |
| `SFTTrainer unexpected keyword 'tokenizer'` | 已适配：改用 `processing_class` |
| `SFTTrainer unexpected keyword 'max_seq_length'` | 已适配：改到 `SFTConfig(max_length=...)` |
| `formatting_func` 报 dict 错误 | 已适配：`formatting_func` 须直接返回字符串 |
| Colab 报 CUDA OOM | 减少 `--batch_size` 到 1，或 `max_length` 从 2048 降到 1024 |
| 想换基座（DeepSeek/Llama） | 改 `--model_name`，LoRA target_modules 按模型结构调整 |

---

## 7. 数据合规说明

- 训练数据全部为**原创改写 + 公开事实**（NSRF/Bursa/Maybank 等均为官方公开披露），无教材原文、无同学个人信息
- 基座模型 Qwen2.5-7B-Instruct 为 Apache-2.0 开源，微调产物可开源发布
- 使用 AI 辅助作业时请遵守所在机构的学术诚信规定
