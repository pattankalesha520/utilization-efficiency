"""
Nexus Repository Space & Usage Analytics
----------------------------------------
• Daily / Weekly / Monthly usage
• Artifact count
• Storage consumption (MB)
• Per repository

Compatible with:
- Nexus Repository Manager 3.x

Author: (You)
"""

import requests
from datetime import datetime
from collections import defaultdict
import pandas as pd
import sys

# ===================== CONFIG =====================
NEXUS_URL = "http://localhost:8081"
USERNAME = "admin"
PASSWORD = "admin123"

OUTPUT_PREFIX = "nexus_repo_usage"

HEADERS = {"Accept": "application/json"}
AUTH = (USERNAME, PASSWORD)
TIMEOUT = 30
# =================================================


def api_get(endpoint, params=None):
    url = f"{NEXUS_URL}{endpoint}"
    r = requests.get(
        url,
        headers=HEADERS,
        auth=AUTH,
        params=params,
        timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()


def get_repositories():
    repos = api_get("/service/rest/v1/repositories")
    return [r["name"] for r in repos]


def get_assets(repo_name):
    assets = []
    token = None

    while True:
        params = {"repository": repo_name}
        if token:
            params["continuationToken"] = token

        data = api_get("/service/rest/v1/assets", params)
        assets.extend(data.get("items", []))
        token = data.get("continuationToken")

        if not token:
            break

    return assets


def aggregate_usage(assets):
    daily = defaultdict(lambda: {"count": 0, "size": 0})
    weekly = defaultdict(lambda: {"count": 0, "size": 0})
    monthly = defaultdict(lambda: {"count": 0, "size": 0})

    for asset in assets:
        ts = asset.get("lastDownloaded") or asset.get("blobCreated")
        if not ts:
            continue

        dt = datetime.fromisoformat(ts.replace("Z", ""))
        size_mb = asset.get("fileSize", 0) / (1024 * 1024)

        d_key = dt.strftime("%Y-%m-%d")
        w_key = f"{dt.year}-W{dt.isocalendar()[1]}"
        m_key = dt.strftime("%Y-%m")

        daily[d_key]["count"] += 1
        daily[d_key]["size"] += size_mb

        weekly[w_key]["count"] += 1
        weekly[w_key]["size"] += size_mb

        monthly[m_key]["count"] += 1
        monthly[m_key]["size"] += size_mb

    return daily, weekly, monthly


def generate_reports():
    rows_daily = []
    rows_weekly = []
    rows_monthly = []

    repos = get_repositories()

    for repo in repos:
        print(f"Processing repository: {repo}")
        assets = get_assets(repo)
        daily, weekly, monthly = aggregate_usage(assets)

        for k, v in daily.items():
            rows_daily.append({
                "repository": repo,
                "date": k,
                "artifact_count": v["count"],
                "storage_mb": round(v["size"], 2)
            })

        for k, v in weekly.items():
            rows_weekly.append({
                "repository": repo,
                "week": k,
                "artifact_count": v["count"],
                "storage_mb": round(v["size"], 2)
            })

        for k, v in monthly.items():
            rows_monthly.append({
                "repository": repo,
                "month": k,
                "artifact_count": v["count"],
                "storage_mb": round(v["size"], 2)
            })

    return (
        pd.DataFrame(rows_daily),
        pd.DataFrame(rows_weekly),
        pd.DataFrame(rows_monthly)
    )


def main():
    try:
        df_daily, df_weekly, df_monthly = generate_reports()

        df_daily.to_csv(f"{OUTPUT_PREFIX}_daily.csv", index=False)
        df_weekly.to_csv(f"{OUTPUT_PREFIX}_weekly.csv", index=False)
        df_monthly.to_csv(f"{OUTPUT_PREFIX}_monthly.csv", index=False)

        print("\n✅ Reports generated successfully:")
        print(f" - {OUTPUT_PREFIX}_daily.csv")
        print(f" - {OUTPUT_PREFIX}_weekly.csv")
        print(f" - {OUTPUT_PREFIX}_monthly.csv")

    except Exception as e:
        print("❌ Error:", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
