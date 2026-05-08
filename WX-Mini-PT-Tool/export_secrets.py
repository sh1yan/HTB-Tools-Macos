import json
import pandas as pd


def export_secrets_to_excel(json_path: str, excel_path: str):
    # 读取 JSON
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_hits = data.get("all_hits", [])

    if not all_hits:
        print("⚠️ 没有发现任何命中记录")
        return

    # 构造 DataFrame
    df = pd.DataFrame([
        {
            "file": hit.get("file"),
            "line": hit.get("line"),
            "category": hit.get("category"),
            "sub_type": hit.get("sub_type"),
            "severity": hit.get("severity"),
            "value": hit.get("value"),
            "context": hit.get("context")
        }
        for hit in all_hits
    ])

    # 按风险等级排序（Critical > High > Medium > Info）
    severity_order = {"Critical": 1, "High": 2, "Medium": 3, "Info": 4}
    df["severity_rank"] = df["severity"].map(severity_order)
    df.sort_values("severity_rank", inplace=True)
    df.drop(columns="severity_rank", inplace=True)

    # 导出 Excel
    df.to_excel(excel_path, index=False)
    print(f"✅ 成功导出 {len(df)} 条记录到 {excel_path}")


if __name__ == "__main__":
    export_secrets_to_excel(
        json_path="raw_secrets.json",
        excel_path="secrets_report.xlsx"
    )