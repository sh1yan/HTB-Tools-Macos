import json
import pandas as pd
from pathlib import Path

# ========= 配置 =========
JSON_PATH = "raw_endpoints.json"
OUTPUT_EXCEL = "raw_endpoints_report.xlsx"
CONTEXT_LIMIT = 300  # 防止单元格过大
# =======================

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_all_endpoints(data):
    rows = []
    for hit in data.get("all_hits", []):
        rows.append({
            "file": hit.get("file"),
            "line": hit.get("line"),
            "type": hit.get("type"),
            "value": hit.get("value"),
            "context": hit.get("context", "")[:CONTEXT_LIMIT],
            "pattern": hit.get("pattern")
        })
    return pd.DataFrame(rows)

def build_base_url_candidates(data):
    rows = []
    for item in data.get("base_url_candidates", []):
        rows.append({
            "value": item.get("value"),
            "file": item.get("file"),
            "line": item.get("line"),
            "context": item.get("context", "")[:CONTEXT_LIMIT],
            "env_hint": item.get("env_hint", False)
        })
    return pd.DataFrame(rows)

def export_to_excel(df_endpoints, df_base_urls, output_path):
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df_endpoints.to_excel(
            writer,
            sheet_name="all_endpoints",
            index=False
        )
        df_base_urls.to_excel(
            writer,
            sheet_name="base_url_candidates",
            index=False
        )
    print(f"✅ Excel 已生成: {output_path}")

def main():
    data = load_json(JSON_PATH)

    df_endpoints = build_all_endpoints(data)
    df_base_urls = build_base_url_candidates(data)

    export_to_excel(df_endpoints, df_base_urls, OUTPUT_EXCEL)

if __name__ == "__main__":
    main()