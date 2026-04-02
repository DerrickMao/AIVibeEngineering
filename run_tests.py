"""
基金经理观点打标接口 — 自动化测试脚本
===================================
读取 test_cases.json 中的测试用例，逐条调用接口，
生成 HTML 格式的测试报告（含输入、输出、耗时统计）。

用法：
    python run_tests.py
    python run_tests.py --url http://localhost:8000/api/fund-manager/label
    python run_tests.py --output my_report.html
"""

import argparse
import html
import json
import os
import time
from datetime import datetime

import requests

# ──────────────────────────────────────────────
# 配置
# ──────────────────────────────────────────────

DEFAULT_URL = "http://124.223.42.93:8000/api/fund-manager/label"
DEFAULT_CASES_FILE = os.path.join(os.path.dirname(__file__), "test_cases.json")
DEFAULT_OUTPUT = "test_report.html"


# ──────────────────────────────────────────────
# 测试执行
# ──────────────────────────────────────────────

def run_single_test(url: str, case: dict) -> dict:
    """执行单个测试用例，返回结果。"""
    payload = {"queryContent": case["queryContent"]}

    start = time.time()
    try:
        resp = requests.post(url, json=payload, timeout=120)
        elapsed = time.time() - start
        resp_json = resp.json()
        return {
            "case": case,
            "status_code": resp.status_code,
            "response": resp_json,
            "elapsed": elapsed,
            "success": resp.status_code == 200 and resp_json.get("code") == 0,
            "error": None,
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "case": case,
            "status_code": None,
            "response": None,
            "elapsed": elapsed,
            "success": False,
            "error": str(e),
        }


# ──────────────────────────────────────────────
# HTML 报告生成
# ──────────────────────────────────────────────

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>接口测试报告</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; background: #f5f7fa; color: #333; padding: 20px; }}
  .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 24px; }}
  .header h1 {{ font-size: 24px; margin-bottom: 8px; }}
  .header p {{ opacity: 0.9; font-size: 14px; }}
  .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }}
  .summary-card {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); text-align: center; }}
  .summary-card .number {{ font-size: 32px; font-weight: bold; color: #667eea; }}
  .summary-card .label {{ font-size: 13px; color: #888; margin-top: 4px; }}
  .case {{ background: white; border-radius: 10px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); overflow: hidden; }}
  .case-header {{ display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #eee; cursor: pointer; }}
  .case-header:hover {{ background: #fafbfc; }}
  .case-title {{ font-weight: 600; font-size: 15px; }}
  .case-meta {{ display: flex; gap: 12px; align-items: center; font-size: 13px; }}
  .badge {{ padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; }}
  .badge-success {{ background: #e8f5e9; color: #2e7d32; }}
  .badge-fail {{ background: #ffebee; color: #c62828; }}
  .badge-time {{ background: #e3f2fd; color: #1565c0; }}
  .case-body {{ padding: 20px; display: none; }}
  .case-body.open {{ display: block; }}
  .section-label {{ font-size: 13px; font-weight: 600; color: #555; margin-bottom: 8px; margin-top: 16px; }}
  .section-label:first-child {{ margin-top: 0; }}
  .content-box {{ background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; padding: 14px; font-size: 13px; line-height: 1.8; max-height: 300px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }}
  .json-box {{ background: #1e1e2e; color: #cdd6f4; border: none; font-family: "SF Mono", "Fira Code", Consolas, monospace; font-size: 12px; line-height: 1.6; }}
  .json-key {{ color: #89b4fa; }}
  .json-string {{ color: #a6e3a1; }}
  .json-number {{ color: #fab387; }}
  .json-bool {{ color: #f38ba8; }}
  .json-null {{ color: #6c7086; }}
  .error-box {{ background: #fff3f3; border: 1px solid #ffcdd2; color: #c62828; }}
  .managers-summary {{ margin-top: 12px; }}
  .manager-tag {{ display: inline-block; background: #ede7f6; color: #5e35b1; padding: 3px 10px; border-radius: 12px; font-size: 12px; margin: 2px 4px 2px 0; }}
  .expand-btn {{ color: #667eea; font-size: 18px; transition: transform 0.2s; }}
  .expand-btn.open {{ transform: rotate(90deg); }}
</style>
</head>
<body>
<div class="header">
  <h1>基金经理观点打标接口 — 测试报告</h1>
  <p>生成时间：{generated_at} &nbsp;|&nbsp; 接口地址：{api_url}</p>
</div>

<div class="summary">
  <div class="summary-card">
    <div class="number">{total}</div>
    <div class="label">总用例数</div>
  </div>
  <div class="summary-card">
    <div class="number" style="color: #2e7d32;">{passed}</div>
    <div class="label">成功</div>
  </div>
  <div class="summary-card">
    <div class="number" style="color: #c62828;">{failed}</div>
    <div class="label">失败</div>
  </div>
  <div class="summary-card">
    <div class="number">{avg_time}s</div>
    <div class="label">平均耗时</div>
  </div>
  <div class="summary-card">
    <div class="number">{max_time}s</div>
    <div class="label">最大耗时</div>
  </div>
  <div class="summary-card">
    <div class="number">{min_time}s</div>
    <div class="label">最小耗时</div>
  </div>
</div>

{cases_html}

<script>
document.querySelectorAll('.case-header').forEach(header => {{
  header.addEventListener('click', () => {{
    const body = header.nextElementSibling;
    const btn = header.querySelector('.expand-btn');
    body.classList.toggle('open');
    btn.classList.toggle('open');
  }});
}});
</script>
</body>
</html>
"""


def syntax_highlight_json(obj) -> str:
    """将 JSON 对象转为带语法高亮的 HTML。"""
    raw = json.dumps(obj, ensure_ascii=False, indent=2)
    # 转义 HTML
    raw = html.escape(raw)
    # 高亮 key
    import re
    raw = re.sub(
        r'&quot;(.+?)&quot;(\s*:)',
        r'<span class="json-key">&quot;\1&quot;</span>\2',
        raw,
    )
    # 高亮 string value
    raw = re.sub(
        r':\s*&quot;(.+?)&quot;',
        lambda m: f': <span class="json-string">&quot;{m.group(1)}&quot;</span>',
        raw,
    )
    # 高亮数字
    raw = re.sub(
        r':\s*(\d+\.?\d*)',
        r': <span class="json-number">\1</span>',
        raw,
    )
    # 高亮 bool / null
    raw = re.sub(r'\b(true|false)\b', r'<span class="json-bool">\1</span>', raw)
    raw = re.sub(r'\bnull\b', r'<span class="json-null">null</span>', raw)
    return raw


def build_case_html(idx: int, result: dict) -> str:
    """构建单个用例的 HTML 块。"""
    case = result["case"]
    success = result["success"]
    elapsed = result["elapsed"]

    badge_cls = "badge-success" if success else "badge-fail"
    badge_text = "成功" if success else "失败"

    # 基金经理摘要
    managers_html = ""
    if result["response"] and result["response"].get("data"):
        managers = result["response"]["data"]
        tags = [
            f'<span class="manager-tag">{m["manager_name"]}（{m["fund_company"]}）— {m["sentiment"]}</span>'
            for m in managers
        ]
        managers_html = f'''
        <div class="managers-summary">
            <span style="font-size:12px;color:#888;">提取到 {len(managers)} 位基金经理：</span><br>
            {"".join(tags)}
        </div>'''
    elif result["response"] and result["response"].get("code") == 0:
        managers_html = '<div class="managers-summary"><span style="font-size:12px;color:#888;">未提取到基金经理观点（空数组）</span></div>'

    # 响应 JSON
    if result["response"]:
        resp_html = f'<pre class="content-box json-box">{syntax_highlight_json(result["response"])}</pre>'
    elif result["error"]:
        resp_html = f'<div class="content-box error-box">{html.escape(result["error"])}</div>'
    else:
        resp_html = '<div class="content-box error-box">无响应</div>'

    # 输入内容（截断显示）
    content_display = html.escape(case["queryContent"])

    return f'''
    <div class="case">
      <div class="case-header">
        <div>
          <span class="case-title">#{case["id"]} {html.escape(case["name"])}</span>
          <span style="color:#888;font-size:12px;margin-left:8px;">{html.escape(case["description"])}</span>
        </div>
        <div class="case-meta">
          <span class="badge {badge_cls}">{badge_text}</span>
          <span class="badge badge-time">{elapsed:.2f}s</span>
          <span class="expand-btn">▶</span>
        </div>
      </div>
      <div class="case-body">
        <div class="section-label">输入文章（{len(case["queryContent"])} 字）</div>
        <div class="content-box">{content_display}</div>
        {managers_html}
        <div class="section-label">接口返回（HTTP {result["status_code"] or "N/A"}）</div>
        {resp_html}
      </div>
    </div>'''


def generate_report(results: list, api_url: str) -> str:
    """生成完整的 HTML 报告。"""
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed
    times = [r["elapsed"] for r in results]
    avg_time = sum(times) / len(times) if times else 0
    max_time = max(times) if times else 0
    min_time = min(times) if times else 0

    cases_html = "\n".join(
        build_case_html(i, r) for i, r in enumerate(results)
    )

    return HTML_TEMPLATE.format(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        api_url=api_url,
        total=total,
        passed=passed,
        failed=failed,
        avg_time=f"{avg_time:.2f}",
        max_time=f"{max_time:.2f}",
        min_time=f"{min_time:.2f}",
        cases_html=cases_html,
    )


# ──────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="基金经理观点打标接口测试")
    parser.add_argument("--url", default=DEFAULT_URL, help="接口地址")
    parser.add_argument("--cases", default=DEFAULT_CASES_FILE, help="测试用例 JSON 文件路径")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="测试报告输出路径")
    args = parser.parse_args()

    # 加载测试用例
    with open(args.cases, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print(f"加载了 {len(cases)} 个测试用例")
    print(f"接口地址: {args.url}")
    print(f"开始测试...\n")

    results = []
    for i, case in enumerate(cases):
        print(f"[{i + 1}/{len(cases)}] 执行用例 #{case['id']} {case['name']} ...", end=" ", flush=True)
        result = run_single_test(args.url, case)
        results.append(result)

        status = "✓" if result["success"] else "✗"
        manager_count = len(result["response"]["data"]) if result["response"] and "data" in result["response"] else 0
        print(f"{status}  耗时 {result['elapsed']:.2f}s  提取 {manager_count} 位基金经理")

    # 生成报告
    report_html = generate_report(results, args.url)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report_html)

    # 打印汇总
    times = [r["elapsed"] for r in results]
    passed = sum(1 for r in results if r["success"])
    print(f"\n{'=' * 50}")
    print(f"测试完成！")
    print(f"总用例: {len(results)}  成功: {passed}  失败: {len(results) - passed}")
    print(f"平均耗时: {sum(times) / len(times):.2f}s  最大: {max(times):.2f}s  最小: {min(times):.2f}s")
    print(f"报告已保存至: {os.path.abspath(args.output)}")


if __name__ == "__main__":
    main()
