# -*- coding: utf-8 -*-
"""批量测试脚本：用本地 Gradio 服务跑 Q2-Q6（题库外泛化题），输出模型原始答案。"""
import json, time
from gradio_client import Client

BASE = "http://127.0.0.1:7860"

QUES = [
    ("Q2 价格弹性(新公式)",
     "A shop raises the price of a drink from RM5.00 to RM6.00 and weekly quantity sold falls from 100 to 80. Calculate the price elasticity of demand and classify the demand."),
    ("Q3 商法(新科目)",
     "Distinguish an invitation to treat from an offer in contract law, with a Malaysian example of each."),
    ("Q4 品牌延伸(评估题)",
     "A Malaysian instant-noodle brand famous for its \"spicy\" identity wants to launch a premium imported coffee line under the same brand name. Evaluate whether this is advisable and justify your answer."),
    ("Q5 HRM理论对比(跨理论)",
     "Compare Maslow's hierarchy of needs with Herzberg's two-factor theory, and state which you would use to motivate part-time retail staff in Malaysia, with reasons."),
    ("Q6 特许经营跨科案例(最难)",
     "A franchisee of a fast-food chain in Kuala Lumpur wants to exit his franchise contract early because of falling sales. The franchisor demands full payment of remaining franchise fees. Advise the franchisee using both contract law and franchise management concepts."),
]


def main():
    # 注意：gradio_client 复用同一 Client 连续 predict 会污染 ChatInterface 会话历史
    #（第二题会被当成第一题的追问）。每题必须新建 Client 隔离会话。
    client = Client(BASE)
    print("=== 端点探测 ===")
    try:
        api = client.view_api(return_format="dict")
        eps = list((api.get("named_endpoints") or {}).keys())
        print("named:", eps)
    except Exception as e:
        print("view_api failed:", repr(e))

    for name, q in QUES:
        print(f"\n{'=' * 72}\n### {name}\nQ: {q}")
        t0 = time.time()
        text = ""
        try:
            c = Client(BASE)  # 每题新会话，避免串题
            out = c.predict(q, api_name="/chat")
            text = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
        except Exception as e:
            text = f"ERROR: {e!r}"
        print(f"T+{time.time() - t0:.0f}s")
        print(f"A: {text[:4000]}")


if __name__ == "__main__":
    main()
