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
    receives = pd.read_parquet("receive_events_2526_final.parquet")
    set_summary = pd.read_parquet("set_summary_2526.parquet")

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

    for col in [
        "3점차이내",
        "5점차이내",
        "후반상황",
        "후반3점차이내",
        "후반5점차이내",
        "접전세트",
        "듀스세트",
        "경기결정세트",
    ]:
        if col in receives.columns:
            receives[col] = receives[col].fillna(False).astype(bool)

    return routes, games, receives, set_summary


routes, games, receives, set_summary = load_data()


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


def plain_three_point_mask(df):
    """
    공격 직전 점수 기준의 '그냥 3점차 이내' 마스크.
    후반 조건은 붙이지 않습니다.
    저장 데이터에 이미 계산된 플래그/점수차가 있을 때만 사용합니다.
    """
    for col in [
        "3점차이내",
        "점수차3점이내",
        "공격직전3점차이내",
    ]:
        if col in df.columns:
            return df[col].fillna(False).astype(bool)

    for col in [
        "점수차",
        "공격직전점수차",
        "공격시점점수차",
    ]:
        if col in df.columns:
            numeric = pd.to_numeric(
                df[col],
                errors="coerce",
            )
            return numeric.abs() <= 3

    return None


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


def enrich_receive_set_tags(receive_df, set_df):
    """
    리시브 이벤트에 세트 단위 태그를 붙입니다.
    접전세트/듀스세트/경기결정세트는 같은 경기·세트의 모든 이벤트에 공통입니다.
    """
    out = receive_df.copy()

    required_tags = [
        "접전세트",
        "듀스세트",
        "경기결정세트",
    ]

    if all(col in out.columns for col in required_tags):
        return out

    tag_cols = [
        col
        for col in required_tags
        if col in set_df.columns
    ]

    if not tag_cols:
        return out

    join_keys = [
        col
        for col in [
            "시즌코드",
            "경기번호",
            "세트",
        ]
        if col in out.columns and col in set_df.columns
    ]

    if len(join_keys) < 2:
        return out

    tag_table = (
        set_df[join_keys + tag_cols]
        .drop_duplicates(subset=join_keys)
        .copy()
    )

    out = out.merge(
        tag_table,
        on=join_keys,
        how="left",
    )

    for col in tag_cols:
        out[col] = out[col].fillna(False).astype(bool)

    return out


def receive_comparison_rows(df):
    """리시브 상황별 비교: 공격 비교와 같은 7개 상황을 사용합니다."""
    rows = []

    def append_row(label, subset):
        s = receive_summary(subset)
        rows.append(
            {
                "상황": label,
                "리시브시도": s["리시브시도"],
                "리시브정확": s["리시브정확"],
                "리시브실패": s["리시브실패"],
                "정확리시브율_%": (
                    s["리시브정확"] / s["리시브시도"] * 100
                    if s["리시브시도"]
                    else 0
                ),
                "실패율_%": (
                    s["리시브실패"] / s["리시브시도"] * 100
                    if s["리시브시도"]
                    else 0
                ),
                "리시브효율_%": s["리시브효율_%"],
            }
        )

    append_row("전체", df)

    for col, label in [
        ("3점차이내", "3점차 이내"),
        ("후반5점차이내", "후반 5점차 이내"),
        ("후반3점차이내", "후반 3점차 이내"),
        ("접전세트", "접전 세트"),
        ("듀스세트", "듀스 세트"),
        ("경기결정세트", "경기 결정 세트"),
    ]:
        if col in df.columns:
            append_row(label, df[df[col] == True])

    order = [
        "전체",
        "3점차 이내",
        "후반 5점차 이내",
        "후반 3점차 이내",
        "접전 세트",
        "듀스 세트",
        "경기 결정 세트",
    ]

    result = pd.DataFrame(rows)

    if not result.empty:
        result["상황"] = pd.Categorical(
            result["상황"],
            categories=order,
            ordered=True,
        )
        result = result.sort_values("상황").reset_index(drop=True)
        result["상황"] = result["상황"].astype(str)

    return result

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

        selected_team_codes = (
            team_base["팀코드"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        # 4) 포지션
        receive_position_pool = receives[
            receives["시즌코드"].astype(str)
            == str(selected_season_code)
        ].copy()

        if selected_team != "전체 팀":
            receive_position_pool = receive_position_pool[
                receive_position_pool["팀코드"]
                .astype(str)
                .isin(selected_team_codes)
            ]

        attack_positions = set(
            team_base["공격수포지션"]
            .dropna()
            .astype(str)
            .tolist()
        )
        receive_positions = set(
            receive_position_pool["포지션"]
            .dropna()
            .astype(str)
            .tolist()
        )

        position_options = ["전체 포지션"] + sorted(
            attack_positions | receive_positions
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
        attack_players = set(
            position_base["공격수"]
            .dropna()
            .astype(str)
            .tolist()
        )

        receive_player_pool = receives[
            receives["시즌코드"].astype(str)
            == str(selected_season_code)
        ].copy()

        if selected_team != "전체 팀":
            receive_player_pool = receive_player_pool[
                receive_player_pool["팀코드"]
                .astype(str)
                .isin(selected_team_codes)
            ]

        if selected_position != "전체 포지션":
            receive_player_pool = receive_player_pool[
                receive_player_pool["포지션"].astype(str)
                == selected_position
            ]

        receive_players = set(
            receive_player_pool["선수"]
            .dropna()
            .astype(str)
            .tolist()
        )

        available_players = sorted(
            attack_players | receive_players
        )

        player_options = available_players

        if player_options:
            selected_player = st.selectbox(
                "선수",
                player_options,
                index=0,
            )

            # 분석 범위 선택지는 공격 기록이 있으면 공격 기록,
            # 공격 기록이 없는 선수(예: 리베로)는 리시브 기록 기준으로 구성합니다.
            attack_scope_source = position_base[
                position_base["공격수"].astype(str)
                == selected_player
            ].copy()

            if not attack_scope_source.empty:
                scope_source = attack_scope_source
            else:
                receive_scope_source = receive_player_pool[
                    receive_player_pool["선수"].astype(str)
                    == selected_player
                ].copy()

                # 리시브 데이터의 필드명을 공격 데이터의 범위 선택용 형식에 맞춤
                scope_source = pd.DataFrame(
                    {
                        "대회구분": receive_scope_source["대회구분"],
                        "경기구분": (
                            receive_scope_source["라운드"]
                            .astype(str)
                            .map(lambda x: f"{x}라운드")
                        ),
                        "경기일": receive_scope_source["경기일"],
                        "경기번호": receive_scope_source["경기번호"],
                        "팀": receive_scope_source["팀"],
                        "상대팀": "",
                    }
                )
        else:
            selected_player = None
            scope_source = position_base.iloc[0:0].copy()
            st.info("현재 조건에 해당하는 선수가 없습니다.")

    else:
        # 비교 모드에서는 팀 A / 팀 B를 독립적으로 선택
        # 공격 기록이 없는 리베로도 리시브 데이터에서 선수 목록에 포함합니다.
        team_base = season_base.copy()
        position_base = season_base.copy()

        team_code_map = (
            season_base[
                ["팀", "팀코드"]
            ]
            .dropna()
            .drop_duplicates(subset=["팀"])
            .set_index("팀")["팀코드"]
            .astype(str)
            .to_dict()
        )

        selected_team_a = st.selectbox(
            "팀 A",
            team_options,
            index=0,
            key="compare_team_a",
        )
        team_a_code = team_code_map.get(selected_team_a, "")

        attack_a_players = set(
            season_base.loc[
                season_base["팀"].astype(str) == selected_team_a,
                "공격수",
            ]
            .dropna()
            .astype(str)
            .tolist()
        )
        receive_a_players = set(
            receives.loc[
                (receives["시즌코드"].astype(str) == str(selected_season_code))
                & (receives["팀코드"].astype(str) == str(team_a_code)),
                "선수",
            ]
            .dropna()
            .astype(str)
            .tolist()
        )
        player_a_options = sorted(
            attack_a_players | receive_a_players
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
        team_b_code = team_code_map.get(selected_team_b, "")

        attack_b_players = set(
            season_base.loc[
                season_base["팀"].astype(str) == selected_team_b,
                "공격수",
            ]
            .dropna()
            .astype(str)
            .tolist()
        )
        receive_b_players = set(
            receives.loc[
                (receives["시즌코드"].astype(str) == str(selected_season_code))
                & (receives["팀코드"].astype(str) == str(team_b_code)),
                "선수",
            ]
            .dropna()
            .astype(str)
            .tolist()
        )
        player_b_options = sorted(
            attack_b_players | receive_b_players
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

        attack_scope_source = season_base[
            (
                (season_base["팀"].astype(str) == selected_team_a)
                & (season_base["공격수"].astype(str) == selected_player_a)
            )
            | (
                (season_base["팀"].astype(str) == selected_team_b)
                & (season_base["공격수"].astype(str) == selected_player_b)
            )
        ].copy()

        receive_scope_source = receives[
            (receives["시즌코드"].astype(str) == str(selected_season_code))
            & (
                (
                    (receives["팀코드"].astype(str) == str(team_a_code))
                    & (receives["선수"].astype(str) == selected_player_a)
                )
                | (
                    (receives["팀코드"].astype(str) == str(team_b_code))
                    & (receives["선수"].astype(str) == selected_player_b)
                )
            )
        ].copy()

        receive_scope_meta = pd.DataFrame(
            {
                "대회구분": receive_scope_source["대회구분"],
                "경기구분": (
                    receive_scope_source["라운드"]
                    .astype(str)
                    .map(lambda x: f"{x}라운드")
                ),
                "경기일": receive_scope_source["경기일"],
                "경기번호": receive_scope_source["경기번호"],
                "팀": receive_scope_source["팀"],
                "상대팀": receive_scope_source["상대팀"],
            }
        )

        scope_source = pd.concat(
            [
                attack_scope_source[
                    [
                        "대회구분",
                        "경기구분",
                        "경기일",
                        "경기번호",
                        "팀",
                        "상대팀",
                    ]
                ],
                receive_scope_meta,
            ],
            ignore_index=True,
        ).drop_duplicates()

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
receive_scope = enrich_receive_set_tags(
    receives,
    set_summary,
)

receive_scope = receive_scope[
    receive_scope["시즌코드"].astype(str)
    == str(selected_season_code)
].copy()

if selected_team != "전체 팀":
    receive_scope = receive_scope[
        receive_scope["팀코드"]
        .astype(str)
        .isin(selected_team_codes)
    ]

receive_scope = apply_receive_scope(
    receive_scope,
    selected_scope,
    selected_game_key,
)

# 최종 리시브 데이터에는 API 선수 정보 기반 포지션이 포함되어 있습니다.
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
    team_code_map = (
        season_base[["팀", "팀코드"]]
        .dropna()
        .drop_duplicates(subset=["팀"])
        .set_index("팀")["팀코드"]
        .astype(str)
        .to_dict()
    )

    a_team_code = team_code_map.get(selected_team_a, "")
    b_team_code = team_code_map.get(selected_team_b, "")
    a_team_name = selected_team_a
    b_team_name = selected_team_b
    a_color = get_team_color(str(selected_season_code), str(a_team_code))
    b_color = get_team_color(str(selected_season_code), str(b_team_code))

    st.subheader(
        f"{selected_player_a} vs {selected_player_b}"
    )

    if selected_game_label:
        st.markdown(f"**선택 경기:** {selected_game_label}")

    st.caption(
        f"{selected_player_a}: {a_team_name} · "
        f"{selected_player_b}: {b_team_name}"
    )

    compare_detail_type = st.radio(
        "비교 지표",
        ["공격", "리시브"],
        horizontal=True,
        key="compare_detail_type",
    )

    if compare_detail_type == "공격":
        # ------------------------------
        # 공격 비교
        # ------------------------------
        compare_base = apply_attack_scope(
            season_base,
            selected_scope,
            selected_game_key,
        )

        player_a_df = compare_base[
            (compare_base["팀"].astype(str) == selected_team_a)
            & (compare_base["공격수"].astype(str) == selected_player_a)
        ].copy()

        player_b_df = compare_base[
            (compare_base["팀"].astype(str) == selected_team_b)
            & (compare_base["공격수"].astype(str) == selected_player_b)
        ].copy()

        if player_a_df.empty and player_b_df.empty:
            st.info("선택한 범위에서 두 선수의 공격 기록은 없습니다.")
        else:
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

                plain3_mask = plain_three_point_mask(player_df)
                if plain3_mask is not None:
                    s = attack_summary(player_df[plain3_mask])
                    rows.append(
                        {
                            "상황": "3점차 이내",
                            "공격시도": s["공격시도"],
                            "공격성공률_%": s["공격성공률_%"],
                            "공격효율_%": s["공격효율_%"],
                        }
                    )

                for col, label in [
                    ("후반5점차이내", "후반 5점차 이내"),
                    ("후반3점차이내", "후반 3점차 이내"),
                    ("접전세트", "접전 세트"),
                    ("듀스세트", "듀스 세트"),
                    ("경기결정세트", "경기 결정 세트"),
                ]:
                    if col in player_df.columns:
                        s = attack_summary(player_df[player_df[col] == True])
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
                "3점차 이내",
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
            compare_df = compare_df.sort_values("상황").reset_index(drop=True)
            compare_df["상황"] = compare_df["상황"].astype(str)

            st.caption(
                "접전 기준은 공격 직전 점수를 기준으로 계산합니다. "
                "'3점차 이내'는 세트 진행 시점과 관계없이 점수차만 적용합니다."
            )

            st.markdown("### 상황별 공격 성공률 비교")

            graph_rows = []
            for _, row in compare_df.iterrows():
                graph_rows.extend(
                    [
                        {
                            "상황": row["상황"],
                            "선수": selected_player_a,
                            "공격성공률_%": row["공격성공률_%_A"],
                            "공격시도": int(row["공격시도_A"]),
                        },
                        {
                            "상황": row["상황"],
                            "선수": selected_player_b,
                            "공격성공률_%": row["공격성공률_%_B"],
                            "공격시도": int(row["공격시도_B"]),
                        },
                    ]
                )

            graph_df = pd.DataFrame(graph_rows)
            graph_df["표시"] = graph_df.apply(
                lambda row: (
                    f"{row['공격성공률_%']:.1f}%"
                    f"<br>({int(row['공격시도']):,}회)"
                ),
                axis=1,
            )

            fig_compare = px.bar(
                graph_df,
                x="상황",
                y="공격성공률_%",
                color="선수",
                text="표시",
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
                    "표시": "",
                },
            )

            fig_compare.update_traces(
                textposition="outside",
                cliponaxis=False,
                textfont=dict(size=BAR_LABEL_SIZE, color="black"),
                hovertemplate=(
                    "%{x}<br>%{fullData.name}<br>"
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
                uniformtext_minsize=BAR_LABEL_SIZE,
                uniformtext_mode="show",
                font=dict(size=BODY_TEXT_SIZE, color="black"),
                xaxis=dict(
                    tickfont=dict(size=16, color="black"),
                    showline=True,
                    linecolor="black",
                ),
                yaxis=dict(
                    range=[0, max_compare_rate + 14],
                    ticksuffix="%",
                    tickfont=dict(size=AXIS_TICK_SIZE, color="black"),
                    title_font=dict(size=AXIS_TITLE_SIZE, color="black"),
                    showgrid=True,
                    gridcolor="rgba(0,0,0,0.12)",
                    showline=True,
                    linecolor="black",
                ),
                legend=dict(
                    title_text="",
                    font=dict(size=BODY_TEXT_SIZE, color="black"),
                ),
            )

            st.plotly_chart(fig_compare, use_container_width=True)

            st.markdown("### 상세 비교")
            st.caption("같은 지표의 두 선수 값을 바로 옆에 배치했습니다.")

            attempts_table = pd.DataFrame(
                {
                    "상황": compare_df["상황"],
                    selected_player_a: compare_df["공격시도_A"].astype(int),
                    selected_player_b: compare_df["공격시도_B"].astype(int),
                }
            )
            success_table = pd.DataFrame(
                {
                    "상황": compare_df["상황"],
                    selected_player_a: compare_df["공격성공률_%_A"].round(1),
                    selected_player_b: compare_df["공격성공률_%_B"].round(1),
                }
            )
            efficiency_table = pd.DataFrame(
                {
                    "상황": compare_df["상황"],
                    selected_player_a: compare_df["공격효율_%_A"].round(1),
                    selected_player_b: compare_df["공격효율_%_B"].round(1),
                }
            )

            compact_height = 58 + 54 * len(compare_df) + 8
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
                        selected_player_a: st.column_config.NumberColumn(format="%.1f%%"),
                        selected_player_b: st.column_config.NumberColumn(format="%.1f%%"),
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
                        selected_player_a: st.column_config.NumberColumn(format="%.1f%%"),
                        selected_player_b: st.column_config.NumberColumn(format="%.1f%%"),
                    },
                )

    else:
        # ------------------------------
        # 리시브 비교
        # ------------------------------
        receive_compare_base = receives[
            receives["시즌코드"].astype(str)
            == str(selected_season_code)
        ].copy()

        receive_compare_base = apply_receive_scope(
            receive_compare_base,
            selected_scope,
            selected_game_key,
        )

        player_a_receive = receive_compare_base[
            (receive_compare_base["팀코드"].astype(str) == str(a_team_code))
            & (receive_compare_base["선수"].astype(str) == selected_player_a)
        ].copy()

        player_b_receive = receive_compare_base[
            (receive_compare_base["팀코드"].astype(str) == str(b_team_code))
            & (receive_compare_base["선수"].astype(str) == selected_player_b)
        ].copy()

        if player_a_receive.empty and player_b_receive.empty:
            st.info("선택한 범위에서 두 선수의 리시브 기록은 없습니다.")
        else:
            st.divider()
            st.subheader("리시브 비교")
            st.caption(
                "점수차 기준은 리시브가 발생한 랠리 시작 직전 점수입니다. "
                "'3점차 이내'는 세트 진행 시점과 관계없이 적용합니다."
            )

            a_receive_summary = receive_comparison_rows(player_a_receive)
            b_receive_summary = receive_comparison_rows(player_b_receive)

            receive_compare_df = a_receive_summary.merge(
                b_receive_summary,
                on="상황",
                how="outer",
                suffixes=("_A", "_B"),
            ).fillna(0)

            receive_graph_rows = []
            for _, row in receive_compare_df.iterrows():
                receive_graph_rows.extend(
                    [
                        {
                            "상황": row["상황"],
                            "선수": selected_player_a,
                            "리시브효율_%": row["리시브효율_%_A"],
                            "리시브시도": int(row["리시브시도_A"]),
                        },
                        {
                            "상황": row["상황"],
                            "선수": selected_player_b,
                            "리시브효율_%": row["리시브효율_%_B"],
                            "리시브시도": int(row["리시브시도_B"]),
                        },
                    ]
                )

            receive_graph_df = pd.DataFrame(receive_graph_rows)
            receive_graph_df["표시"] = receive_graph_df.apply(
                lambda row: (
                    f"{row['리시브효율_%']:.1f}%"
                    f"<br>({int(row['리시브시도']):,}회)"
                ),
                axis=1,
            )

            fig_receive_compare = px.bar(
                receive_graph_df,
                x="상황",
                y="리시브효율_%",
                color="선수",
                text="표시",
                barmode="group",
                color_discrete_map={
                    selected_player_a: a_color,
                    selected_player_b: b_color,
                },
                custom_data=["리시브시도"],
                labels={
                    "상황": "",
                    "리시브효율_%": "리시브 효율 (%)",
                    "선수": "",
                    "표시": "",
                },
            )

            fig_receive_compare.update_traces(
                textposition="outside",
                cliponaxis=False,
                textfont=dict(size=14, color="black"),
                hovertemplate=(
                    "%{x}<br>%{fullData.name}<br>"
                    "리시브 효율 %{y:.1f}%<br>"
                    "리시브 시도 %{customdata[0]:,}회"
                    "<extra></extra>"
                ),
            )

            max_receive_rate = (
                float(receive_graph_df["리시브효율_%"].max())
                if not receive_graph_df.empty
                else 0
            )

            fig_receive_compare.update_layout(
                height=620,
                margin=dict(l=60, r=40, t=60, b=100),
                uniformtext_minsize=14,
                uniformtext_mode="show",
                bargap=0.28,
                bargroupgap=0.10,
                font=dict(size=BODY_TEXT_SIZE, color="black"),
                xaxis=dict(
                    tickfont=dict(size=16, color="black"),
                    showline=True,
                    linecolor="black",
                ),
                yaxis=dict(
                    range=[0, max_receive_rate + 20],
                    ticksuffix="%",
                    tickfont=dict(size=AXIS_TICK_SIZE, color="black"),
                    title_font=dict(size=AXIS_TITLE_SIZE, color="black"),
                    showgrid=True,
                    gridcolor="rgba(0,0,0,0.12)",
                    showline=True,
                    linecolor="black",
                ),
                legend=dict(
                    title_text="",
                    font=dict(size=BODY_TEXT_SIZE, color="black"),
                ),
            )

            st.plotly_chart(
                fig_receive_compare,
                use_container_width=True,
            )

            st.markdown("### 리시브 상세 비교")
            st.caption("같은 지표의 두 선수 값을 바로 옆에 배치했습니다.")

            receive_attempts_table = pd.DataFrame(
                {
                    "상황": receive_compare_df["상황"],
                    selected_player_a: receive_compare_df["리시브시도_A"].astype(int),
                    selected_player_b: receive_compare_df["리시브시도_B"].astype(int),
                }
            )
            receive_exact_table = pd.DataFrame(
                {
                    "상황": receive_compare_df["상황"],
                    selected_player_a: receive_compare_df["정확리시브율_%_A"].round(1),
                    selected_player_b: receive_compare_df["정확리시브율_%_B"].round(1),
                }
            )
            receive_fail_table = pd.DataFrame(
                {
                    "상황": receive_compare_df["상황"],
                    selected_player_a: receive_compare_df["실패율_%_A"].round(1),
                    selected_player_b: receive_compare_df["실패율_%_B"].round(1),
                }
            )
            receive_eff_table = pd.DataFrame(
                {
                    "상황": receive_compare_df["상황"],
                    selected_player_a: receive_compare_df["리시브효율_%_A"].round(1),
                    selected_player_b: receive_compare_df["리시브효율_%_B"].round(1),
                }
            )

            receive_table_height = 58 + 54 * len(receive_compare_df) + 8
            rc1, rc2 = st.columns(2)
            rc3, rc4 = st.columns(2)

            with rc1:
                st.markdown("#### 리시브 시도")
                st.dataframe(
                    receive_attempts_table,
                    use_container_width=True,
                    hide_index=True,
                    height=receive_table_height,
                )
            with rc2:
                st.markdown("#### 정확 리시브율")
                st.dataframe(
                    receive_exact_table,
                    use_container_width=True,
                    hide_index=True,
                    height=receive_table_height,
                    column_config={
                        selected_player_a: st.column_config.NumberColumn(format="%.1f%%"),
                        selected_player_b: st.column_config.NumberColumn(format="%.1f%%"),
                    },
                )
            with rc3:
                st.markdown("#### 리시브 실패율")
                st.dataframe(
                    receive_fail_table,
                    use_container_width=True,
                    hide_index=True,
                    height=receive_table_height,
                    column_config={
                        selected_player_a: st.column_config.NumberColumn(format="%.1f%%"),
                        selected_player_b: st.column_config.NumberColumn(format="%.1f%%"),
                    },
                )
            with rc4:
                st.markdown("#### 리시브 효율")
                st.dataframe(
                    receive_eff_table,
                    use_container_width=True,
                    hide_index=True,
                    height=receive_table_height,
                    column_config={
                        selected_player_a: st.column_config.NumberColumn(format="%.1f%%"),
                        selected_player_b: st.column_config.NumberColumn(format="%.1f%%"),
                    },
                )


# ==========================================
# 개별 선수 상세
# ==========================================

if (
    analysis_mode == "개별 선수"
    and selected_player is not None
):
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

    if player_df.empty and player_receive_df.empty:
        st.info("선택한 범위에서 이 선수의 기록이 없습니다.")

    else:
        attack = attack_summary(player_df)
        receive = receive_summary(player_receive_df)

        if not player_df.empty:
            player_team = str(player_df["팀"].iloc[0])
            player_team_code = str(player_df["팀코드"].iloc[0])
            player_season_code = str(player_df["시즌코드"].iloc[0])
        else:
            player_team = str(player_receive_df["팀"].iloc[0])
            player_team_code = str(player_receive_df["팀코드"].iloc[0])
            player_season_code = str(player_receive_df["시즌코드"].iloc[0])

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

        individual_detail_type = st.radio(
            "세부 지표",
            ["공격", "리시브"],
            horizontal=True,
            key="individual_detail_type",
        )

        if individual_detail_type == "공격":
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

            st.caption(
                "공격 효율 = (공격 성공 - 공격 범실 - 블로킹 당함) / 공격 시도."
            )
        else:
            r1, r2, r3, r4 = st.columns(4)

            exact_rate = (
                receive["리시브정확"] / receive["리시브시도"] * 100
                if receive["리시브시도"]
                else 0
            )
            fail_rate = (
                receive["리시브실패"] / receive["리시브시도"] * 100
                if receive["리시브시도"]
                else 0
            )

            r1.metric(
                "리시브 시도",
                f"{receive['리시브시도']:,}회",
            )
            r2.metric(
                "정확 리시브율",
                f"{exact_rate:.1f}%",
            )
            r3.metric(
                "리시브 실패율",
                f"{fail_rate:.1f}%",
            )
            r4.metric(
                "리시브 효율",
                f"{receive['리시브효율_%']:.1f}%",
            )

            st.caption(
                "리시브 효율 = (정확 리시브 - 리시브 실패) / 리시브 시도."
            )

        player_color = get_team_color(
            player_season_code,
            player_team_code,
        )

        if individual_detail_type == "공격":
            if player_df.empty:
                st.info(
                    "이 선수는 선택한 범위에서 공격 기록이 없어 "
                    "공격 상황별 그래프는 표시하지 않습니다."
                )

            if not player_df.empty:
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

                plain3_mask = plain_three_point_mask(player_df)

                if plain3_mask is not None:
                    close3 = player_df[plain3_mask]
                    s = attack_summary(close3)

                    close_rows.append(
                        {
                            "상황": "3점차 이내",
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
                        "3점차 이내는 공격 직전 점수 기준으로 세트 진행 시점과 관계없이 "
                        "점수차가 3점 이내인 공격입니다. 후반 3점차 이내는 1~4세트는 한 팀이라도 "
                        "20점 이상, 5세트는 한 팀이라도 10점 이상인 후반 상황까지 함께 적용합니다."
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


        else:
            # ------------------------------
            # 리시브 상황별 분석
            # ------------------------------
            if not player_receive_df.empty:
                st.divider()
                st.subheader("상황별 리시브")

                st.caption(
                    "점수차 기준은 리시브가 발생한 랠리 시작 직전 점수입니다. "
                    "'3점차 이내'는 세트 진행 시점과 관계없이 적용합니다."
                )

                receive_situation = receive_comparison_rows(
                    player_receive_df
                )

                fig_receive_individual = px.bar(
                    receive_situation,
                    x="상황",
                    y="리시브효율_%",
                    text=[
                        f"{rate:.1f}%<br>{int(attempt):,}회"
                        for rate, attempt in zip(
                            receive_situation["리시브효율_%"],
                            receive_situation["리시브시도"],
                        )
                    ],
                    custom_data=[
                        "리시브시도",
                        "리시브정확",
                        "리시브실패",
                        "정확리시브율_%",
                        "실패율_%",
                    ],
                    labels={
                        "상황": "",
                        "리시브효율_%": "리시브 효율 (%)",
                    },
                )

                fig_receive_individual.update_traces(
                    marker_color=player_color,
                    textposition="outside",
                    cliponaxis=False,
                    textfont=dict(
                        size=14,
                        color="black",
                    ),
                    hovertemplate=(
                        "%{x}<br>"
                        "리시브 효율 %{y:.1f}%<br>"
                        "리시브 시도 %{customdata[0]:,}회<br>"
                        "정확 %{customdata[1]:,}회<br>"
                        "실패 %{customdata[2]:,}회<br>"
                        "정확 리시브율 %{customdata[3]:.1f}%<br>"
                        "실패율 %{customdata[4]:.1f}%"
                        "<extra></extra>"
                    ),
                )

                max_individual_receive = (
                    float(receive_situation["리시브효율_%"].max())
                    if not receive_situation.empty
                    else 0
                )

                fig_receive_individual.update_layout(
                    height=600,
                    margin=dict(l=60, r=40, t=50, b=100),
                    bargap=0.32,
                    font=dict(
                        size=BODY_TEXT_SIZE,
                        color="black",
                    ),
                    xaxis=dict(
                        tickfont=dict(size=16, color="black"),
                        showline=True,
                        linecolor="black",
                    ),
                    yaxis=dict(
                        range=[0, max_individual_receive + 18],
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
                    showlegend=False,
                )

                st.plotly_chart(
                    fig_receive_individual,
                    use_container_width=True,
                )

                st.markdown("### 리시브 상세")

                receive_detail = receive_situation[
                    [
                        "상황",
                        "리시브시도",
                        "리시브정확",
                        "리시브실패",
                        "정확리시브율_%",
                        "실패율_%",
                        "리시브효율_%",
                    ]
                ].copy()

                receive_detail.columns = [
                    "상황",
                    "리시브 시도",
                    "리시브 정확",
                    "리시브 실패",
                    "정확 리시브율 (%)",
                    "실패율 (%)",
                    "리시브 효율 (%)",
                ]

                for col in [
                    "정확 리시브율 (%)",
                    "실패율 (%)",
                    "리시브 효율 (%)",
                ]:
                    receive_detail[col] = receive_detail[col].round(1)

                st.dataframe(
                    receive_detail,
                    use_container_width=True,
                    hide_index=True,
                    height=58 + 54 * len(receive_detail) + 8,
                    column_config={
                        "정확 리시브율 (%)": st.column_config.NumberColumn(format="%.1f%%"),
                        "실패율 (%)": st.column_config.NumberColumn(format="%.1f%%"),
                        "리시브 효율 (%)": st.column_config.NumberColumn(format="%.1f%%"),
                    },
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
            "리시브 효율",
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

    max_receive_attempts = (
        int(
            receive_scope
            .groupby(["팀코드", "선수"])
            .size()
            .max()
        )
        if not receive_scope.empty
        else 1
    )

    if ranking_type == "리시브 효율":
        min_receive_attempts = st.number_input(
            "최소 리시브 시도",
            min_value=1,
            max_value=max(max_receive_attempts, 1),
            value=min(
                default_min_attempts,
                max(max_receive_attempts, 1),
            ),
            step=1,
            key="top10_min_receive_attempts",
        )
    else:
        min_receive_attempts = 1


    if ranking_type in ["리시브 시도", "리시브 효율"]:
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

            if ranking_type == "리시브 효율":
                receive_rank = receive_rank[
                    receive_rank["리시브시도"]
                    >= min_receive_attempts
                ].copy()
                receive_rank = (
                    receive_rank
                    .sort_values(
                        ["리시브효율_%", "리시브시도"],
                        ascending=[False, False],
                    )
                    .head(10)
                    .reset_index(drop=True)
                )
            else:
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
                52
                + 42 * len(receive_table)
                + 12
            )

            st.dataframe(
                receive_table,
                use_container_width=True,
                height=top10_height,
            )
            if ranking_type == "리시브 효율":
                st.caption(
                    f"최소 리시브 시도 {min_receive_attempts:,}회 이상 선수만 포함합니다."
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
            52
            + 42 * len(attack_table)
            + 12
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
