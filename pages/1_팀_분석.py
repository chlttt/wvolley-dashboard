import pandas as pd
import plotly.express as px
import streamlit as st

# ==========================================
# 글씨 크기 설정
# 숫자만 바꾸면 해당 글씨 크기가 변경됩니다.
# ==========================================
PAGE_TITLE_SIZE = 52
SECTION_TITLE_SIZE = 40
SUBSECTION_TITLE_SIZE = 32
BODY_TEXT_SIZE = 20
METRIC_VALUE_SIZE = 46
METRIC_LABEL_SIZE = 22
TEAM_NAME_SIZE = 18
BAR_LABEL_SIZE = 20
AXIS_TITLE_SIZE = 22
AXIS_TICK_SIZE = 20
X_AXIS_TEXT_COLOR = "black"

st.set_page_config(
    page_title="팀 분석 | 여자배구 데이터 대시보드",
    page_icon="🏐",
    layout="wide",
)

st.markdown(
    f"""
    <style>
    html, body, [class*="css"] {{ font-size: {BODY_TEXT_SIZE}px; }}
    .stMarkdown, .stCaption, .stMetric, label, p, div {{ font-size: {BODY_TEXT_SIZE}px; }}
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
    routes = pd.read_parquet("season_routes_2526.parquet")
    team_set = pd.read_parquet("team_set_summary.parquet")

    for col in ["공격성공", "공격범실", "블로킹당함"]:
        if col in routes.columns:
            routes[col] = routes[col].fillna(False).astype(bool)

    return routes, team_set

routes, team_set = load_data()

st.title("🏐 팀 분석")
st.caption("2025-26 V-League 여자부 팀별 공격 지표")

with st.sidebar:
    st.header("팀 분석 필터")

    # 1) 시즌 선택
    season_column = "시즌명" if "시즌명" in routes.columns else "시즌코드"

    season_options = sorted(
        routes[season_column].dropna().astype(str).unique().tolist(),
        reverse=True,
    )

    selected_season = st.selectbox(
        "시즌",
        season_options,
        index=0,
    )

    season_base = routes[
        routes[season_column].astype(str) == selected_season
    ].copy()

    # 2) 선택한 시즌에 실제로 존재하는 팀만 표시
    team_options = sorted(
        season_base["팀"].dropna().astype(str).unique().tolist()
    )

    selected_team = st.selectbox(
        "팀",
        team_options,
    )

    team_base = season_base[
        season_base["팀"].astype(str) == selected_team
    ].copy()

    postseason_competitions = [
        "준플레이오프",
        "플레이오프",
        "챔피언결정전",
    ]

    # 3) 경기 구분
    # 포스트시즌 관련 항목은 선택한 시즌 + 팀이 실제로 참가한 경우에만 표시
    regular_scope_options = [
        "전체",
        "정규리그",
        "1라운드",
        "2라운드",
        "3라운드",
        "4라운드",
        "5라운드",
        "6라운드",
    ]

    team_competitions = set(
        team_base["대회구분"].dropna().astype(str).unique().tolist()
    )

    participated_postseason = [
        comp for comp in postseason_competitions
        if comp in team_competitions
    ]

    game_scope_options = regular_scope_options.copy()

    if participated_postseason:
        game_scope_options.insert(2, "포스트시즌")
        game_scope_options.extend(participated_postseason)

    selected_scope = st.selectbox(
        "경기 구분",
        game_scope_options,
        index=0,
    )

    team_df = team_base.copy()

    if selected_scope == "정규리그":
        team_df = team_df[
            team_df["대회구분"].astype(str) == "정규리그"
        ]

    elif selected_scope == "포스트시즌":
        team_df = team_df[
            team_df["대회구분"].astype(str).isin(postseason_competitions)
        ]

    elif selected_scope in [
        "1라운드",
        "2라운드",
        "3라운드",
        "4라운드",
        "5라운드",
        "6라운드",
    ]:
        team_df = team_df[
            (team_df["대회구분"].astype(str) == "정규리그")
            & (team_df["경기구분"].astype(str) == selected_scope)
        ]

    elif selected_scope in postseason_competitions:
        team_df = team_df[
            team_df["대회구분"].astype(str) == selected_scope
        ]

st.subheader(selected_team)

attempts = len(team_df)
successes = int(team_df["공격성공"].sum())
errors = int(team_df["공격범실"].sum())
blocked = int(team_df["블로킹당함"].sum())
success_rate = successes / attempts * 100 if attempts else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("공격 시도", f"{attempts:,}회")
c2.metric("공격 성공률", f"{success_rate:.1f}%")
c3.metric("공격 범실", f"{errors:,}회")
c4.metric("블로킹 당함", f"{blocked:,}회")

st.divider()

st.subheader("세트별 공격 성공률")

set_summary = (
    team_df
    .groupby("세트")
    .agg(
        공격시도=("공격수", "size"),
        공격성공=("공격성공", "sum"),
    )
    .reset_index()
)

set_summary["공격성공률_%"] = (
    set_summary["공격성공"] / set_summary["공격시도"] * 100
).round(1)

set_summary = set_summary.sort_values("세트")

fig_set = px.bar(
    set_summary,
    x="세트",
    y="공격성공률_%",
    hover_data={
        "공격시도": ":,",
        "공격성공": ":,",
        "공격성공률_%": ":.1f",
    },
    labels={
        "세트": "세트",
        "공격성공률_%": "공격 성공률 (%)",
        "공격시도": "공격 시도",
        "공격성공": "공격 성공",
    },
)

fig_set.update_traces(
    text=[
        f"{rate:.1f}%<br>({attempt:,}회)"
        for rate, attempt in zip(
            set_summary["공격성공률_%"],
            set_summary["공격시도"]
        )
    ],
    textposition="outside",
    cliponaxis=False,
    textfont=dict(size=BAR_LABEL_SIZE),
)

fig_set.update_layout(
    height=520,
    margin=dict(l=20, r=20, t=70, b=20),
    font=dict(size=BODY_TEXT_SIZE),
    xaxis=dict(
        tickmode="linear",
        dtick=1,
        tickfont=dict(size=BODY_TEXT_SIZE, color=X_AXIS_TEXT_COLOR),
        title_font=dict(size=AXIS_TITLE_SIZE, color=X_AXIS_TEXT_COLOR),
    ),
    yaxis=dict(
        tickfont=dict(size=BODY_TEXT_SIZE),
        title_font=dict(size=AXIS_TITLE_SIZE),
    ),
)

fig_set.update_yaxes(
    range=[0, max(set_summary["공격성공률_%"]) + 12],
    ticksuffix="%",
)

st.plotly_chart(fig_set, use_container_width=True)

st.divider()

st.subheader("점수대별 공격 성공률")

score_order = ["0점대", "10점대", "20점 이후"]

score_summary = (
    team_df
    .groupby("점수대")
    .agg(
        공격시도=("공격수", "size"),
        공격성공=("공격성공", "sum"),
    )
    .reset_index()
)

score_summary["공격성공률_%"] = (
    score_summary["공격성공"] / score_summary["공격시도"] * 100
).round(1)

score_summary["점수대"] = pd.Categorical(
    score_summary["점수대"],
    categories=score_order,
    ordered=True,
)

score_summary = score_summary.sort_values("점수대")

fig_score = px.bar(
    score_summary,
    x="점수대",
    y="공격성공률_%",
    hover_data={
        "공격시도": ":,",
        "공격성공": ":,",
        "공격성공률_%": ":.1f",
    },
    labels={
        "점수대": "",
        "공격성공률_%": "공격 성공률 (%)",
        "공격시도": "공격 시도",
        "공격성공": "공격 성공",
    },
)

fig_score.update_traces(
    text=[
        f"{rate:.1f}%<br>({attempt:,}회)"
        for rate, attempt in zip(
            score_summary["공격성공률_%"],
            score_summary["공격시도"]
        )
    ],
    textposition="outside",
    cliponaxis=False,
    textfont=dict(size=BAR_LABEL_SIZE),
)

fig_score.update_layout(
    height=500,
    margin=dict(l=20, r=20, t=70, b=20),
    font=dict(size=BODY_TEXT_SIZE),
    xaxis=dict(tickfont=dict(size=BODY_TEXT_SIZE, color=X_AXIS_TEXT_COLOR)),
    yaxis=dict(
        tickfont=dict(size=BODY_TEXT_SIZE),
        title_font=dict(size=AXIS_TITLE_SIZE),
    ),
)

fig_score.update_yaxes(
    range=[0, max(score_summary["공격성공률_%"]) + 12],
    ticksuffix="%",
)

st.plotly_chart(fig_score, use_container_width=True)

st.caption("점수대는 공격하는 팀의 공격 직전 점수를 기준으로 구분합니다.")

st.divider()

st.subheader("클러치 상황")

clutch_df = team_df[team_df["후반3점차이내"] == True].copy()

clutch_attempts = len(clutch_df)
clutch_successes = int(clutch_df["공격성공"].sum())
clutch_rate = clutch_successes / clutch_attempts * 100 if clutch_attempts else 0
clutch_share = clutch_attempts / attempts * 100 if attempts else 0

k1, k2, k3 = st.columns(3)
k1.metric("클러치 공격 시도", f"{clutch_attempts:,}회")
k2.metric("클러치 공격 성공률", f"{clutch_rate:.1f}%")
k3.metric("전체 공격 중 비중", f"{clutch_share:.1f}%")

st.caption(
    "클러치: 1~4세트는 한 팀이라도 20점 이상, 5세트는 한 팀이라도 10점 이상인 "
    "후반 상황에서 3점차 이내인 공격을 뜻합니다."
)

st.divider()

st.subheader("선수별 공격 비중")

player_summary = (
    team_df
    .groupby(["공격수", "공격수포지션"], dropna=False)
    .agg(
        공격시도=("공격수", "size"),
        공격성공=("공격성공", "sum"),
    )
    .reset_index()
)

player_summary["공격점유율_%"] = (
    player_summary["공격시도"] / player_summary["공격시도"].sum() * 100
).round(1)

player_summary["공격성공률_%"] = (
    player_summary["공격성공"] / player_summary["공격시도"] * 100
).round(1)

player_summary = player_summary.sort_values(
    "공격시도",
    ascending=False
).head(10)

fig_player = px.bar(
    player_summary,
    x="공격수",
    y="공격점유율_%",
    hover_data={
        "공격수포지션": True,
        "공격시도": ":,",
        "공격성공률_%": ":.1f",
        "공격점유율_%": ":.1f",
    },
    labels={
        "공격수": "",
        "공격점유율_%": "공격 점유율 (%)",
        "공격수포지션": "포지션",
        "공격시도": "공격 시도",
        "공격성공률_%": "공격 성공률",
    },
)

fig_player.update_traces(
    text=[
        f"{share:.1f}%"
        for share in player_summary["공격점유율_%"]
    ],
    textposition="outside",
    cliponaxis=False,
    textfont=dict(size=TEAM_NAME_SIZE),
)

fig_player.update_layout(
    height=540,
    margin=dict(l=20, r=20, t=70, b=80),
    font=dict(size=BODY_TEXT_SIZE),
    xaxis=dict(tickfont=dict(size=TEAM_NAME_SIZE, color=X_AXIS_TEXT_COLOR)),
    yaxis=dict(
        tickfont=dict(size=BODY_TEXT_SIZE),
        title_font=dict(size=AXIS_TITLE_SIZE),
    ),
)

fig_player.update_yaxes(
    range=[0, max(player_summary["공격점유율_%"]) + 8],
    ticksuffix="%",
)

st.plotly_chart(fig_player, use_container_width=True)

st.caption(
    "공격 점유율은 선택한 조건에서 해당 선수가 기록한 공격 시도 비중입니다."
)
