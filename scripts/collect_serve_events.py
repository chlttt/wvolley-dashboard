from pathlib import Path
import time

import pandas as pd
import requests

SEASON_CODE = "022"
REALTIME_URL = "https://user-api.kovo.co.kr/stat/real-time"
ROUTES_FILE = Path("season_routes_2526.parquet")
GAMES_FILE = Path("games_2526_all.parquet")
OUT_FILE = Path("serve_events_2526.parquet")


def get_json(params):
    r = requests.get(REALTIME_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def find_row_lists(obj):
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


def pick_realtime_rows(payload):
    required = {"rindex", "raction", "raresult", "rpname", "rtname"}
    scored = []
    for rows in find_row_lists(payload):
        keys = set().union(*(r.keys() for r in rows[:10])) if rows else set()
        score = len(keys & required)
        if score:
            scored.append((score, len(rows), rows))
    return max(scored, default=(0, 0, []), key=lambda x: (x[0], x[1]))[2]


def normalize_game_no(value):
    if pd.isna(value):
        return None
    try:
        return str(int(float(value)))
    except (ValueError, TypeError):
        return str(value).strip()


def main():
    routes = pd.read_parquet(ROUTES_FILE)
    games = pd.read_parquet(GAMES_FILE)

    # season_routes is already the validated women's V-League event table.
    women_teams = sorted(routes["팀"].dropna().astype(str).unique().tolist())
    women_codes = sorted(routes["팀코드"].dropna().astype(str).unique().tolist())

    if len(women_teams) != 7:
        raise RuntimeError(f"Women's-team validation failed: expected 7 teams, got {women_teams}")

    game_col = "경기번호"
    if game_col not in games.columns:
        raise RuntimeError(f"{game_col} is missing from games data")

    game_nos = []
    for value in games[game_col].dropna().unique():
        gnum = normalize_game_no(value)
        if gnum and gnum not in game_nos:
            game_nos.append(gnum)

    if len(game_nos) != 132:
        raise RuntimeError(f"Women's-game validation failed: expected 132 games, got {len(game_nos)}")

    meta_cols = [c for c in ["시즌코드", "시즌명", "대회구분", "경기구분", "경기번호", "경기일"] if c in routes.columns]
    game_meta = routes[meta_cols].drop_duplicates(subset=["경기번호"]).copy()
    game_meta["_gnum"] = game_meta["경기번호"].map(normalize_game_no)

    records = []
    for idx, gnum in enumerate(game_nos, start=1):
        for set_no in range(1, 6):
            try:
                payload = get_json({
                    "seasonCode": SEASON_CODE,
                    "gnum": gnum,
                    "set": set_no,
                })
            except requests.RequestException as e:
                print(f"request failed gnum={gnum} set={set_no}: {e}")
                continue

            rows = pick_realtime_rows(payload)
            for event_order, row in enumerate(rows, start=1):
                # VV is the serve action in the realtime feed.
                if str(row.get("raction")) != "VV":
                    continue
                team = str(row.get("rtname") or "").strip()
                # Hard guard: never persist a team outside the seven validated women's teams.
                if team not in women_teams:
                    continue
                records.append({
                    "_gnum": gnum,
                    "경기번호": gnum,
                    "세트": set_no,
                    "event_order": event_order,
                    "rindex": row.get("rindex"),
                    "팀": team,
                    "선수": row.get("rpname"),
                    "선수코드": row.get("rpcode"),
                    "서브결과코드": row.get("raresult"),
                    "서브득점": str(row.get("raresult")) == "suc",
                })
            time.sleep(0.03)
        if idx % 20 == 0:
            print(f"processed {idx}/{len(game_nos)} games")

    serves = pd.DataFrame(records)
    if serves.empty:
        raise RuntimeError("No women's serve events were collected.")

    # Post-collection guard: any non-women team aborts the workflow.
    collected_teams = set(serves["팀"].dropna().astype(str).unique())
    unexpected = collected_teams - set(women_teams)
    if unexpected:
        raise RuntimeError(f"Non-women teams detected: {sorted(unexpected)}")

    serves = serves.merge(
        game_meta.drop(columns=["경기번호"], errors="ignore"),
        on="_gnum",
        how="left",
    )
    serves["경기번호"] = serves["_gnum"]
    serves = serves.drop(columns=["_gnum"])

    ordered = [c for c in [
        "시즌코드", "시즌명", "대회구분", "경기구분", "경기번호", "경기일",
        "세트", "event_order", "rindex", "팀", "선수", "선수코드",
        "서브결과코드", "서브득점"
    ] if c in serves.columns]
    serves = serves[ordered]

    serves.to_parquet(OUT_FILE, index=False)

    print(f"saved {OUT_FILE}: {serves.shape}")
    print("teams:", sorted(serves["팀"].unique().tolist()))
    print("serve result codes:")
    print(serves["서브결과코드"].value_counts(dropna=False).to_string())
    print("serve points:", int(serves["서브득점"].sum()))


if __name__ == "__main__":
    main()
