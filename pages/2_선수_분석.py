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


POSTSEASON = [
    "준플레이오프",
    "플레이오프",
    "챔피언결정전",
]


@st.cache_data
def load_data():
    routes = pd.read_parquet("season_routes_2526.parquet")
    games = pd.read_parquet("games_2526_all.parquet")
    receives = pd.read_parquet("receive_events_2526.parquet")

    for col in ["공격성공", "공격범실", "블로킹당함"]:
        if col in routes.columns:
            routes[col] = routes[col].fillna(False).astype(bool)

    for col in [
        "후반3점차이내",
        "후반5점차이내",
        "접전세트",
        "듀스세트",
        "경기결정세트",
    ]:
        if col in routes.columns:
            routes[col] = routes[col].fillna(False).astype(bool)

    return routes, games, receives


routes, games, receives = load_data()


def apply_attack_scope(df, scope, game_key=None):
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
        game_date, competition, game_no = game_key
        out = out[
            (out["경기번호"].astype(str) == str(game_no))
            & (out["대회구분"].astype(str) == str(competition))
            & (out["경기일"].astype(str).str[:10] == str(game_date))
        ]

    return out


def apply_receive_scope(df, scope, game_key=None):
    out = df.copy()

    if scope == "정규리그 전체":
        out = out[out["대회구분"].astype(str) == "정규리그"]

    elif scope == "포스트시즌 전체":
        out = out[out["대회구분"].astype(str).isin(POSTSEASON)]

    elif scope.endswith("라운드"):
        round_no = scope.replace("라운드", "")
        out = out[
            (out["대회구분"].astype(str) == "정규리그")
            & (out["라운드"].astype(str) == str(round_no))
        ]

    elif scope in POSTSEASON:
        out = out[out["대회구분"].astype(str) == scope]

    elif scope == "개별 경기" and game_key is not None:
        game_date, competition, game_no = game_key
        out = out[
            (out["경기번호"].astype(str) == str(game_no))
            & (out["대회구분"].astype(str) == str(competition))
            & (out["경기일"].astype(str).str[:10] == str(game_date))
        ]

    return out


def attack_summary(df):
    attempts = len(df)
    successes = int(df["공격성공"].sum()) if attempts else 0
    errors = int(df["공격범실"].sum()) if attempts else 0
    blocked = int(df["블로킹당함"].sum()) if attempts else 0

    success_rate = successes / attempts * 100 if attempts else 0
    efficiency = (
        (successes - errors - blocked) / attempts * 100
        if attempts
        else 0
    )

    return {
        "공격시도": attempts,
        "공격성공": successes,
        "공격범실": errors,
        "블로킹당함": blocked,
        "공격성공률_%": success_rate,
        "공격효율_%": efficiency,
    }


def receive_summary(df):
    attempts = len(df)

    if attempts == 0:
        return {
            "리시브시도": 0,
            "리시브정확": 0,
            "리시브실패": 0,
            "리시브효율_%": 0.0,
        }

    exact = int((df["리시브결과"].astype(str) == "exc").sum())
    failed = int((df["리시브결과"].astype(str) == "fal").sum())
    efficiency = max(
        0.0,
        (exact - failed) / attempts * 100,
    )

    return {
        "리시브시도": attempts,
        "리시브정확": exact,
        "리시브실패": failed,
        "리시브효율_%": efficiency,
    }


def build_player_summary(player_rows, team_rows):
    summary = (
        player_rows
        .groupby(
            [
                "시즌코드",
                "팀코드",
                "팀",
                "공격수",
                "공격수포지션",
            ],
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

    if summary.empty:
        return summary

    summary["공격성공률_%"] = (
        summary["공격성공"]
        / summary["공격시도"]
        * 100
    )

    summary["공격효율_%"] = (
        (
            summary["공격성공"]
            - summary["공격범실"]
            - summary["블로킹당함"]
        )
        / summary["공격시도"]
        * 100
    )

    team_totals = (
        team_rows
        .groupby(["팀코드", "팀"], dropna=False)
        .size()
        .rename("팀공격시도")
        .reset_index()
    )

    summary = summary.merge(
        team_totals,
        on=["팀코드", "팀"],
        how="left",
    )

    summary["공격점유율_%"] = (
        summary["공격시도"]
        / summary["팀공격시도"]
        * 100
    )

    return summary


def make_rate_bar(df, x_col, title, color):
    fig = px.bar(
        df,
        x=x_col,
        y="공격성공률_%",
        hover_data={
            "공격시도": ":,",
            "공격성공": ":,",
            "공격효율_%": ":.1f",
        },
        labels={
            x_col: "",
            "공격성공률_%": "공격 성공률 (%)",
            "공격시도": "공격 시도",
            "공격성공": "공격 성공",
            "공격효율_%": "공격 효율 (%)",
        },
        title=title,
    )

    fig.update_traces(
        marker_color=color,
        text=[
            f"{rate:.1f}%<br>({attempt:,}회)"
            for rate, attempt in zip(
                df["공격성공률_%"],
                df["공격시도"],
            )
        ],
        textposition="outside",
        cliponaxis=False,
        textfont=dict(
            size=BAR_LABEL_SIZE,
            color="black",
        ),
    )

    max_rate = (
        float(df["공격성공률_%"].max())
        if not df.empty
        else 0
    )

    fig.update_layout(
        height=500,
        margin=dict(l=45, r=30, t=80, b=55),
        font=dict(
            size=BODY_TEXT_SIZE,
            color=CHART_TEXT_COLOR,
        ),
        xaxis=dict(
            tickfont=dict(size=AXIS_TICK_SIZE, color="black"),
            title_font=dict(size=AXIS_TITLE_SIZE, color="black"),
            showline=True,
            linecolor="black",
        ),
        yaxis=dict(
            range=[0, max_rate + 12],
            ticksuffix="%",
            tickfont=dict(size=AXIS_TICK_SIZE, color="black"),
            title_font=dict(size=AXIS_TITLE_SIZE, color="black"),
            showgrid=True,
            gridcolor="rgba(0,0,0,0.12)",
            showline=True,
            linecolor="black",
        ),
    )

    return fig


st.title("🏐 선수 분석")
st.caption("V-League 여자부 선수별 공격·리시브 기록을 상황별로 비교합니다.")


# ==========================================
# 필터
# ==========================================

season_column = "시즌명" if "시즌명" in routes.columns else "시즌코드"

with st.sidebar:
    st.header("선수 분석 필터")

    # 1) 시즌
    season_options = sorted(
        routes[season_column]
        .dropna()
        .astype(str)
        .unique()
        .tolist(),
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

    selected_season_codes = (
        season_base["시즌코드"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_season_code = (
        selected_season_codes[0]
        if selected_season_codes
        else str(selected_season)
    )

    # 2) 분석 모드
    analysis_mode = st.radio(
        "분석 모드",
        ["개별 선수", "선수 비교"],
        horizontal=True,
    )

    selected_team = "전체 팀"
    selected_position = "전체 포지션"
    selected_player = "전체 선수"
    selected_player_a = None
    selected_player_b = None

    team_options = sorted(
        season_base["팀"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    if analysis_mode == "개별 선수":
        # 3) 팀
        individual_team_options = ["전체 팀"] + team_options

        selected_team = st.selectbox(
            "팀",
            individual_team_options,
            index=0,
        )

        team_base = season_base.copy()

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

        position_base = team_base.copy()

        if selected_position != "전체 포지션":
            position_base = position_base[
                position_base["공격수포지션"].astype(str)
                == selected_position
            ]

        # 5) 선수
        available_players = sorted(
            position_base["공격수"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        player_options = ["전체 선수"] + available_players

        selected_player = st.selectbox(
            "선수",
            player_options,
            index=0,
        )

        scope_source = position_base.copy()

        if selected_player != "전체 선수":
            scope_source = scope_source[
                scope_source["공격수"].astype(str)
                == selected_player
            ]

    else:
        # 비교 모드에서는 팀 A / 팀 B를 독립적으로 선택
        # 서로 다른 팀 선수도 비교할 수 있음
        team_base = season_base.copy()
        position_base = season_base.copy()

        selected_team_a = st.selectbox(
            "팀 A",
            team_options,
            index=0,
            key="compare_team_a",
        )

        player_a_pool = season_base[
            season_base["팀"].astype(str) == selected_team_a
        ].copy()

        player_a_options = sorted(
            player_a_pool["공격수"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_player_a = st.selectbox(
            "선수 A",
            player_a_options,
            index=0,
            key="compare_player_a",
        )

        selected_team_b = st.selectbox(
            "팀 B",
            team_options,
            index=(1 if len(team_options) > 1 else 0),
            key="compare_team_b",
        )

        player_b_pool = season_base[
            season_base["팀"].astype(str) == selected_team_b
        ].copy()

        player_b_options = sorted(
            player_b_pool["공격수"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        if (
            selected_team_a == selected_team_b
            and selected_player_a in player_b_options
            and len(player_b_options) > 1
        ):
            player_b_options = [
                p for p in player_b_options
                if p != selected_player_a
            ]

        selected_player_b = st.selectbox(
            "선수 B",
            player_b_options,
            index=0,
            key="compare_player_b",
        )

        scope_source = season_base[
            (
                (season_base["팀"].astype(str) == selected_team_a)
                & (
                    season_base["공격수"].astype(str)
                    == selected_player_a
                )
            )
            | (
                (season_base["팀"].astype(str) == selected_team_b)
                & (
                    season_base["공격수"].astype(str)
                    == selected_player_b
                )
            )
        ].copy()

    available_competitions = set(
        scope_source["대회구분"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    available_rounds = set(
        scope_source["경기구분"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    # 6) 분석 범위
    scope_options = [
        "시즌 전체",
        "정규리그 전체",
    ]

    if any(
        comp in available_competitions
        for comp in POSTSEASON
    ):
        scope_options.append("포스트시즌 전체")

    for round_name in [
        "1라운드",
        "2라운드",
        "3라운드",
        "4라운드",
        "5라운드",
        "6라운드",
    ]:
        if round_name in available_rounds:
            scope_options.append(round_name)

    scope_options += [
        comp
        for comp in POSTSEASON
        if comp in available_competitions
    ]

    scope_options.append("개별 경기")

    selected_scope = st.selectbox(
        "분석 범위",
        scope_options,
        index=0,
    )

    selected_game_key = None
    selected_game_label = None

    # 7) 개별 경기
    if selected_scope == "개별 경기":
        game_pairs = (
            scope_source[
                [
                    "경기일",
                    "대회구분",
                    "경기번호",
                    "팀",
                    "상대팀",
                ]
            ]
            .drop_duplicates()
            .sort_values(
                ["경기일", "경기번호"],
                ascending=[False, False],
            )
        )

        game_label_map = {}

        for _, row in game_pairs.iterrows():
            game_date = str(row["경기일"])[:10]
            competition = str(row["대회구분"])
            game_no = str(row["경기번호"])
            team_name = str(row["팀"])
            opponent = str(row["상대팀"])

            label = (
                f"{game_date} | "
                f"{team_name} vs {opponent}"
            )

            if competition != "정규리그":
                label += f" | {competition}"

            game_label_map[label] = (
                game_date,
                competition,
                game_no,
            )

        game_labels = list(game_label_map.keys())

        if game_labels:
            selected_game_label = st.selectbox(
                "경기 선택",
                game_labels,
                index=0,
            )
            selected_game_key = game_label_map[
                selected_game_label
            ]


# ==========================================
# 현재 범위 데이터
# ==========================================

# 팀 전체 데이터: 공격점유율의 분모 계산용
scope_team_rows = apply_attack_scope(
    team_base,
    selected_scope,
    selected_game_key,
)

# 포지션 필터까지 적용된 비교용 데이터
scope_player_rows = apply_attack_scope(
    position_base,
    selected_scope,
    selected_game_key,
)

player_summary = build_player_summary(
    scope_player_rows,
    scope_team_rows,
)

# 리시브 데이터에도 같은 시즌 / 팀 / 범위를 적용
receive_scope = receives[
    receives["시즌코드"].astype(str)
    == str(selected_season_code)
].copy()

if selected_team != "전체 팀":
    receive_scope = receive_scope[
        receive_scope["팀"].astype(str)
        == selected_team
    ]

receive_scope = apply_receive_scope(
    receive_scope,
    selected_scope,
    selected_game_key,
)

# 리시브 이벤트에는 포지션이 없으므로 공격 데이터에서 포지션 매핑
position_map = (
    season_base[
        ["팀", "공격수", "공격수포지션"]
    ]
    .dropna(subset=["공격수"])
    .drop_duplicates(
        subset=["팀", "공격수"],
        keep="first",
    )
    .rename(
        columns={
            "공격수": "선수",
            "공격수포지션": "포지션",
        }
    )
)

receive_scope = receive_scope.merge(
    position_map,
    on=["팀", "선수"],
    how="left",
)

if selected_position != "전체 포지션":
    receive_scope = receive_scope[
        receive_scope["포지션"].astype(str)
        == selected_position
    ]


# ==========================================
# 선수 비교
# ==========================================

if (
    analysis_mode == "선수 비교"
    and selected_player_a is not None
    and selected_player_b is not None
):
    compare_base = apply_attack_scope(
        season_base,
        selected_scope,
        selected_game_key,
    )

    compare_base = compare_base[
        (
            (compare_base["팀"].astype(str) == selected_team_a)
            & (
                compare_base["공격수"].astype(str)
                == selected_player_a
            )
        )
        | (
            (compare_base["팀"].astype(str) == selected_team_b)
            & (
                compare_base["공격수"].astype(str)
                == selected_player_b
            )
        )
    ].copy()

    if compare_base.empty:
        st.info("선택한 범위에 두 선수의 공격 기록이 없습니다.")

    else:
        st.subheader(
            f"{selected_player_a} vs {selected_player_b}"
        )

        if selected_game_label:
            st.markdown(f"**선택 경기:** {selected_game_label}")

        player_a_df = compare_base[
            (compare_base["팀"].astype(str) == selected_team_a)
            & (
                compare_base["공격수"].astype(str)
                == selected_player_a
            )
        ].copy()

        player_b_df = compare_base[
            (compare_base["팀"].astype(str) == selected_team_b)
            & (
                compare_base["공격수"].astype(str)
                == selected_player_b
            )
        ].copy()

        def comparison_rows(player_df):
            rows = []

            whole = attack_summary(player_df)
            rows.append(
                {
                    "상황": "전체",
                    "공격시도": whole["공격시도"],
                    "공격성공률_%": whole["공격성공률_%"],
                    "공격효율_%": whole["공격효율_%"],
                }
            )

            if "후반5점차이내" in player_df.columns:
                s5 = attack_summary(
                    player_df[
                        player_df["후반5점차이내"] == True
                    ]
                )
                rows.append(
                    {
                        "상황": "후반 5점차 이내",
                        "공격시도": s5["공격시도"],
                        "공격성공률_%": s5["공격성공률_%"],
                        "공격효율_%": s5["공격효율_%"],
                    }
                )

            if "후반3점차이내" in player_df.columns:
                s3 = attack_summary(
                    player_df[
                        player_df["후반3점차이내"] == True
                    ]
                )
                rows.append(
                    {
                        "상황": "후반 3점차 이내",
                        "공격시도": s3["공격시도"],
                        "공격성공률_%": s3["공격성공률_%"],
                        "공격효율_%": s3["공격효율_%"],
                    }
                )

            for col, label in [
                ("접전세트", "접전 세트"),
                ("듀스세트", "듀스 세트"),
                ("경기결정세트", "경기 결정 세트"),
            ]:
                if col in player_df.columns:
                    s = attack_summary(
                        player_df[
                            player_df[col] == True
                        ]
                    )
                    rows.append(
                        {
                            "상황": label,
                            "공격시도": s["공격시도"],
                            "공격성공률_%": s["공격성공률_%"],
                            "공격효율_%": s["공격효율_%"],
                        }
                    )

            return pd.DataFrame(rows)

        a_summary = comparison_rows(player_a_df)
        b_summary = comparison_rows(player_b_df)

        compare_df = a_summary.merge(
            b_summary,
            on="상황",
            how="outer",
            suffixes=("_A", "_B"),
        ).fillna(0)

        situation_order = [
            "전체",
            "후반 5점차 이내",
            "후반 3점차 이내",
            "접전 세트",
            "듀스 세트",
            "경기 결정 세트",
        ]

        compare_df["상황"] = pd.Categorical(
            compare_df["상황"],
            categories=situation_order,
            ordered=True,
        )

        compare_df = (
            compare_df
            .sort_values("상황")
            .reset_index(drop=True)
        )

        compare_df["상황"] = compare_df["상황"].astype(str)

        # 선수 소속팀 색상
        def player_team_meta(df):
            if df.empty:
                return (
                    str(selected_season_code),
                    "",
                    "",
                )
            return (
                str(df["시즌코드"].iloc[0]),
                str(df["팀코드"].iloc[0]),
                str(df["팀"].iloc[0]),
            )

        a_season, a_team_code, a_team_name = player_team_meta(
            player_a_df
        )
        b_season, b_team_code, b_team_name = player_team_meta(
            player_b_df
        )

        a_color = get_team_color(
            a_season,
            a_team_code,
        )
        b_color = get_team_color(
            b_season,
            b_team_code,
        )

        st.caption(
            f"{selected_player_a}: {a_team_name} · "
            f"{selected_player_b}: {b_team_name}"
        )

        st.markdown("### 상황별 공격 성공률 비교")

        graph_rows = []

        for _, row in compare_df.iterrows():
            graph_rows.append(
                {
                    "상황": row["상황"],
                    "선수": selected_player_a,
                    "공격성공률_%": row["공격성공률_%_A"],
                    "공격시도": int(row["공격시도_A"]),
                }
            )
            graph_rows.append(
                {
                    "상황": row["상황"],
                    "선수": selected_player_b,
                    "공격성공률_%": row["공격성공률_%_B"],
                    "공격시도": int(row["공격시도_B"]),
                }
            )

        graph_df = pd.DataFrame(graph_rows)

        fig_compare = px.bar(
            graph_df,
            x="상황",
            y="공격성공률_%",
            color="선수",
            barmode="group",
            color_discrete_map={
                selected_player_a: a_color,
                selected_player_b: b_color,
            },
            custom_data=["공격시도"],
            labels={
                "상황": "",
                "공격성공률_%": "공격 성공률 (%)",
                "선수": "",
            },
        )

        fig_compare.update_traces(
            text=[
                f"{rate:.1f}%<br>({attempt:,}회)"
                for rate, attempt in zip(
                    graph_df["공격성공률_%"],
                    graph_df["공격시도"],
                )
            ],
            textposition="outside",
            cliponaxis=False,
            textfont=dict(
                size=BAR_LABEL_SIZE,
                color="black",
            ),
            hovertemplate=(
                "%{x}<br>"
                "%{fullData.name}<br>"
                "공격 성공률 %{y:.1f}%<br>"
                "공격 시도 %{customdata[0]:,}회"
                "<extra></extra>"
            ),
        )

        max_compare_rate = (
            float(graph_df["공격성공률_%"].max())
            if not graph_df.empty
            else 0
        )

        fig_compare.update_layout(
            height=560,
            margin=dict(l=60, r=40, t=40, b=80),
            font=dict(
                size=BODY_TEXT_SIZE,
                color="black",
            ),
            xaxis=dict(
                tickfont=dict(
                    size=AXIS_TICK_SIZE,
                    color="black",
                ),
                showline=True,
                linecolor="black",
            ),
            yaxis=dict(
                range=[0, max_compare_rate + 14],
                ticksuffix="%",
                tickfont=dict(
                    size=AXIS_TICK_SIZE,
                    color="black",
                ),
                title_font=dict(
                    size=AXIS_TITLE_SIZE,
                    color="black",
                ),
                showgrid=True,
                gridcolor="rgba(0,0,0,0.12)",
                showline=True,
                linecolor="black",
            ),
            legend=dict(
                title_text="",
                font=dict(
                    size=BODY_TEXT_SIZE,
                    color="black",
                ),
            ),
        )

        st.plotly_chart(
            fig_compare,
            use_container_width=True,
        )

        st.markdown("### 상세 비교")
        st.caption(
            "같은 지표의 두 선수 값을 바로 옆에 배치했습니다."
        )

        attempts_table = pd.DataFrame(
            {
                "상황": compare_df["상황"],
                selected_player_a: (
                    compare_df["공격시도_A"]
                    .astype(int)
                ),
                selected_player_b: (
                    compare_df["공격시도_B"]
                    .astype(int)
                ),
            }
        )

        success_table = pd.DataFrame(
            {
                "상황": compare_df["상황"],
                selected_player_a: (
                    compare_df["공격성공률_%_A"]
                    .round(1)
                ),
                selected_player_b: (
                    compare_df["공격성공률_%_B"]
                    .round(1)
                ),
            }
        )

        efficiency_table = pd.DataFrame(
            {
                "상황": compare_df["상황"],
                selected_player_a: (
                    compare_df["공격효율_%_A"]
                    .round(1)
                ),
                selected_player_b: (
                    compare_df["공격효율_%_B"]
                    .round(1)
                ),
            }
        )

        compact_height = (
            58
            + 54 * len(compare_df)
            + 8
        )

        t1, t2, t3 = st.columns(3)

        with t1:
            st.markdown("#### 공격 시도")
            st.dataframe(
                attempts_table,
                use_container_width=True,
                hide_index=True,
                height=compact_height,
            )

        with t2:
            st.markdown("#### 공격 성공률")
            st.dataframe(
                success_table,
                use_container_width=True,
                hide_index=True,
                height=compact_height,
                column_config={
                    selected_player_a: st.column_config.NumberColumn(
                        format="%.1f%%"
                    ),
                    selected_player_b: st.column_config.NumberColumn(
                        format="%.1f%%"
                    ),
                },
            )

        with t3:
            st.markdown("#### 공격 효율")
            st.dataframe(
                efficiency_table,
                use_container_width=True,
                hide_index=True,
                height=compact_height,
                column_config={
                    selected_player_a: st.column_config.NumberColumn(
                        format="%.1f%%"
                    ),
                    selected_player_b: st.column_config.NumberColumn(
                        format="%.1f%%"
                    ),
                },
            )

        if "후반5점차이내" not in compare_base.columns:
            st.caption(
                "※ 후반 5점차 이내는 현재 저장 데이터에 별도 플래그가 없어 "
                "다음 데이터 갱신 때 추가할 예정입니다."
            )


# ==========================================
# 개별 선수 상세
# ==========================================

if selected_player != "전체 선수":
    player_df = scope_team_rows[
        scope_team_rows["공격수"].astype(str)
        == selected_player
    ].copy()

    player_receive_df = receive_scope[
        receive_scope["선수"].astype(str)
        == selected_player
    ].copy()

    st.subheader(
        f"{selected_player}"
        + (
            f" · {selected_team}"
            if selected_team != "전체 팀"
            else ""
        )
    )

    if selected_game_label:
        st.markdown(f"**선택 경기:** {selected_game_label}")

    if player_df.empty:
        st.info("선택한 범위에서 이 선수의 공격 기록이 없습니다.")

    else:
        attack = attack_summary(player_df)
        receive = receive_summary(player_receive_df)

        player_team = str(player_df["팀"].iloc[0])
        player_team_code = str(player_df["팀코드"].iloc[0])
        player_season_code = str(player_df["시즌코드"].iloc[0])

        team_attempts = len(
            scope_team_rows[
                scope_team_rows["팀"].astype(str)
                == player_team
            ]
        )

        attack_share = (
            attack["공격시도"] / team_attempts * 100
            if team_attempts
            else 0
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "공격 시도",
            f"{attack['공격시도']:,}회",
        )
        c2.metric(
            "공격 성공률",
            f"{attack['공격성공률_%']:.1f}%",
        )
        c3.metric(
            "공격 효율",
            f"{attack['공격효율_%']:.1f}%",
        )
        c4.metric(
            "공격 점유율",
            f"{attack_share:.1f}%",
        )

        r1, r2, r3 = st.columns(3)

        r1.metric(
            "리시브 시도",
            f"{receive['리시브시도']:,}회",
        )
        r2.metric(
            "리시브 정확",
            f"{receive['리시브정확']:,}회",
        )
        r3.metric(
            "리시브 효율",
            f"{receive['리시브효율_%']:.1f}%",
        )

        st.caption(
            "공격 효율 = (공격 성공 - 공격 범실 - 블로킹 당함) / 공격 시도. "
            "리시브 효율 = (정확 리시브 - 리시브 실패) / 리시브 시도."
        )

        player_color = get_team_color(
            player_season_code,
            player_team_code,
        )

        # ------------------------------
        # 세트별
        # ------------------------------
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
        )

        set_summary["공격효율_%"] = (
            (
                set_summary["공격성공"]
                - set_summary["공격범실"]
                - set_summary["블로킹당함"]
            )
            / set_summary["공격시도"]
            * 100
        )

        fig_set = make_rate_bar(
            set_summary,
            "세트",
            "세트별 공격 성공률",
            player_color,
        )

        fig_set.update_xaxes(
            tickmode="linear",
            dtick=1,
        )

        st.plotly_chart(
            fig_set,
            use_container_width=True,
        )

        # ------------------------------
        # 점수대별
        # ------------------------------
        st.divider()
        st.subheader("점수대별 공격")

        score_order = [
            "0점대",
            "10점대",
            "20점 이후",
        ]

        score_summary = (
            player_df
            .groupby("점수대")
            .agg(
                공격시도=("공격수", "size"),
                공격성공=("공격성공", "sum"),
                공격범실=("공격범실", "sum"),
                블로킹당함=("블로킹당함", "sum"),
            )
            .reset_index()
        )

        score_summary["공격성공률_%"] = (
            score_summary["공격성공"]
            / score_summary["공격시도"]
            * 100
        )

        score_summary["공격효율_%"] = (
            (
                score_summary["공격성공"]
                - score_summary["공격범실"]
                - score_summary["블로킹당함"]
            )
            / score_summary["공격시도"]
            * 100
        )

        score_summary["점수대"] = pd.Categorical(
            score_summary["점수대"],
            categories=score_order,
            ordered=True,
        )

        score_summary = score_summary.sort_values("점수대")

        fig_score = make_rate_bar(
            score_summary,
            "점수대",
            "점수대별 공격 성공률",
            player_color,
        )

        st.plotly_chart(
            fig_score,
            use_container_width=True,
        )

        st.caption(
            "점수대는 공격하는 팀의 공격 직전 점수를 기준으로 구분합니다."
        )

        # ------------------------------
        # 접전 상황
        # ------------------------------
        st.divider()
        st.subheader("접전 상황 공격")

        close_rows = []

        if "후반3점차이내" in player_df.columns:
            clutch3 = player_df[
                player_df["후반3점차이내"] == True
            ]
            s = attack_summary(clutch3)

            close_rows.append(
                {
                    "상황": "후반 3점차 이내",
                    "공격 시도": s["공격시도"],
                    "공격 성공": s["공격성공"],
                    "공격 성공률 (%)": round(
                        s["공격성공률_%"],
                        1,
                    ),
                    "공격 효율 (%)": round(
                        s["공격효율_%"],
                        1,
                    ),
                    "전체 공격 중 비중 (%)": round(
                        s["공격시도"]
                        / attack["공격시도"]
                        * 100
                        if attack["공격시도"]
                        else 0,
                        1,
                    ),
                }
            )

        if "후반5점차이내" in player_df.columns:
            clutch5 = player_df[
                player_df["후반5점차이내"] == True
            ]
            s = attack_summary(clutch5)

            close_rows.append(
                {
                    "상황": "후반 5점차 이내",
                    "공격 시도": s["공격시도"],
                    "공격 성공": s["공격성공"],
                    "공격 성공률 (%)": round(
                        s["공격성공률_%"],
                        1,
                    ),
                    "공격 효율 (%)": round(
                        s["공격효율_%"],
                        1,
                    ),
                    "전체 공격 중 비중 (%)": round(
                        s["공격시도"]
                        / attack["공격시도"]
                        * 100
                        if attack["공격시도"]
                        else 0,
                        1,
                    ),
                }
            )

        if close_rows:
            close_df = pd.DataFrame(close_rows)
            st.dataframe(
                close_df,
                use_container_width=True,
                hide_index=True,
                height=58 + 54 * len(close_df) + 8,
            )

            st.caption(
                "후반 3점차 이내: 1~4세트는 한 팀이라도 20점 이상, "
                "5세트는 한 팀이라도 10점 이상인 상황에서 점수차가 3점 이내인 공격."
            )

            if "후반5점차이내" not in player_df.columns:
                st.caption(
                    "※ 후반 5점차 이내 지표는 현재 저장된 공격 데이터에 "
                    "별도 플래그가 없어, 다음 원점수 데이터 갱신 때 추가합니다."
                )

        # ------------------------------
        # 세트 상황별
        # ------------------------------
        situation_cols = [
            ("접전세트", "접전 세트"),
            ("듀스세트", "듀스 세트"),
            ("경기결정세트", "경기 결정 세트"),
        ]

        available_situations = [
            item
            for item in situation_cols
            if item[0] in player_df.columns
        ]

        if available_situations:
            st.divider()
            st.subheader("세트 상황별 공격")

            situation_rows = []

            for col, label in available_situations:
                situation_df = player_df[
                    player_df[col] == True
                ]
                s = attack_summary(situation_df)

                situation_rows.append(
                    {
                        "상황": label,
                        "공격 시도": s["공격시도"],
                        "공격 성공": s["공격성공"],
                        "공격 성공률 (%)": round(
                            s["공격성공률_%"],
                            1,
                        ),
                        "공격 효율 (%)": round(
                            s["공격효율_%"],
                            1,
                        ),
                    }
                )

            situation_df = pd.DataFrame(situation_rows)

            st.dataframe(
                situation_df,
                use_container_width=True,
                hide_index=True,
                height=58 + 54 * len(situation_df) + 8,
            )


if analysis_mode == "개별 선수":
    # ==========================================
    # TOP 10
    # ==========================================

    st.divider()
    st.subheader("선수 TOP 10")
    st.caption(
        "현재 선택한 시즌·팀·포지션·분석 범위를 기준으로 순위를 계산합니다."
    )

    if selected_scope in [
        "시즌 전체",
        "정규리그 전체",
    ]:
        default_min_attempts = 100
    elif (
        selected_scope == "포스트시즌 전체"
        or selected_scope.endswith("라운드")
    ):
        default_min_attempts = 30
    else:
        default_min_attempts = 10

    max_attempts = (
        int(player_summary["공격시도"].max())
        if not player_summary.empty
        else 1
    )

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

    if ranking_type in [
        "공격 성공률",
        "공격 효율",
    ]:
        min_attack_attempts = st.number_input(
            "최소 공격 시도",
            min_value=1,
            max_value=max(max_attempts, 1),
            value=min(
                default_min_attempts,
                max(max_attempts, 1),
            ),
            step=1,
            key="top10_min_attempts",
        )
    else:
        min_attack_attempts = 1


    if ranking_type == "리시브 시도":
        receive_rank = (
            receive_scope
            .groupby(
                ["팀", "선수", "포지션"],
                dropna=False,
            )
            .agg(
                리시브시도=("리시브결과", "size"),
                리시브정확=(
                    "리시브결과",
                    lambda x: (
                        x.astype(str) == "exc"
                    ).sum(),
                ),
                리시브실패=(
                    "리시브결과",
                    lambda x: (
                        x.astype(str) == "fal"
                    ).sum(),
                ),
            )
            .reset_index()
        )

        if not receive_rank.empty:
            receive_rank["리시브효율_%"] = (
                (
                    receive_rank["리시브정확"]
                    - receive_rank["리시브실패"]
                )
                / receive_rank["리시브시도"]
                * 100
            ).clip(lower=0)

            receive_rank = (
                receive_rank
                .sort_values(
                    ["리시브시도", "리시브효율_%"],
                    ascending=[False, False],
                )
                .head(10)
                .reset_index(drop=True)
            )

            receive_rank.index = receive_rank.index + 1
            receive_rank.index.name = "순위"

            receive_table = receive_rank[
                [
                    "선수",
                    "팀",
                    "포지션",
                    "리시브시도",
                    "리시브정확",
                    "리시브실패",
                    "리시브효율_%",
                ]
            ].copy()

            receive_table.columns = [
                "선수",
                "팀",
                "포지션",
                "리시브 시도",
                "리시브 정확",
                "리시브 실패",
                "리시브 효율 (%)",
            ]

            receive_table["리시브 효율 (%)"] = (
                receive_table["리시브 효율 (%)"]
                .round(1)
            )

            top10_height = (
                44
                + 35 * len(receive_table)
                + 6
            )

            st.dataframe(
                receive_table,
                use_container_width=True,
                height=top10_height,
            )
        else:
            st.info("선택한 범위에 리시브 기록이 없습니다.")

    else:
        ranking_df = player_summary.copy()

        if ranking_type in [
            "공격 성공률",
            "공격 효율",
        ]:
            ranking_df = ranking_df[
                ranking_df["공격시도"]
                >= min_attack_attempts
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
        ranking_df.index.name = "순위"

        attack_table = ranking_df[
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

        attack_table.columns = [
            "선수",
            "팀",
            "포지션",
            "공격 시도",
            "공격 성공률 (%)",
            "공격 효율 (%)",
            "공격 점유율 (%)",
        ]

        for col in [
            "공격 성공률 (%)",
            "공격 효율 (%)",
            "공격 점유율 (%)",
        ]:
            attack_table[col] = attack_table[col].round(1)

        top10_height = (
            44
            + 35 * len(attack_table)
            + 6
        )

        st.dataframe(
            attack_table,
            use_container_width=True,
            height=top10_height,
        )

        if ranking_type in [
            "공격 성공률",
            "공격 효율",
        ]:
            st.caption(
                f"최소 공격 시도 {min_attack_attempts:,}회 이상 선수만 포함합니다."
            )


    # ==========================================
    # 전체 선수 교차 분석
    # ==========================================

    st.divider()
    st.subheader("선수 교차 분석")
    st.caption(
        "공격 점유율은 각 선수의 공격 시도를 해당 팀의 전체 공격 시도로 나눈 값입니다."
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
        player_summary["공격시도"]
        >= cross_min_attempts
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

    if cross_df.empty:
        st.info("선택한 조건에 해당하는 선수가 없습니다.")

    else:
        cross_df["팀색상"] = cross_df.apply(
            lambda row: get_team_color(
                str(row["시즌코드"]),
                str(row["팀코드"]),
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
            height=650,
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
                tickfont=dict(
                    size=AXIS_TICK_SIZE,
                    color="black",
                ),
                title_font=dict(
                    size=AXIS_TITLE_SIZE,
                    color="black",
                ),
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="rgba(0,0,0,0.12)",
                showline=True,
                linecolor="black",
                tickfont=dict(
                    size=AXIS_TICK_SIZE,
                    color="black",
                ),
                title_font=dict(
                    size=AXIS_TITLE_SIZE,
                    color="black",
                ),
            ),
        )

        st.plotly_chart(
            fig_cross,
            use_container_width=True,
        )
