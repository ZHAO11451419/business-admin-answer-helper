# 模型使用指南（Usage）

本文档介绍如何运行微调后的工商管理答题助手模型。模型权重已发布在**双平台**：

| 平台 | 链接 | 适用 |
|---|---|---|
| Hugging Face | [zhaoweichang/business-admin-answer-helper](https://huggingface.co/zhaoweichang/business-admin-answer-helper) | 国际用户 |
| **ModelScope（魔搭）** | [zhao1145141919/business-admin-answer-helper](https://modelscope.cn/models/zhao1145141919/business-admin-answer-helper) | **中国大陆用户直连，无需 VPN** |

（LoRA 适配器，基座为 Qwen2.5-3B-Instruct，v2：1552 对训练数据 / 验证集 token 准确率 94.4% / r=24）

运行方式按推荐程度排列：**中国大陆用户用方式〇（ModelScope 直连）最省事，方式一（命令行）最灵活，方式二（网页界面）最日常，方式三（Colab 在线）零本地资源**。

---

## 方式〇：中国大陆直连（ModelScope，免 VPN）

基座模型从 ModelScope 官方仓库国内直连下载，再挂载本仓库 adapter：

```python
import torch
from modelscope import AutoModelForCausalLM, AutoTokenizer, snapshot_download
from peft import PeftModel

# 1) 下载基座（国内直连，ModelScope 官方镜像）
base_dir = snapshot_download('Qwen/Qwen2.5-3B-Instruct')
tok = AutoTokenizer.from_pretrained(base_dir, trust_remote_code=True)
base = AutoModelForCausalLM.from_pretrained(
    base_dir, torch_dtype=torch.bfloat16, device_map='auto', trust_remote_code=True)

# 2) 挂载本仓库的 LoRA adapter
model = PeftModel.from_pretrained(base, 'zhao1145141919/business-admin-answer-helper')

# 3) 提问（格式与训练数据一致时效果最好）
q = "Calculate the break-even point in units for Bersatu Limited. Price RM1.50, variable cost RM0.75, fixed costs RM15,000."
s = tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True)
out = model.generate(**tok(s, return_tensors="pt").to(model.device),
                     max_new_tokens=400, do_sample=False)
answer = tok.decode(out[0][len(tok(s)["input_ids"][0]):], skip_special_tokens=True)
print(answer)
```

无需 VPN、无需科学上网；显卡 8GB 显存即可跑（纯 CPU 推理也可以，但较慢）。

---

## 0. 依赖（方式一、二需要）

```bash
pip install -U torch transformers peft bitsandbytes
```

本项目仓库内的 `.venv_train` 虚拟环境已装好全部依赖，可直接使用。

---

## 方式一：命令行直接提问（最灵活）

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

# 1) 加载基座 + 微调适配器（4-bit，低内存）
bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
                         bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True)
base = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-3B-Instruct", quantization_config=bnb,
    device_map="auto", torch_dtype=torch.bfloat16)
model = PeftModel.from_pretrained(base, "zhaoweichang/business-admin-answer-helper")
tok = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-3B-Instruct")

# 2) 提问（格式与训练数据一致时效果最好）
q = "Calculate the break-even point in units for Bersatu Limited. Price RM1.50, variable cost RM0.75, fixed costs RM15,000."
s = tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True)
out = model.generate(**tok(s, return_tensors="pt").to(model.device),
                     max_new_tokens=300, do_sample=False)
answer = tok.decode(out[0][len(tok(s)["input_ids"][0]):], skip_special_tokens=True)
print(answer)
```

要点：
- 用 `max_new_tokens=300` 或更大，避免长答案被截断；
- 保持贪婪解码（`do_sample=False`），计算题数字更稳定；
- 提问格式参考 `examples/in-out-pairs.md`，与训练数据一致时效果最好。

---

## 方式二：网页界面（Gradio，适合日常使用）

仓库内置演示脚本：

```bash
python scripts/serve.py --model zhaoweichang/business-admin-answer-helper
```

然后浏览器打开 **http://127.0.0.1:7860** 即可对话。

若本地已有合并后的完整模型，也可以直接指定本地路径：

```bash
python scripts/serve.py --model outputs/business-admin-answer-helper/merged
```

---

## 方式三：Colab 在线运行（零成本、不占本地资源）

模型在 Hugging Face 上是公开的，无需本地 GPU / 内存：

1. 打开仓库的 Colab 笔记本：
   [`notebooks/finetune_qwen25_colab.ipynb`](../notebooks/finetune_qwen25_colab.ipynb)
2. 运行环境 → 更改运行时类型 → **T4 GPU**（免费）
3. 只运行后半部分（加载 + 测试单元格），或直接使用笔记本中的测试代码；
4. 也可参考方式一的代码，把加载目标换成 HF 上的 adapter。

---

## 常见问题

| 问题 | 解决方案 |
|---|---|
| 加载时内存不足 / 卡死 | 4-bit 加载已是最低内存方案；仍不足时请调大虚拟内存（见下），或改用方式三 Colab |
| `OSError: 页面文件太小` (os error 1455) | Windows 虚拟内存（页面文件）过小。设置 → 系统 → 关于 → 高级系统设置 → 性能设置 → 高级 → 虚拟内存 → 改为 **16-24GB** 或"系统管理的大小"，重启生效 |
| Windows 加载 safetensors 段错误（0xC0000005） | 已在 `scripts/train_lora.py` 内置单线程加载修复（`GLOBAL_WORKERS=1`）；推理脚本可自行加同样的补丁 |
| 没有 GPU，只有 CPU | 代码可运行（`device_map="auto"` 会落到 CPU），但生成较慢（一条答案数十秒），建议用 Colab |
| 网络无法访问 huggingface.co | 中国大陆用户请直接用 **方式〇（ModelScope 直连）**，无需 VPN；或离线加载：先把权重下载到本地，再把模型名换成本地目录路径 |

---

## 关于模型输出

- 模型定位是**高分答题初稿**：格式正确、步骤完整、有商业解读；
- **计算器辅助（calculator-assist）**：推理输出会经 `scripts/calc_assist.py` 自动核验——
  提取答案中的计算表达式（如 `72,000 ÷ 4.50 = 20,000`），用精确运算重算并修正算术错误，
  解读句里重复的错误数字也会一并纠正（修正明细打印在服务端控制台）；
- 局限：纯心算结论（没有写出表达式的数字）和无表达式的常识换算（如"约 45 天"）无法自动修正，
  提交前仍需人工核对关键数字；
- 数字和引用仍需人工核验（大模型仍可能算错或编造引用），提交前务必检查；
- 使用须遵守所在院校的学术诚信政策。
