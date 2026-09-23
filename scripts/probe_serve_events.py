import json
import time
from pathlib import Path

import pandas as pd
import requests

SEASON_CODE = "022"
LEAGUE_CODES = ["201", "204", "202", "203"]
SCHEDULE_URL = "https://user-api.kovo.co.kr/stat/game-schedule"
REALTIME_URL = "https://user-api.kovo.co.kr/stat/real-time"
OUT = Path("serve_probe_2526.csv")


def get_json(url, params):
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def rows_from_payload(payload):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ["data", "list", "result"]:
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            for key2 in ["list", "data"]:
                if isinstance(value.get(key2), list):
                    return value[key2]
    return []


def main():
    # Probe a few completed matches first. We intentionally save every action/result
    # pair instead of guessing which code means serve/ace.
    schedules = []
    for league in LEAGUE_CODES:
        payload = get_json(SCHEDULE_URL, {
            "seasonCode": SEASON_CODE,
            "leagueCode": league,
        })
        schedules.extend(rows_from_payload(payload))

    probes = []
    seen = set()
    for game in schedules:
        gnum = game.get("gnum") or game.get("gameNo") or game.get("gameNumber")
        if not gnum or gnum in seen:
            continue
        seen.add(gnum)
        for set_no in range(1, 6):
            try:
                payload = get_json(REALTIME_URL, {
                    "seasonCode": SEASON_CODE,
                    "gnum": gnum,
                    "set": set_no,
                })
            except requests.RequestException:
                continue
            rows = rows_from_payload(payload)
            for row in rows:
                probes.append({
                    "경기번호": gnum,
                    "세트": set_no,
                    "rindex": row.get("rindex"),
                    "rtcode": row.get("rtcode"),
                    "rgrade": row.get("rgrade"),
                    "rbnum": row.get("rbnum"),
                    "raction": row.get("raction"),
                    "raresult": row.get("raresult"),
                    "rpname": row.get("rpname"),
                    "rtname": row.get("rtname"),
                    "rpcode": row.get("rpcode"),
                })
            time.sleep(0.05)
        # A handful of matches is enough to discover the serve action/result codes.
        if len(seen) >= 6:
            break

    df = pd.DataFrame(probes)
    if df.empty:
        raise RuntimeError("No realtime rows were returned.")

    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    print("rows:", len(df))
    print("\naction counts")
    print(df["raction"].value_counts(dropna=False).to_string())
    print("\naction/result counts")
    print(df.groupby(["raction", "raresult"], dropna=False).size().sort_values(ascending=False).head(80).to_string())
    print(f"saved: {OUT}")


if __name__ == "__main__":
    main()
