import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="여자배구 데이터 대시보드",
    page_icon="🏐",
    layout="wide",
)

st.markdown(
    """
    <style>
    /* larger dashboard typography */
    html, body, [class*="css"]  {
        font-size: 20px;
    }
    .stMarkdown, .stCaption, .stMetric, label, p, div {
        font-size: 20px;
    }
    h1 { font-size: 52px !important; }
    h2 { font-size: 40px !important; }
    h3 { font-size: 32px !important; }
    [data-testid="stMetricValue"] {
        font-size: 46px !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 22px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

@st.cache_data
def load_routes():
    df = pd.read_parquet("season_routes_2526.parquet")

    if "공격성공" in df.columns:
        df["공격성공"] = df["공격성공"].fillna(False).astype(bool)

    return df

df = load_routes()

# --------------------------------------------------
# Header
# --------------------------------------------------

st.title("🏐 여자배구 데이터 대시보드")
st.caption("2025-26 V-League 여자부 공격 데이터 분석")

# --------------------------------------------------
# Global filters
# --------------------------------------------------

with st.sidebar:
    st.header("필터")

    competition_options = ["전체"] + sorted(
        df["대회구분"].dropna().astype(str).unique().tolist()
    )

    selected_competition = st.selectbox(
        "대회 구분",
        competition_options,
        index=0,
    )

    filtered = df.copy()

    if selected_competition != "전체":
        filtered = filtered[
            filtered["대회구분"].astype(str) == selected_competition
        ]

    team_options = ["전체"] + sorted(
        filtered["팀"].dropna().astype(str).unique().tolist()
    )

    selected_team = st.selectbox(
        "팀",
        team_options,
        index=0,
    )

    if selected_team != "전체":
        filtered = filtered[
            filtered["팀"].astype(str) == selected_team
        ]

    st.caption("필터는 홈 화면 지표와 그래프에 함께 적용됩니다.")

# --------------------------------------------------
# Overview metrics
# --------------------------------------------------

total_attacks = len(filtered)
games = filtered["경기번호"].nunique() if "경기번호" in filtered.columns else 0
players = filtered["공격수"].nunique() if "공격수" in filtered.columns else 0

if total_attacks > 0 and "공격성공" in filtered.columns:
    success_rate = filtered["공격성공"].mean() * 100
else:
    success_rate = 0

st.subheader("시즌 개요")

col1, col2, col3, col4 = st.columns(4)

col1.metric("공격 시도", f"{total_attacks:,}회")
col2.metric("경기", f"{games:,}경기")
col3.metric("공격 선수", f"{players:,}명")
col4.metric("공격 성공률", f"{success_rate:.1f}%")

st.divider()

# --------------------------------------------------
# Team comparison
# --------------------------------------------------

st.subheader("팀별 공격 성공률")

team_summary = (
    filtered
    .groupby("팀", dropna=False)
    .agg(
        공격시도=("공격수", "size"),
        공격성공=("공격성공", "sum"),
    )
    .reset_index()
)

team_summary["공격성공률_%"] = (
    team_summary["공격성공"] /
    team_summary["공격시도"] * 100
).round(1)

team_summary = team_summary.sort_values(
    "공격성공률_%",
    ascending=False
)

fig_team = px.bar(
    team_summary,
    x="팀",
    y="공격성공률_%",
    hover_data={
        "공격시도": ":,",
        "공격성공": ":,",
        "공격성공률_%": ":.1f",
    },
    labels={
        "팀": "",
        "공격성공률_%": "공격 성공률 (%)",
        "공격시도": "공격 시도",
        "공격성공": "공격 성공",
    },
)

fig_team.update_traces(
    textfont=dict(size=20),
    text=[
        f"{rate:.1f}%<br>({attempts:,}회)"
        for rate, attempts in zip(
            team_summary["공격성공률_%"],
            team_summary["공격시도"]
        )
    ],
    textposition="outside",
    cliponaxis=False,
)

fig_team.update_layout(
    height=520,
    margin=dict(l=20, r=20, t=70, b=20),
    hovermode="x unified",
    font=dict(size=20),
    xaxis=dict(tickfont=dict(size=20), title_font=dict(size=22)),
    yaxis=dict(tickfont=dict(size=20), title_font=dict(size=22)),
)

fig_team.update_yaxes(
    range=[
        0,
        max(team_summary["공격성공률_%"]) + 12
    ],
    ticksuffix="%",
)

st.plotly_chart(
    fig_team,
    use_container_width=True,
)

st.caption(
    "공격 성공률 = 공격 성공 횟수 ÷ 공격 시도 횟수. "
    "필터에서 대회 구분이나 팀을 선택하면 그래프도 함께 바뀝니다."
)

st.divider()

# --------------------------------------------------
# Set-by-set view
# --------------------------------------------------

st.subheader("세트별 공격 성공률")

set_summary = (
    filtered
    .groupby("세트", dropna=False)
    .agg(
        공격시도=("공격수", "size"),
        공격성공=("공격성공", "sum"),
    )
    .reset_index()
)

set_summary["공격성공률_%"] = (
    set_summary["공격성공"] /
    set_summary["공격시도"] * 100
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
    textfont=dict(size=20),
    text=[
        f"{rate:.1f}%<br>({attempts:,}회)"
        for rate, attempts in zip(
            set_summary["공격성공률_%"],
            set_summary["공격시도"]
        )
    ],
    textposition="outside",
    cliponaxis=False,
)

fig_set.update_layout(
    height=500,
    margin=dict(l=20, r=20, t=70, b=20),
    font=dict(size=20),
    xaxis=dict(tickfont=dict(size=20), title_font=dict(size=22)),
    yaxis=dict(tickfont=dict(size=20), title_font=dict(size=22)),
)

fig_set.update_yaxes(
    range=[
        0,
        max(set_summary["공격성공률_%"]) + 12
    ],
    ticksuffix="%",
)

st.plotly_chart(
    fig_set,
    use_container_width=True,
)

# --------------------------------------------------
# Quick guide
# --------------------------------------------------

st.divider()

st.subheader("이 대시보드에서 볼 수 있는 것")

guide1, guide2 = st.columns(2)

with guide1:
    st.markdown(
        """
        **팀 분석**
        - 세트별 공격 성공률
        - 점수대별 공격 성공률
        - 클러치 상황
        - 공격 집중도

        **선수 분석**
        - 선수별 공격 기록
        - 세트별·점수대별 변화
        - 클러치 공격
        - 받고 때린 공격
        """
    )

with guide2:
    st.markdown(
        """
        **루트 분석**
        - 리시브·디그 → 연결선수 → 공격수
        - 기점 유형별 공격 결과
        - 비세터 연결 상황

        **경기 환경**
        - 휴식일수
        - 홈·원정
        - 직전 경기장 간 직선거리
        """
    )

st.caption(
    "※ 공격 이벤트는 KOVO 실시간 경기 기록을 기반으로 정리했습니다. "
    "기록이 비어 있는 일부 세트는 이벤트 분석에서 제외됩니다."
)
