import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="여자배구 데이터 대시보드",
    page_icon="🏐",
    layout="wide",
)

@st.cache_data
def load_routes():
    return pd.read_parquet("season_routes_2526.parquet")

df = load_routes()

st.title("🏐 여자배구 데이터 대시보드")
st.caption("2025-26 V-League 여자부 데이터 분석")

st.success("실제 경기 데이터 연결 완료")

col1, col2, col3, col4 = st.columns(4)

col1.metric("공격 이벤트", f"{len(df):,}회")
col2.metric("경기", f"{df['경기번호'].nunique():,}경기")
col3.metric("팀", f"{df['팀'].nunique()}팀")
col4.metric("공격 선수", f"{df['공격수'].nunique()}명")

st.divider()

st.subheader("데이터 확인")

competition_options = ["전체"] + sorted(
    df["대회구분"].dropna().astype(str).unique().tolist()
)

selected_competition = st.selectbox(
    "대회 구분",
    competition_options,
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
)

if selected_team != "전체":
    filtered = filtered[
        filtered["팀"].astype(str) == selected_team
    ]

st.write(
    f"현재 조건의 공격 이벤트: **{len(filtered):,}회**"
)

preview_columns = [
    "경기일",
    "대회구분",
    "팀",
    "상대팀",
    "세트",
    "공격수",
    "공격유형",
    "공격결과",
]

preview_columns = [
    col for col in preview_columns
    if col in filtered.columns
]

st.dataframe(
    filtered[preview_columns].head(20),
    use_container_width=True,
    hide_index=True,
)

st.caption(
    "이 화면은 데이터 연결 확인용입니다. "
    "다음 단계에서 홈 화면과 팀·선수 분석 화면을 본격적으로 구성합니다."
)
