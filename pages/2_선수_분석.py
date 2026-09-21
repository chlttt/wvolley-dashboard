import pandas as pd
import plotly.express as px
import streamlit as st

from team_config import get_team_color

# ==========================================
# 글씨 크기 설정
# ==========================================
PAGE_TITLE_SIZE = 52
SECTION_TITLE_SIZE = 40
SUBSECTION_TITLE_SIZE = 32
BODY_TEXT_SIZE = 20
METRIC_VALUE_SIZE = 46
METRIC_LABEL_SIZE = 22
BAR_LABEL_SIZE = 18
AXIS_TITLE_SIZE = 22
AXIS_TICK_SIZE = 20
PLAYER_LABEL_SIZE = 18
CHART_TEXT_COLOR = "black"


st.set_page_config(
    page_title="선수 분석 | 여자배구 데이터 대시보드",
    page_icon="🏐",
    layout="wide",
)

st.markdown(
    f"""
    <style>
    html, body, [class*="css"] {{
        color: black;
        font-size: {BODY_TEXT_SIZE}px;
    }}
    .stMarkdown, .stCaption, .stMetric, label, p, div {{
        color: black;
        font-size: {BODY_TEXT_SIZE}px;
    }}
    h1 {{ font-size: {PAGE_TITLE_SIZE}px !important; }}
    h2 {{ font-size: {SECTION_TITLE_SIZE}px !important; }}
    h3 {{ font-size: {SUBSECTION_TITLE_SIZE}px !important; }}
    [data-testid="stMetricValue"] {{
        font-size: {METRIC_VALUE_SIZE}px !important;
    }}
    [data-testid="stMetricLabel"] {{
        font-size: {METRIC_LABEL_SIZE}px !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data():
    routes = pd.read_parquet("season_routes_2526.parquet")

    for col in ["공격성공", "공격범실", "블로킹당함"]:
        if col in routes.columns:
            routes[col] = routes[col].fillna(False).astype(bool)

    return routes


routes = load_data()

st.title("🏐 선수 분석")
st.caption("2025-26 V-League 여자부 선수별 공격 데이터 분석")

postseason_competitions = [
    "준플레이오프",
    "플레이오프",
    "챔피언결정전",
]

with st.sidebar:
    st.header("선수 분석 필터")

    # 1) 시즌
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

    # 2) 경기 구분
    available_competitions = set(
        season_base["대회구분"].dropna().astype(str).unique().tolist()
    )

    game_scope_options = [
        "전체",
        "정규리그",
    ]

    if any(
        comp in available_competitions
        for comp in postseason_competitions
    ):
        game_scope_options.append("포스트시즌")

    game_scope_options += [
        "1라운드",
        "2라운드",
        "3라운드",
        "4라운드",
        "5라운드",
        "6라운드",
    ]

    game_scope_options += [
        comp for comp in postseason_competitions
        if comp in available_competitions
    ]

    selected_scope = st.selectbox(
        "경기 구분",
        game_scope_options,
        index=0,
    )

    scope_base = season_base.copy()

    if selected_scope == "정규리그":
        scope_base = scope_base[
            scope_base["대회구분"].astype(str) == "정규리그"
        ]

    elif selected_scope == "포스트시즌":
        scope_base = scope_base[
            scope_base["대회구분"].astype(str).isin(postseason_competitions)
        ]

    elif selected_scope.endswith("라운드"):
        scope_base = scope_base[
            (scope_base["대회구분"].astype(str) == "정규리그")
            & (scope_base["경기구분"].astype(str) == selected_scope)
        ]

    elif selected_scope in postseason_competitions:
        scope_base = scope_base[
            scope_base["대회구분"].astype(str) == selected_scope
        ]

    # 3) 팀
    team_options = ["전체 팀"] + sorted(
        scope_base["팀"].dropna().astype(str).unique().tolist()
    )

    selected_team = st.selectbox(
        "팀",
        team_options,
        index=0,
    )

    team_base = scope_base.copy()

    if selected_team != "전체 팀":
        team_base = team_base[
            team_base["팀"].astype(str) == selected_team
        ]

    # 4) 포지션
    position_options = ["전체 포지션"] + sorted(
        team_base["공격수포지션"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_position = st.selectbox(
        "포지션",
        position_options,
        index=0,
    )

    filtered = team_base.copy()

    if selected_position != "전체 포지션":
        filtered = filtered[
            filtered["공격수포지션"].astype(str) == selected_position
        ]

    # 5) 선수
    player_options = ["전체 선수"] + sorted(
        filtered["공격수"].dropna().astype(str).unique().tolist()
    )

    selected_player = st.selectbox(
        "선수",
        player_options,
        index=0,
    )


# ==========================================
# 공통 선수 집계
# ==========================================

player_summary = (
    filtered
    .groupby(
        ["시즌코드", "팀코드", "팀", "공격수", "공격수포지션"],
        dropna=False,
    )
    .agg(
        공격시도=("공격수", "size"),
        공격성공=("공격성공", "sum"),
        공격범실=("공격범실", "sum"),
        블로킹당함=("블로킹당함", "sum"),
    )
    .reset_index()
)

player_summary["공격성공률_%"] = (
    player_summary["공격성공"]
    / player_summary["공격시도"]
    * 100
).round(1)

player_summary["공격효율_%"] = (
    (
        player_summary["공격성공"]
        - player_summary["공격범실"]
        - player_summary["블로킹당함"]
    )
    / player_summary["공격시도"]
    * 100
).round(1)

team_totals = (
    filtered
    .groupby(["팀코드", "팀"], dropna=False)
    .size()
    .rename("팀공격시도")
    .reset_index()
)

player_summary = player_summary.merge(
    team_totals,
    on=["팀코드", "팀"],
    how="left",
)

player_summary["공격점유율_%"] = (
    player_summary["공격시도"]
    / player_summary["팀공격시도"]
    * 100
).round(1)


# ==========================================
# 개별 선수 화면
# ==========================================

if selected_player != "전체 선수":
    player_df = filtered[
        filtered["공격수"].astype(str) == selected_player
    ].copy()

    player_row = (
        player_summary[
            player_summary["공격수"].astype(str) == selected_player
        ]
        .sort_values("공격시도", ascending=False)
        .iloc[0]
    )

    st.subheader(f"{selected_player} · {player_row['팀']}")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "공격 시도",
        f"{int(player_row['공격시도']):,}회",
    )
    c2.metric(
        "공격 성공률",
        f"{player_row['공격성공률_%']:.1f}%",
    )
    c3.metric(
        "공격 효율",
        f"{player_row['공격효율_%']:.1f}%",
    )
    c4.metric(
        "공격 점유율",
        f"{player_row['공격점유율_%']:.1f}%",
    )

    st.divider()

    st.subheader("세트별 공격")

    set_summary = (
        player_df
        .groupby("세트")
        .agg(
            공격시도=("공격수", "size"),
            공격성공=("공격성공", "sum"),
            공격범실=("공격범실", "sum"),
            블로킹당함=("블로킹당함", "sum"),
        )
        .reset_index()
    )

    set_summary["공격성공률_%"] = (
        set_summary["공격성공"]
        / set_summary["공격시도"]
        * 100
    ).round(1)

    set_summary["공격효율_%"] = (
        (
            set_summary["공격성공"]
            - set_summary["공격범실"]
            - set_summary["블로킹당함"]
        )
        / set_summary["공격시도"]
        * 100
    ).round(1)

    player_color = get_team_color(
        str(player_row["시즌코드"]),
        str(player_row["팀코드"]),
    )

    fig_set = px.bar(
        set_summary,
        x="세트",
        y="공격성공률_%",
        hover_data={
            "공격시도": ":,",
            "공격효율_%": ":.1f",
        },
        labels={
            "세트": "세트",
            "공격성공률_%": "공격 성공률 (%)",
            "공격시도": "공격 시도",
            "공격효율_%": "공격 효율 (%)",
        },
    )

    fig_set.update_traces(
        marker_color=player_color,
        text=[
            f"{rate:.1f}%<br>({attempt:,}회)"
            for rate, attempt in zip(
                set_summary["공격성공률_%"],
                set_summary["공격시도"],
            )
        ],
        textposition="outside",
        cliponaxis=False,
        textfont=dict(
            size=BAR_LABEL_SIZE,
            color="black",
        ),
    )

    fig_set.update_layout(
        height=500,
        margin=dict(l=30, r=30, t=70, b=40),
        font=dict(
            size=BODY_TEXT_SIZE,
            color=CHART_TEXT_COLOR,
        ),
        xaxis=dict(
            tickmode="linear",
            dtick=1,
            tickfont=dict(size=AXIS_TICK_SIZE, color="black"),
            title_font=dict(size=AXIS_TITLE_SIZE, color="black"),
        ),
        yaxis=dict(
            ticksuffix="%",
            tickfont=dict(size=AXIS_TICK_SIZE, color="black"),
            title_font=dict(size=AXIS_TITLE_SIZE, color="black"),
        ),
    )

    st.plotly_chart(
        fig_set,
        use_container_width=True,
    )

    st.divider()


# ==========================================
# TOP 10
# ==========================================

st.subheader("선수 TOP 10")

ranking_type = st.selectbox(
    "순위 기준",
    [
        "공격 성공률",
        "공격 효율",
        "공격 시도",
        "공격 점유율",
        "리시브 시도",
    ],
    key="player_top10_metric",
)

if selected_scope in ["전체", "정규리그"]:
    default_min_attempts = 100
elif selected_scope == "포스트시즌" or selected_scope.endswith("라운드"):
    default_min_attempts = 30
else:
    default_min_attempts = 10

max_attempts = (
    int(player_summary["공격시도"].max())
    if not player_summary.empty
    else 1
)

min_attack_attempts = st.number_input(
    "공격 성공률·효율 순위 최소 공격 시도",
    min_value=1,
    max_value=max(max_attempts, 1),
    value=min(
        default_min_attempts,
        max(max_attempts, 1),
    ),
    step=1,
)

if ranking_type == "리시브 시도":
    st.info(
        "현재 저장된 season_routes 데이터는 공격 이벤트 중심이라 "
        "선수의 전체 리시브 시도와 공식 리시브 효율을 정확히 계산할 수 없습니다. "
        "리시브 전체 이벤트 데이터를 추가하면 이 순위를 연결할 예정입니다."
    )

else:
    ranking_df = player_summary.copy()

    if ranking_type in ["공격 성공률", "공격 효율"]:
        ranking_df = ranking_df[
            ranking_df["공격시도"] >= min_attack_attempts
        ].copy()

    sort_col = {
        "공격 성공률": "공격성공률_%",
        "공격 효율": "공격효율_%",
        "공격 시도": "공격시도",
        "공격 점유율": "공격점유율_%",
    }[ranking_type]

    ranking_df = (
        ranking_df
        .sort_values(
            [sort_col, "공격시도"],
            ascending=[False, False],
        )
        .head(10)
        .reset_index(drop=True)
    )

    ranking_df.index = ranking_df.index + 1

    table_df = ranking_df[
        [
            "공격수",
            "팀",
            "공격수포지션",
            "공격시도",
            "공격성공률_%",
            "공격효율_%",
            "공격점유율_%",
        ]
    ].copy()

    table_df.columns = [
        "선수",
        "팀",
        "포지션",
        "공격 시도",
        "공격 성공률 (%)",
        "공격 효율 (%)",
        "공격 점유율 (%)",
    ]

    # TOP 10 전체가 내부 스크롤 없이 한 번에 보이도록 높이 고정
    top10_row_height = 35
    top10_header_height = 38
    top10_height = (
        top10_header_height
        + top10_row_height * len(table_df)
        + 6
    )

    st.dataframe(
        table_df,
        use_container_width=True,
        height=top10_height,
    )

    if ranking_type in ["공격 성공률", "공격 효율"]:
        st.caption(
            f"현재 최소 공격 시도 {min_attack_attempts:,}회 이상 선수만 포함합니다."
        )


# ==========================================
# 전체 선수 교차분석
# ==========================================

st.divider()

st.subheader("선수 교차 분석")
st.caption(
    "전체 팀 또는 특정 팀, 포지션을 선택한 상태에서 선수들을 비교할 수 있습니다."
)

cross_metric = st.selectbox(
    "지표 조합",
    [
        "공격점유율 × 공격효율",
        "공격점유율 × 공격성공률",
        "공격성공률 × 공격효율",
    ],
    key="player_league_cross_metric",
)

cross_min_attempts = st.number_input(
    "교차 분석 최소 공격 시도",
    min_value=1,
    max_value=max(max_attempts, 1),
    value=min(
        default_min_attempts,
        max(max_attempts, 1),
    ),
    step=1,
    key="player_league_cross_min_attempts",
)

cross_df = player_summary[
    player_summary["공격시도"] >= cross_min_attempts
].copy()

cross_metric_map = {
    "공격점유율 × 공격효율": (
        "공격점유율_%",
        "공격효율_%",
    ),
    "공격점유율 × 공격성공률": (
        "공격점유율_%",
        "공격성공률_%",
    ),
    "공격성공률 × 공격효율": (
        "공격성공률_%",
        "공격효율_%",
    ),
}

x_col, y_col = cross_metric_map[cross_metric]

cross_df["팀색상"] = cross_df.apply(
    lambda row: get_team_color(
        row["시즌코드"],
        row["팀코드"],
    ),
    axis=1,
)

color_map = dict(
    zip(
        cross_df["팀"],
        cross_df["팀색상"],
    )
)

fig_cross = px.scatter(
    cross_df,
    x=x_col,
    y=y_col,
    color="팀",
    color_discrete_map=color_map,
    hover_name="공격수",
    hover_data={
        "팀": True,
        "공격수포지션": True,
        "공격시도": ":,",
        "공격점유율_%": ":.1f",
        "공격성공률_%": ":.1f",
        "공격효율_%": ":.1f",
    },
    labels={
        "공격점유율_%": "공격 점유율 (%)",
        "공격성공률_%": "공격 성공률 (%)",
        "공격효율_%": "공격 효율 (%)",
        "공격수포지션": "포지션",
        "공격시도": "공격 시도",
    },
)

fig_cross.update_traces(
    marker=dict(
        size=14,
        line=dict(
            width=1,
            color="black",
        ),
    )
)

fig_cross.update_layout(
    height=640,
    margin=dict(l=80, r=80, t=50, b=90),
    font=dict(
        size=BODY_TEXT_SIZE,
        color="black",
    ),
    xaxis=dict(
        showgrid=True,
        gridcolor="rgba(0,0,0,0.12)",
        showline=True,
        linecolor="black",
        tickfont=dict(size=AXIS_TICK_SIZE, color="black"),
        title_font=dict(size=AXIS_TITLE_SIZE, color="black"),
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor="rgba(0,0,0,0.12)",
        showline=True,
        linecolor="black",
        tickfont=dict(size=AXIS_TICK_SIZE, color="black"),
        title_font=dict(size=AXIS_TITLE_SIZE, color="black"),
    ),
)

st.plotly_chart(
    fig_cross,
    use_container_width=True,
)

st.caption(
    "현재는 전체 선수 비교에서는 hover로 선수 이름을 확인합니다. "
    "팀 분석의 소수 선수 산점도와 달리 선수 수가 많아질 수 있어 "
    "라벨이 과밀해지는 것을 막기 위한 구성입니다."
)
