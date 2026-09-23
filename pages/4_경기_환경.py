import pandas as pd
import plotly.express as px
import streamlit as st

from team_config import get_team_color

PAGE_TITLE_SIZE = 52
SECTION_TITLE_SIZE = 40
SUBSECTION_TITLE_SIZE = 32
BODY_TEXT_SIZE = 20
METRIC_VALUE_SIZE = 46
METRIC_LABEL_SIZE = 22
BAR_LABEL_SIZE = 16
AXIS_TITLE_SIZE = 20
AXIS_TICK_SIZE = 16

POSTSEASON = ["준플레이오프", "플레이오프", "챔피언결정전"]

st.set_page_config(
    page_title="경기 환경 | 여자배구 데이터 대시보드",
    page_icon="🏐",
    layout="wide",
)

st.markdown(
    f"""
    <style>
    html, body, [class*="css"] {{ color: black; font-size: {BODY_TEXT_SIZE}px; }}
    .stMarkdown, .stCaption, .stMetric, label, p, div {{
        color: black; font-size: {BODY_TEXT_SIZE}px;
    }}
    h1 {{ font-size: {PAGE_TITLE_SIZE}px !important; }}
    h2 {{ font-size: {SECTION_TITLE_SIZE}px !important; }}
    h3 {{ font-size: {SUBSECTION_TITLE_SIZE}px !important; }}
    [data-testid="stMetricValue"] {{ font-size: {METRIC_VALUE_SIZE}px !important; }}
    [data-testid="stMetricLabel"] {{ font-size: {METRIC_LABEL_SIZE}px !important; }}
    </style>
    """,
    unsafe_allow_html=True,
)

@st.cache_data
def load_data():
    schedule = pd.read_parquet("team_schedule_2526.parquet")
    routes = pd.read_parquet("season_routes_2526.parquet")
    for col in ["공격성공", "공격범실", "블로킹당함"]:
        if col in routes.columns:
            routes[col] = routes[col].fillna(False).astype(bool)
    return schedule, routes

schedule, routes = load_data()

def apply_schedule_scope(df, scope):
    out = df.copy()
    if scope == "정규리그 전체":
        out = out[out["대회구분"].astype(str) == "정규리그"]
    elif scope == "포스트시즌 전체":
        out = out[out["대회구분"].astype(str).isin(POSTSEASON)]
    elif scope.endswith("라운드"):
        round_no = scope.replace("라운드", "")
        if "라운드" in out.columns:
            out = out[
                (out["대회구분"].astype(str) == "정규리그")
                & (out["라운드"].astype(str) == round_no)
            ]
        elif "경기구분" in out.columns:
            out = out[
                (out["대회구분"].astype(str) == "정규리그")
                & (out["경기구분"].astype(str) == scope)
            ]
    elif scope in POSTSEASON:
        out = out[out["대회구분"].astype(str) == scope]
    return out

def attack_metrics(df):
    n = len(df)
    success = int(df["공격성공"].sum()) if n else 0
    errors = int(df["공격범실"].sum()) if n else 0
    blocked = int(df["블로킹당함"].sum()) if n else 0
    return n, success / n * 100 if n else 0, (success - errors - blocked) / n * 100 if n else 0

def find_col(df, names):
    for name in names:
        if name in df.columns:
            return name
    return None

st.title("경기 환경")
st.caption("휴식일수, 홈·원정, 직전 경기장 간 직선거리와 경기 기록을 함께 봅니다.")

season_col = "시즌명" if "시즌명" in schedule.columns else "시즌코드"

season_labels = {}
# 팀/선수 분석과 동일하게 season_routes의 '시즌명'을 화면 표시값으로 사용
if "시즌코드" in routes.columns and "시즌명" in routes.columns:
    season_pairs = routes[["시즌코드", "시즌명"]].dropna().drop_duplicates()
    season_labels.update(
        dict(zip(season_pairs["시즌코드"].astype(str), season_pairs["시즌명"].astype(str)))
    )
elif "시즌코드" in schedule.columns and "시즌명" in schedule.columns:
    season_pairs = schedule[["시즌코드", "시즌명"]].dropna().drop_duplicates()
    season_labels.update(
        dict(zip(season_pairs["시즌코드"].astype(str), season_pairs["시즌명"].astype(str)))
    )

with st.sidebar:
    st.header("경기 환경 필터")
    if "시즌코드" in schedule.columns:
        seasons = sorted(schedule["시즌코드"].dropna().astype(str).unique(), reverse=True)
        selected_season = st.selectbox(
            "시즌",
            seasons,
            format_func=lambda x: season_labels.get(str(x), str(x)),
        )
        season_schedule = schedule[
            schedule["시즌코드"].astype(str) == str(selected_season)
        ].copy()
    else:
        seasons = sorted(schedule[season_col].dropna().astype(str).unique(), reverse=True)
        selected_season = st.selectbox("시즌", seasons)
        season_schedule = schedule[
            schedule[season_col].astype(str) == str(selected_season)
        ].copy()

    teams = ["전체 팀"] + sorted(season_schedule["팀"].dropna().astype(str).unique())
    selected_team = st.selectbox("팀", teams)
    team_schedule = season_schedule.copy()
    if selected_team != "전체 팀":
        team_schedule = team_schedule[team_schedule["팀"].astype(str) == selected_team]

    comps = set(team_schedule["대회구분"].dropna().astype(str).unique())
    scopes = ["시즌 전체", "정규리그 전체"]
    if any(x in comps for x in POSTSEASON):
        scopes.append("포스트시즌 전체")
    if "라운드" in team_schedule.columns:
        rounds = set(team_schedule["라운드"].dropna().astype(str).unique())
        scopes += [f"{n}라운드" for n in range(1, 7) if str(n) in rounds]
    elif "경기구분" in team_schedule.columns:
        rounds = set(team_schedule["경기구분"].dropna().astype(str).unique())
        scopes += [f"{n}라운드" for n in range(1, 7) if f"{n}라운드" in rounds]
    scopes += [x for x in POSTSEASON if x in comps]
    selected_scope = st.selectbox("경기 구분", scopes)

filtered_schedule = apply_schedule_scope(team_schedule, selected_scope)

if filtered_schedule.empty:
    st.info("선택한 조건에 해당하는 경기 일정이 없습니다.")
    st.stop()

rest_col = find_col(filtered_schedule, ["휴식일수", "휴식일", "rest_days"])
distance_col = find_col(filtered_schedule, ["직전경기장거리_km", "경기장간직선거리_km", "직선거리_km"])
home_col = find_col(filtered_schedule, ["홈원정", "홈_원정", "경기장구분"])

game_count = len(filtered_schedule)
avg_rest = pd.to_numeric(filtered_schedule[rest_col], errors="coerce").mean() if rest_col else float("nan")
avg_distance = pd.to_numeric(filtered_schedule[distance_col], errors="coerce").mean() if distance_col else float("nan")

m1, m2, m3 = st.columns(3)
m1.metric("경기", f"{game_count:,}경기")
m2.metric("평균 휴식일", "-" if pd.isna(avg_rest) else f"{avg_rest:.1f}일")
m3.metric("평균 직선거리", "-" if pd.isna(avg_distance) else f"{avg_distance:.0f} km")

st.caption(
    "직선거리는 실제 이동 경로나 이동시간이 아니라 직전 경기장과 현재 경기장 사이의 지리적 직선거리입니다."
)

# Join team-match environment to attack events using robust common keys.
join_keys = [
    col for col in ["시즌코드", "경기번호", "팀코드"]
    if col in filtered_schedule.columns and col in routes.columns
]
if len(join_keys) < 2:
    join_keys = [
        col for col in ["시즌코드", "경기번호", "팀"]
        if col in filtered_schedule.columns and col in routes.columns
    ]

# Merge에는 실제로 존재하는 열만 사용하고, 팀/팀코드처럼 join key가 아닌
# 중복 식별 열은 제외한다. 그래야 팀 선택 시 환경 열 이름이 suffix로 바뀌지 않는다.
env_cols = list(join_keys)
for col in [rest_col, distance_col, home_col]:
    if col and col in filtered_schedule.columns and col not in env_cols:
        env_cols.append(col)

env_match = filtered_schedule[env_cols].drop_duplicates(subset=join_keys).copy()
attack_base = routes.copy()
if "시즌코드" in filtered_schedule.columns:
    attack_base = attack_base[
        attack_base["시즌코드"].astype(str)
        == str(filtered_schedule["시즌코드"].astype(str).iloc[0])
    ]
# 팀 선택은 schedule의 표시명으로 routes를 다시 필터링하지 않는다.
# 두 파일의 팀 표시명이 서로 다를 수 있으므로(예: 구단 풀네임 vs 축약명),
# 이미 선택된 env_match의 팀코드 + 경기번호를 merge key로 사용해 팀을 제한한다.
analysis = attack_base.merge(env_match, on=join_keys, how="inner", suffixes=("", "_환경"))

st.divider()
st.subheader("휴식일수별 공격")

if rest_col and rest_col in analysis.columns:
    analysis[rest_col] = pd.to_numeric(analysis[rest_col], errors="coerce")
    rest_rows = []
    for value, part in analysis.dropna(subset=[rest_col]).groupby(rest_col):
        n, rate, eff = attack_metrics(part)
        rest_rows.append({"휴식일수": int(value), "공격시도": n, "공격성공률_%": rate, "공격효율_%": eff})

    # 팀/범위 필터 후 공격 이벤트가 0건이면 rest_rows 자체가 비므로
    # 빈 DataFrame을 정렬하기 전에 먼저 검사한다.
    rest_summary = pd.DataFrame(rest_rows)
    if rest_summary.empty:
        st.info("선택한 조건에서 휴식일수와 연결할 수 있는 공격 기록이 없습니다.")
    else:
        rest_summary = rest_summary.sort_values("휴식일수")
        fig_rest = px.bar(
            rest_summary,
            x="휴식일수",
            y="공격성공률_%",
            text=[f"{r:.1f}%<br>{n:,}회" for r, n in zip(rest_summary["공격성공률_%"], rest_summary["공격시도"])],
            custom_data=["공격시도", "공격효율_%"],
            labels={"휴식일수": "휴식일수", "공격성공률_%": "공격 성공률 (%)"},
        )
        fig_rest.update_traces(
            textposition="outside", cliponaxis=False,
            textfont=dict(size=BAR_LABEL_SIZE, color="black"),
            hovertemplate="휴식 %{x}일<br>공격 성공률 %{y:.1f}%<br>공격 시도 %{customdata[0]:,}회<br>공격 효율 %{customdata[1]:.1f}%<extra></extra>",
        )
        fig_rest.update_layout(
            height=520, showlegend=False, font=dict(size=BODY_TEXT_SIZE, color="black"),
            xaxis=dict(dtick=1, tickfont=dict(size=AXIS_TICK_SIZE, color="black"), title_font=dict(size=AXIS_TITLE_SIZE, color="black")),
            yaxis=dict(range=[0, rest_summary["공격성공률_%"].max() + 12], ticksuffix="%", tickfont=dict(size=AXIS_TICK_SIZE, color="black"), title_font=dict(size=AXIS_TITLE_SIZE, color="black"), gridcolor="rgba(0,0,0,0.12)"),
        )
        st.plotly_chart(fig_rest, use_container_width=True)
else:
    st.info("현재 일정 데이터에는 휴식일수 열이 없습니다.")

st.divider()
st.subheader("홈·원정 공격")

if home_col and home_col in analysis.columns:
    home_summary_rows = []
    for value, part in analysis.dropna(subset=[home_col]).groupby(home_col):
        n, rate, eff = attack_metrics(part)
        home_summary_rows.append({"구분": str(value), "공격시도": n, "공격성공률_%": rate, "공격효율_%": eff})
    home_summary = pd.DataFrame(home_summary_rows)
    if home_summary.empty:
        st.info("홈·원정 구분 기록이 없습니다.")
    else:
        home_summary = home_summary.sort_values("구분")
        fig_home = px.bar(
            home_summary, x="구분", y="공격성공률_%",
            text=[f"{r:.1f}%<br>{n:,}회" for r, n in zip(home_summary["공격성공률_%"], home_summary["공격시도"])],
            custom_data=["공격시도", "공격효율_%"],
            labels={"구분": "", "공격성공률_%": "공격 성공률 (%)"},
        )
        fig_home.update_traces(
            textposition="outside", cliponaxis=False,
            textfont=dict(size=BAR_LABEL_SIZE, color="black"),
            hovertemplate="%{x}<br>공격 성공률 %{y:.1f}%<br>공격 시도 %{customdata[0]:,}회<br>공격 효율 %{customdata[1]:.1f}%<extra></extra>",
        )
        fig_home.update_layout(
            height=480, showlegend=False, font=dict(size=BODY_TEXT_SIZE, color="black"),
            xaxis=dict(tickfont=dict(size=AXIS_TICK_SIZE, color="black")),
            yaxis=dict(range=[0, home_summary["공격성공률_%"].max() + 12], ticksuffix="%", tickfont=dict(size=AXIS_TICK_SIZE, color="black"), title_font=dict(size=AXIS_TITLE_SIZE, color="black"), gridcolor="rgba(0,0,0,0.12)"),
        )
        st.plotly_chart(fig_home, use_container_width=True)
else:
    st.info("현재 일정 데이터에는 홈·원정 구분 열이 없습니다.")

st.divider()
st.subheader("직전 경기장 간 직선거리")

if distance_col and distance_col in analysis.columns:
    analysis[distance_col] = pd.to_numeric(analysis[distance_col], errors="coerce")
    distance_view = analysis.dropna(subset=[distance_col]).copy()
    if distance_view.empty:
        st.info("직선거리와 연결할 수 있는 공격 기록이 없습니다.")
    else:
        distance_view["거리구간"] = pd.cut(
            distance_view[distance_col],
            bins=[-0.1, 0.1, 100, 200, 300, float("inf")],
            labels=["0 km", "0~100 km", "100~200 km", "200~300 km", "300 km+"],
            include_lowest=True,
        )
        distance_rows = []
        for value, part in distance_view.groupby("거리구간", observed=True):
            n, rate, eff = attack_metrics(part)
            distance_rows.append({"거리구간": str(value), "공격시도": n, "공격성공률_%": rate, "공격효율_%": eff})
        distance_summary = pd.DataFrame(distance_rows)
        order = ["0 km", "0~100 km", "100~200 km", "200~300 km", "300 km+"]
        distance_summary["거리구간"] = pd.Categorical(distance_summary["거리구간"], categories=order, ordered=True)
        distance_summary = distance_summary.sort_values("거리구간")
        fig_distance = px.bar(
            distance_summary, x="거리구간", y="공격성공률_%",
            text=[f"{r:.1f}%<br>{n:,}회" for r, n in zip(distance_summary["공격성공률_%"], distance_summary["공격시도"])],
            custom_data=["공격시도", "공격효율_%"],
            labels={"거리구간": "경기장 간 직선거리", "공격성공률_%": "공격 성공률 (%)"},
        )
        fig_distance.update_traces(
            textposition="outside", cliponaxis=False,
            textfont=dict(size=BAR_LABEL_SIZE, color="black"),
            hovertemplate="%{x}<br>공격 성공률 %{y:.1f}%<br>공격 시도 %{customdata[0]:,}회<br>공격 효율 %{customdata[1]:.1f}%<extra></extra>",
        )
        fig_distance.update_layout(
            height=520, showlegend=False, font=dict(size=BODY_TEXT_SIZE, color="black"),
            xaxis=dict(tickfont=dict(size=AXIS_TICK_SIZE, color="black"), title_font=dict(size=AXIS_TITLE_SIZE, color="black")),
            yaxis=dict(range=[0, distance_summary["공격성공률_%"].max() + 12], ticksuffix="%", tickfont=dict(size=AXIS_TICK_SIZE, color="black"), title_font=dict(size=AXIS_TITLE_SIZE, color="black"), gridcolor="rgba(0,0,0,0.12)"),
        )
        st.plotly_chart(fig_distance, use_container_width=True)
        st.caption("거리 구간은 실제 이동거리나 이동시간이 아니라 경기장 좌표 간 직선거리 기준입니다.")
else:
    st.info("현재 일정 데이터에는 직전 경기장 간 직선거리 열이 없습니다.")

st.divider()
st.subheader("경기별 환경 기록")

display_cols = [
    col for col in ["경기일", "대회구분", "라운드", "경기구분", "팀", "상대팀", home_col, rest_col, distance_col]
    if col and col in filtered_schedule.columns
]
game_table = filtered_schedule[display_cols].copy()
rename = {}
if rest_col: rename[rest_col] = "휴식일수"
if distance_col: rename[distance_col] = "직선거리 (km)"
if home_col: rename[home_col] = "홈·원정"
game_table = game_table.rename(columns=rename)
if "직선거리 (km)" in game_table.columns:
    game_table["직선거리 (km)"] = pd.to_numeric(game_table["직선거리 (km)"], errors="coerce").round(0)
st.dataframe(
    game_table.sort_values("경기일", ascending=False),
    use_container_width=True,
    hide_index=True,
    height=min(620, 52 + 35 * len(game_table)),
)

st.caption(
    "※ 경기 환경과 공격 결과의 차이는 함께 나타나는 패턴을 보여주는 탐색적 비교입니다. "
    "휴식일수·홈/원정·거리 자체가 경기 결과의 원인이라고 단정하지 않습니다."
)
