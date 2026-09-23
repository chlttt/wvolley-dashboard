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
CHART_TEXT_COLOR = "black"

POSTSEASON = ["준플레이오프", "플레이오프", "챔피언결정전"]

st.set_page_config(
    page_title="루트 분석 | 여자배구 데이터 대시보드",
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
def load_routes():
    df = pd.read_parquet("routes_3touch_2526.parquet")
    for col in ["공격성공", "공격범실", "블로킹당함"]:
        if col in df.columns:
            df[col] = df[col].fillna(False).astype(bool)
    return df

routes = load_routes()

def attack_summary(df):
    attempts = len(df)
    success = int(df["공격성공"].sum()) if attempts else 0
    errors = int(df["공격범실"].sum()) if attempts else 0
    blocked = int(df["블로킹당함"].sum()) if attempts else 0
    return {
        "시도": attempts,
        "성공률": success / attempts * 100 if attempts else 0,
        "효율": (success - errors - blocked) / attempts * 100 if attempts else 0,
    }

def apply_scope(df, scope, game_key=None):
    out = df.copy()
    if scope == "정규리그 전체":
        out = out[out["대회구분"].astype(str) == "정규리그"]
    elif scope == "포스트시즌 전체":
        out = out[out["대회구분"].astype(str).isin(POSTSEASON)]
    elif scope.endswith("라운드"):
        out = out[
            (out["대회구분"].astype(str) == "정규리그")
            & (out["경기구분"].astype(str) == scope)
        ]
    elif scope in POSTSEASON:
        out = out[out["대회구분"].astype(str) == scope]
    elif scope == "개별 경기" and game_key is not None:
        date, comp, no = game_key
        out = out[
            (out["경기번호"].astype(str) == str(no))
            & (out["대회구분"].astype(str) == str(comp))
            & (out["경기일"].astype(str).str[:10] == str(date))
        ]
    return out

st.title("루트 분석")
st.caption("기록으로 확인되는 기점 → 연결선수 → 공격수 흐름을 분석합니다.")

with st.sidebar:
    st.header("루트 분석 필터")

    season_col = "시즌명" if "시즌명" in routes.columns else "시즌코드"
    seasons = sorted(routes[season_col].dropna().astype(str).unique(), reverse=True)
    selected_season = st.selectbox("시즌", seasons)
    season_df = routes[routes[season_col].astype(str) == selected_season].copy()

    teams = ["전체 팀"] + sorted(season_df["팀"].dropna().astype(str).unique())
    selected_team = st.selectbox("팀", teams)
    team_df = season_df.copy()
    if selected_team != "전체 팀":
        team_df = team_df[team_df["팀"].astype(str) == selected_team]

    positions = ["전체 포지션"] + sorted(
        team_df["공격수포지션"].dropna().astype(str).unique()
    )
    selected_position = st.selectbox("공격수 포지션", positions)
    position_df = team_df.copy()
    if selected_position != "전체 포지션":
        position_df = position_df[
            position_df["공격수포지션"].astype(str) == selected_position
        ]

    players = ["전체 선수"] + sorted(position_df["공격수"].dropna().astype(str).unique())
    selected_player = st.selectbox("공격수", players)
    player_df = position_df.copy()
    if selected_player != "전체 선수":
        player_df = player_df[player_df["공격수"].astype(str) == selected_player]

    available = set(player_df["대회구분"].dropna().astype(str).unique())
    scopes = ["시즌 전체", "정규리그 전체"]
    if any(x in available for x in POSTSEASON):
        scopes.append("포스트시즌 전체")
    scopes += [
        x for x in ["1라운드", "2라운드", "3라운드", "4라운드", "5라운드", "6라운드"]
        if x in set(player_df["경기구분"].dropna().astype(str).unique())
    ]
    scopes += [x for x in POSTSEASON if x in available]
    scopes.append("개별 경기")
    selected_scope = st.selectbox("분석 범위", scopes)

    selected_game_key = None
    if selected_scope == "개별 경기":
        game_rows = (
            player_df[["경기일", "대회구분", "경기번호", "팀", "상대팀"]]
            .drop_duplicates()
            .sort_values(["경기일", "경기번호"], ascending=[False, False])
        )
        labels = {}
        for _, row in game_rows.iterrows():
            date = str(row["경기일"])[:10]
            label = f"{date} | {row['팀']} vs {row['상대팀']}"
            if str(row["대회구분"]) != "정규리그":
                label += f" | {row['대회구분']}"
            labels[label] = (date, str(row["대회구분"]), str(row["경기번호"]))
        if labels:
            game_label = st.selectbox("경기 선택", list(labels))
            selected_game_key = labels[game_label]

filtered = apply_scope(player_df, selected_scope, selected_game_key)

if filtered.empty:
    st.info("선택한 조건에 해당하는 기록된 루트가 없습니다.")
    st.stop()

summary = attack_summary(filtered)
unique_connectors = filtered["연결선수"].dropna().nunique()
unique_attackers = filtered["공격수"].dropna().nunique()

m1, m2, m3, m4 = st.columns(4)
m1.metric("기록된 루트", f"{summary['시도']:,}회")
m2.metric("공격 성공률", f"{summary['성공률']:.1f}%")
m3.metric("공격 효율", f"{summary['효율']:.1f}%")
m4.metric("연결선수", f"{unique_connectors:,}명")

st.caption(
    "루트는 실시간 기록에서 기점과 연결선수가 확인된 공격만 포함합니다. "
    "실제 랠리의 모든 터치를 의미하지 않습니다."
)

st.divider()
st.subheader("기점 유형별 공격 결과")

origin = (
    filtered.groupby("기점유형", dropna=False)
    .agg(
        공격시도=("공격수", "size"),
        공격성공=("공격성공", "sum"),
        공격범실=("공격범실", "sum"),
        블로킹당함=("블로킹당함", "sum"),
    )
    .reset_index()
)
origin["공격성공률_%"] = origin["공격성공"] / origin["공격시도"] * 100
origin["공격효율_%"] = (
    origin["공격성공"] - origin["공격범실"] - origin["블로킹당함"]
) / origin["공격시도"] * 100
origin = origin.sort_values("공격시도", ascending=False)

fig_origin = px.bar(
    origin,
    x="기점유형",
    y="공격성공률_%",
    text=[
        f"{r:.1f}%<br>{int(n):,}회"
        for r, n in zip(origin["공격성공률_%"], origin["공격시도"])
    ],
    custom_data=["공격시도", "공격효율_%"],
    labels={"기점유형": "", "공격성공률_%": "공격 성공률 (%)"},
)
fig_origin.update_traces(
    textposition="outside",
    cliponaxis=False,
    textfont=dict(size=BAR_LABEL_SIZE, color="black"),
    hovertemplate="%{x}<br>공격 성공률 %{y:.1f}%<br>공격 시도 %{customdata[0]:,}회<br>공격 효율 %{customdata[1]:.1f}%<extra></extra>",
)
fig_origin.update_layout(
    height=500,
    showlegend=False,
    font=dict(size=BODY_TEXT_SIZE, color="black"),
    xaxis=dict(tickfont=dict(size=AXIS_TICK_SIZE, color="black")),
    yaxis=dict(
        range=[0, max(origin["공격성공률_%"].max() + 12, 12)],
        ticksuffix="%",
        tickfont=dict(size=AXIS_TICK_SIZE, color="black"),
        title_font=dict(size=AXIS_TITLE_SIZE, color="black"),
        gridcolor="rgba(0,0,0,0.12)",
    ),
)
st.plotly_chart(fig_origin, use_container_width=True)

st.divider()
st.subheader("연결선수별 공격 결과")

connector = (
    filtered.dropna(subset=["연결선수"])
    .groupby("연결선수")
    .agg(
        공격시도=("공격수", "size"),
        공격성공=("공격성공", "sum"),
        공격범실=("공격범실", "sum"),
        블로킹당함=("블로킹당함", "sum"),
    )
    .reset_index()
)
connector["공격성공률_%"] = connector["공격성공"] / connector["공격시도"] * 100
connector["공격효율_%"] = (
    connector["공격성공"] - connector["공격범실"] - connector["블로킹당함"]
) / connector["공격시도"] * 100
connector = connector.sort_values("공격시도", ascending=False)

min_conn = st.number_input(
    "연결선수 최소 기록 루트",
    min_value=1,
    max_value=max(int(connector["공격시도"].max()), 1),
    value=min(30, max(int(connector["공격시도"].max()), 1)),
    step=1,
)
connector_view = connector[connector["공격시도"] >= min_conn].copy()

if connector_view.empty:
    st.info("최소 기록 루트 기준을 충족하는 연결선수가 없습니다.")
else:
    fig_connector = px.scatter(
        connector_view,
        x="공격시도",
        y="공격성공률_%",
        size="공격시도",
        hover_name="연결선수",
        custom_data=["공격효율_%"],
        labels={
            "공격시도": "기록된 루트 수",
            "공격성공률_%": "이후 공격 성공률 (%)",
        },
    )
    fig_connector.update_traces(
        marker=dict(line=dict(width=1, color="black")),
        hovertemplate="<b>%{hovertext}</b><br>루트 %{x:,}회<br>이후 공격 성공률 %{y:.1f}%<br>이후 공격 효율 %{customdata[0]:.1f}%<extra></extra>",
    )
    fig_connector.update_layout(
        height=560,
        font=dict(size=BODY_TEXT_SIZE, color="black"),
        xaxis=dict(
            tickfont=dict(size=AXIS_TICK_SIZE, color="black"),
            title_font=dict(size=AXIS_TITLE_SIZE, color="black"),
            gridcolor="rgba(0,0,0,0.12)",
        ),
        yaxis=dict(
            ticksuffix="%",
            tickfont=dict(size=AXIS_TICK_SIZE, color="black"),
            title_font=dict(size=AXIS_TITLE_SIZE, color="black"),
            gridcolor="rgba(0,0,0,0.12)",
        ),
        showlegend=False,
    )
    st.plotly_chart(fig_connector, use_container_width=True)
    st.caption("연결선수별 수치는 해당 연결 뒤에 기록된 공격의 결과이며, 연결선수 개인의 기술 평가를 뜻하지 않습니다.")

st.divider()
st.subheader("자주 나온 루트")

route_table = (
    filtered.dropna(subset=["연결선수", "공격수"])
    .groupby(["기점유형", "연결선수", "공격수"], dropna=False)
    .agg(
        루트수=("공격수", "size"),
        공격성공=("공격성공", "sum"),
        공격범실=("공격범실", "sum"),
        블로킹당함=("블로킹당함", "sum"),
    )
    .reset_index()
)
route_table["공격성공률_%"] = route_table["공격성공"] / route_table["루트수"] * 100
route_table["공격효율_%"] = (
    route_table["공격성공"] - route_table["공격범실"] - route_table["블로킹당함"]
) / route_table["루트수"] * 100
route_table = route_table.sort_values(["루트수", "공격성공률_%"], ascending=[False, False]).head(20)
route_table.insert(0, "순위", range(1, len(route_table) + 1))
route_table = route_table.rename(columns={
    "기점유형": "기점",
    "루트수": "기록 수",
    "공격성공률_%": "공격 성공률 (%)",
    "공격효율_%": "공격 효율 (%)",
})
route_table["공격 성공률 (%)"] = route_table["공격 성공률 (%)"].round(1)
route_table["공격 효율 (%)"] = route_table["공격 효율 (%)"].round(1)
st.dataframe(
    route_table[["순위", "기점", "연결선수", "공격수", "기록 수", "공격 성공률 (%)", "공격 효율 (%)"]],
    use_container_width=True,
    hide_index=True,
    height=52 + 35 * len(route_table),
)

st.divider()
st.subheader("특수 연결 상황")

special_rows = []
if "연결선수포지션" in filtered.columns:
    non_setter = filtered[
        filtered["연결선수포지션"].notna()
        & (filtered["연결선수포지션"].astype(str) != "S")
    ]
    s = attack_summary(non_setter)
    special_rows.append({"상황": "비세터 연결", "루트 수": s["시도"], "공격 성공률 (%)": s["성공률"], "공격 효율 (%)": s["효율"]})

self_route = filtered[
    filtered["기점선수"].notna()
    & (filtered["기점선수"].astype(str) == filtered["공격수"].astype(str))
]
s = attack_summary(self_route)
special_rows.append({"상황": "기점선수 = 공격수", "루트 수": s["시도"], "공격 성공률 (%)": s["성공률"], "공격 효율 (%)": s["효율"]})

special = pd.DataFrame(special_rows)
if not special.empty:
    special["공격 성공률 (%)"] = special["공격 성공률 (%)"].round(1)
    special["공격 효율 (%)"] = special["공격 효율 (%)"].round(1)
    st.dataframe(special, use_container_width=True, hide_index=True)

st.caption(
    "※ 이 페이지의 '루트'는 기록된 source → 연결선수 → 공격수 조합입니다. "
    "물리적으로 정확히 3번의 터치가 있었다는 뜻으로 해석하지 않습니다."
)
