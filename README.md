# 工商管理答题助手（BAH）

一个微调过的开源大语言模型，能够以高分 UPM 工商管理学生的答题方式回答**工商管理课程作业**——包含正确的答题格式、完整的计算步骤、商业解读和规范的引用。

构建方式：把真实的作业任务书、已完成作业和习题整理成指令数据集，再用 LoRA 微调开源基座模型（Qwen / DeepSeek / Llama）。

> **核心理念**：这个项目不只是"写答案"——它教会模型商学院评分者真正看重的*格式*和*推理模式*：公式 → 代入 → 结果 → 商业含义，有证据的明确判断，马来西亚本地信源，哈佛式引用。

---

## 为什么做这个项目

商学院作业丢分往往不是因为学生没有想法，而是因为**答题格式不对**。本项目把真实 UPM 课程作业中观察到的答题规范（会计 ACN3101、商业分析 MGM3165、人力资源管理、特许经营、商法、市场营销等）固化到一个开源模型里，让任何人都能一步得到一份**格式正确、得分高的初稿**。

## 它能做什么

| 能力 | 示例 |
|---|---|
| 计算题 | 盈亏平衡、本量利分析、分批成本法、约当产量、财务比率——含完整计算过程 |
| 概念题与论述题 | 定义 → 区分 → 讨论，编号结构，商业解读 |
| 案例分析题 | 明确判断（应该/不应该）+ 证据 + 建议 |
| 报告结构 | 封面 → 章节 → 结论 → 参考文献（哈佛格式） |

## 仓库结构

```
business-admin-answer-helper/
├── README.md              # 本文件
├── LICENSE                # Apache-2.0
├── docs/
│   ├── answering-guide.md # 答题格式规范（核心资产）
│   ├── TRAINING_GUIDE.md  # 训练/评估/发布完整手册
│   └── MODEL_CARD.md      # Hugging Face 模型卡
├── data/
│   ├── train.jsonl        # 指令数据集（问题 → 高分答案）
│   ├── build_dataset.py   # 从原始材料构建 train.jsonl 的脚本
│   ├── generate_dataset.py# 参数化生成器 + 人工题库
│   ├── gen_advanced.py    # 高级会计/分析题生成器
│   └── raw/               # 清洗后、版权安全的原始材料
├── configs/
│   └── lora.yaml          # LoRA 微调配置（LLaMA-Factory）
├── notebooks/
│   └── finetune_qwen25_colab.ipynb  # Colab T4 免费一键微调
├── scripts/
│   ├── prepare_dataset.py # 数据校验 + 分层划分（无需 torch）
│   ├── train_lora.py      # 标准 LoRA/QLoRA 监督微调（transformers + peft + trl）
│   ├── evaluate.py        # 评估格式遵循率 + 计算准确率
│   └── serve.py           # 本地 Gradio 演示
├── examples/
│   └── in-out-pairs.md    # 人工可读的输入 → 输出示例
└── .gitignore
```

## 数据集格式

`data/train.jsonl` 使用 Alpaca 指令格式并带 `type` 标签：

```json
{"instruction": "Calculate the break-even point in units and sales value for Bersatu Limited. Selling price RM1.50/unit, variable cost RM0.75/unit, fixed costs RM15,000.",
 "input": "",
 "output": "Break-even (units) = Fixed Costs ÷ Contribution Margin per unit = 15,000 ÷ (1.50 − 0.75) = 15,000 ÷ 0.75 = 20,000 units. Break-even (sales) = 20,000 × RM1.50 = RM30,000. Interpretation: at 20,000 units revenue exactly covers costs; below that the company makes a loss.",
 "type": "calculation"}
```

## 快速开始

> 📖 **完整手册**：见 [`docs/TRAINING_GUIDE.md`](docs/TRAINING_GUIDE.md)（训练 → 评估 → 发布的完整流程、参数建议和常见问题）。
> 🚀 **运行模型**：见 [`docs/USAGE.md`](docs/USAGE.md)（四种运行方式：ModelScope 国内直连 / 命令行 / 网页界面 / Colab 在线）。

### 推荐：在免费 Colab（T4 GPU）上微调

1. 在 Google Colab 打开 [`notebooks/finetune_qwen25_colab.ipynb`](notebooks/finetune_qwen25_colab.ipynb)
2. 运行环境 → 更改运行时类型 → **T4 GPU**
3. 从上到下依次运行单元格（约 25–40 分钟）：安装依赖、从本仓库下载 `train.jsonl`、以 4-bit（QLoRA）加载 Qwen2.5-7B、训练 3 个 epoch、合并适配器、在线测试模型
4. 可选：把合并后的权重推送到 Hugging Face（权重太大，不适合放 GitHub）

### 备选：本地 / 任意 GPU 训练

```bash
pip install -U torch transformers peft trl datasets accelerate bitsandbytes

# 完整 QLoRA 训练（已在 RTX 4060 8GB 上验证，3B 模型约 12 分钟 / 3 epoch）
python scripts/prepare_dataset.py
python scripts/train_lora.py \
    --model_name Qwen/Qwen2.5-3B-Instruct \
    --data data/train.jsonl --output_dir outputs/business-admin-answer-helper \
    --epochs 3 --lr 2e-4 --batch_size 2 --grad_accum 8 \
    --max_length 2048 --use_4bit --grad_ckpt

# 7B 版（≥16GB 显存）：把 --model_name 换成 Qwen/Qwen2.5-7B-Instruct，建议 --max_length 1024

# 无 GPU 冒烟验证（1 步，验证整个链路）
python scripts/train_lora.py --smoke --model_name Qwen/Qwen2.5-0.5B-Instruct
```

> **Windows 注意事项**（已在 `train_lora.py` 内处理）：
> - 权重加载强制单线程（`GLOBAL_WORKERS=1`），避免并行 safetensors mmap→CUDA 拷贝导致的段错误；
> - `max_steps` 默认为 `-1`（由 epoch 控制），兼容 transformers 5.x；
> - 16GB 内存 + 小页面文件的机器**无法**加载合并后的 16-bit 模型做推理——请用 4-bit 加载或增大页面文件。

### 评估

```bash
python scripts/evaluate.py --model path/to/adapter --test data/train.jsonl
```

### 运行演示

```bash
python scripts/serve.py --model path/to/adapter
```

## 模型权重

微调权重已发布在**双平台**：

| 平台 | 链接 | 适用 |
|---|---|---|
| Hugging Face | [zhaoweichang/business-admin-answer-helper](https://huggingface.co/zhaoweichang/business-admin-answer-helper) | 国际用户 |
| **ModelScope（魔搭）** | [zhao1145141919/business-admin-answer-helper](https://modelscope.cn/models/zhao1145141919/business-admin-answer-helper) | **中国大陆用户直连，无需 VPN** |

> 发布的是基于 Qwen2.5-3B-Instruct 训练的 **LoRA 适配器**（r=24 / α=48），训练数据来自本仓库 **1552 对**指令数据集（v2，验证集 token 准确率 **94.4%**）。使用方法与完整指标见模型主页。

### 中国大陆用户：ModelScope 直连（免 VPN）

基座模型在 ModelScope 官方仓库国内直连下载，再挂载本仓库 adapter 即可（详见 `docs/USAGE.md` 方式〇）：

```python
from modelscope import AutoModelForCausalLM, AutoTokenizer, snapshot_download
from peft import PeftModel

base_dir = snapshot_download('Qwen/Qwen2.5-3B-Instruct')
base = AutoModelForCausalLM.from_pretrained(base_dir, device_map='auto', trust_remote_code=True)
tok = AutoTokenizer.from_pretrained(base_dir, trust_remote_code=True)
model = PeftModel.from_pretrained(base, 'zhao1145141919/business-admin-answer-helper')
# 提问格式同下方"运行演示"
```

## 路线图

- [x] 仓库骨架 + 答题格式规范
- [x] 指令数据集 — **1552 对高质量问答**（v2：计算 1394 / 案例 77 / 概念 53 / 论述 28，含 500 条算术专项强化，全部通过计算器 QC 门）。覆盖：本量利分析、成本与财务比率、统计学、成本分类、弹性预算、制造成本表、加权平均分步成本法、分批成本法、多产品本量利、贡献式利润表、效率/回报率，以及**马来西亚本地案例**（NSRF、Bursa Malaysia、Maybank、MASB、BNM、本地品牌）。所有计算答案均为机器计算并独立复核
- [x] 训练管线 — `scripts/prepare_dataset.py` + `scripts/train_lora.py` + `notebooks/finetune_qwen25_colab.ipynb`（数据管线与冒烟测试已验证）
- [x] **真实 GPU 微调（v1 + v2 已验证）** — Qwen2.5-**3B**-Instruct，QLoRA 4-bit，RTX 4060 Laptop 8GB：v1（444 对 / r16）loss 2.46→0.61、验证集 token 准确率 85.7%；**v2（1552 对 / r24）loss→0.28、验证集 token 准确率 94.4%**。也支持 7B；Windows 上需设置 `GLOBAL_WORKERS=1`（见 `docs/TRAINING_GUIDE.md` § Windows 注意事项）
- [x] **计算器辅助（calculator-assist）** — 推理输出自动提取表达式重算并修正算术错误（比率精度、百分比、取整、分步式等 12 项自测全过）
- [ ] 评估报告（格式遵循率 + 计算准确率）
- [ ] 多课程题库扩充

## 许可证

Apache-2.0。见 [LICENSE](LICENSE)。

## 免责声明与数据来源

- 数据集基于**公开描述的答题规范**和**为本项目原创的示例解答**构建，**不包含**受版权保护的教材内容、校内材料或个人隐私信息。
- 该模型是写作**助手**。用户有责任遵守所在院校的学术诚信政策，并在提交前核对所有数字、引用和事实。
