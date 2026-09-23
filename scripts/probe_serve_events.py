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


def find_row_lists(obj):
    """Recursively collect list-of-dict tables from KOVO payloads."""
    found = []
    if isinstance(obj, list):
        if obj and all(isinstance(x, dict) for x in obj):
            found.append(obj)
        for x in obj:
            found.extend(find_row_lists(x))
    elif isinstance(obj, dict):
        for value in obj.values():
            found.extend(find_row_lists(value))
    return found


def pick_rows(payload, required_keys):
    candidates = find_row_lists(payload)
    scored = []
    for rows in candidates:
        keys = set().union(*(r.keys() for r in rows[:10])) if rows else set()
        score = len(keys.intersection(required_keys))
        if score:
            scored.append((score, len(rows), rows))
    return max(scored, default=(0, 0, []), key=lambda x: (x[0], x[1]))[2]


def main():
    # Probe a few completed matches first. We intentionally save every action/result
    # pair instead of guessing which code means serve/ace.
    schedules = []
    for league in LEAGUE_CODES:
        payload = get_json(SCHEDULE_URL, {
            "seasonCode": SEASON_CODE,
            "leagueCode": league,
        })
        schedules.extend(pick_rows(payload, {"gnum", "gameNo", "gameNumber", "gameDate", "homeTeam"}))

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
            rows = pick_rows(payload, {"rindex", "raction", "raresult", "rpname", "rtname", "rtcode"})
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
        raise RuntimeError(
            "No realtime rows were returned. Schedule rows found: "
            f"{len(schedules)}, game ids found: {len(seen)}"
        )

    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    print("rows:", len(df))
    print("\naction counts")
    print(df["raction"].value_counts(dropna=False).to_string())
    print("\naction/result counts")
    print(df.groupby(["raction", "raresult"], dropna=False).size().sort_values(ascending=False).head(80).to_string())
    print(f"saved: {OUT}")


if __name__ == "__main__":
    main()
