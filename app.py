import streamlit as st

st.set_page_config(
    page_title="여자배구 데이터 대시보드",
    page_icon="🏐",
    layout="wide",
)

st.title("🏐 여자배구 데이터 대시보드")
st.caption("2025-26 V-League 여자부 데이터 분석")

st.info(
    "지금은 사이트의 기본 뼈대만 만든 상태입니다. "
    "다음 단계에서 실제 경기 데이터를 연결합니다."
)

st.subheader("준비 중인 메뉴")
st.write("- 팀 분석")
st.write("- 선수 분석")
st.write("- 루트 분석")
st.write("- 경기 환경")
