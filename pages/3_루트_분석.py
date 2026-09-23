import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from team_config import get_team_color

PAGE_TITLE_SIZE = 52
SECTION_TITLE_SIZE = 40
SUBSECTION_TITLE_SIZE = 32
BODY_TEXT_SIZE = 20
METRIC_VALUE_SIZE = 46
METRIC_LABEL_SIZE = 22
BAR_LABEL_SIZE = 15
AXIS_TITLE_SIZE = 18
AXIS_TICK_SIZE = 16
POSTSEASON = ["준플레이오프", "플레이오프", "챔피언결정전"]

st.set_page_config(page_title="루트 분석 | 여자배구 데이터 대시보드", page_icon="🏐", layout="wide")
st.markdown(
    f"""
    <style>
    html, body, [class*="css"] {{ color:black; font-size:{BODY_TEXT_SIZE}px; }}
    .stMarkdown, .stCaption, .stMetric, label, p, div {{ color:black; font-size:{BODY_TEXT_SIZE}px; }}
    h1 {{ font-size:{PAGE_TITLE_SIZE}px !important; }}
    h2 {{ font-size:{SECTION_TITLE_SIZE}px !important; }}
    h3 {{ font-size:{SUBSECTION_TITLE_SIZE}px !important; }}
    [data-testid="stMetricValue"] {{ font-size:{METRIC_VALUE_SIZE}px !important; }}
    [data-testid="stMetricLabel"] {{ font-size:{METRIC_LABEL_SIZE}px !important; }}
    </style>
    """, unsafe_allow_html=True,
)

@st.cache_data
def load_data():
    routes = pd.read_parquet("routes_3touch_2526.parquet")
    games = pd.read_parquet("games_2526_all.parquet")
    for c in ["공격성공", "공격범실", "블로킹당함"]:
        routes[c] = routes[c].fillna(False).astype(bool)
    return routes, games

routes, games = load_data()

def season_label_map(routes, games):
    mapping = {}
    if "시즌코드" in games.columns and "시즌명" in games.columns:
        tmp = games[["시즌코드", "시즌명"]].dropna().drop_duplicates()
        mapping.update(dict(zip(tmp["시즌코드"].astype(str), tmp["시즌명"].astype(str))))
    if "시즌코드" in routes.columns and "시즌명" in routes.columns:
        tmp = routes[["시즌코드", "시즌명"]].dropna().drop_duplicates()
        mapping.update(dict(zip(tmp["시즌코드"].astype(str), tmp["시즌명"].astype(str))))
    # Current dataset fallback: never expose the internal API season code to users.
    mapping.setdefault("022", "2025-26")
    return mapping

def apply_scope(df, scope):
    if scope == "정규리그":
        return df[df["대회구분"].astype(str) == "정규리그"].copy()
    if scope == "포스트시즌":
        return df[df["대회구분"].astype(str).isin(POSTSEASON)].copy()
    if scope.endswith("라운드"):
        return df[
            (df["대회구분"].astype(str) == "정규리그")
            & (df["경기구분"].astype(str) == scope)
        ].copy()
    if scope in POSTSEASON:
        return df[df["대회구분"].astype(str) == scope].copy()
    return df.copy()

def summarize(df):
    n = len(df)
    s = int(df["공격성공"].sum()) if n else 0
    e = int(df["공격범실"].sum()) if n else 0
    b = int(df["블로킹당함"].sum()) if n else 0
    return n, (s / n * 100 if n else 0), ((s-e-b) / n * 100 if n else 0)

labels = season_label_map(routes, games)
season_codes = sorted(routes["시즌코드"].dropna().astype(str).unique(), reverse=True)

st.title("루트 분석")
st.caption("기록된 기점 → 연결선수 → 공격수 흐름과 이후 공격 결과를 봅니다.")

with st.sidebar:
    st.header("루트 분석 필터")
    selected_code = st.selectbox(
        "시즌", season_codes,
        format_func=lambda x: labels.get(str(x), str(x)),
    )
    season_df = routes[routes["시즌코드"].astype(str) == str(selected_code)].copy()

    team_options = ["전체 팀"] + sorted(season_df["팀"].dropna().astype(str).unique())
    selected_team = st.selectbox("팀", team_options)
    team_df = season_df if selected_team == "전체 팀" else season_df[season_df["팀"].astype(str) == selected_team]

    comps = set(team_df["대회구분"].dropna().astype(str).unique())
    rounds = set(team_df["경기구분"].dropna().astype(str).unique())
    scopes = ["시즌 전체", "정규리그"]
    if any(x in comps for x in POSTSEASON):
        scopes.append("포스트시즌")
    scopes += [f"{n}라운드" for n in range(1,7) if f"{n}라운드" in rounds]
    scopes += [x for x in POSTSEASON if x in comps]
    selected_scope = st.selectbox("분석 범위", scopes)

    with st.expander("상세 필터"):
        positions = ["전체 포지션"] + sorted(team_df["공격수포지션"].dropna().astype(str).unique())
        selected_position = st.selectbox("공격수 포지션", positions)
        detail_df = team_df if selected_position == "전체 포지션" else team_df[team_df["공격수포지션"].astype(str) == selected_position]
        players = ["전체 선수"] + sorted(detail_df["공격수"].dropna().astype(str).unique())
        selected_player = st.selectbox("공격수", players)
        top_n = st.slider("흐름에 표시할 상위 조합", 5, 20, 10, 5)

filtered = apply_scope(team_df, selected_scope)
if selected_position != "전체 포지션":
    filtered = filtered[filtered["공격수포지션"].astype(str) == selected_position]
if selected_player != "전체 선수":
    filtered = filtered[filtered["공격수"].astype(str) == selected_player]

if filtered.empty:
    st.info("선택한 조건에 해당하는 기록된 루트가 없습니다.")
    st.stop()

n, rate, eff = summarize(filtered)
origin_counts = filtered["기점유형"].fillna("기타").astype(str).value_counts()
top_origin = origin_counts.index[0] if len(origin_counts) else "-"

c1,c2,c3,c4 = st.columns(4)
c1.metric("기록된 루트", f"{n:,}회")
c2.metric("공격 성공률", f"{rate:.1f}%")
c3.metric("공격 효율", f"{eff:.1f}%")
c4.metric("가장 많은 기점", top_origin)
st.caption("루트는 실시간 기록에서 기점과 연결선수가 확인된 공격만 포함하며, 실제 랠리의 모든 터치를 의미하지 않습니다.")

st.divider()
st.subheader("기점 → 연결선수 → 공격수")

if selected_team == "전체 팀":
    st.info("선수 단위 흐름은 팀을 선택하면 표시됩니다. 전체 팀에서는 아래 기점 유형 비교를 이용해 주세요.")
else:
    flow = (
        filtered.dropna(subset=["기점유형","연결선수","공격수"])
        .groupby(["기점유형","연결선수","공격수"])
        .size().reset_index(name="루트수")
        .sort_values("루트수", ascending=False).head(top_n)
    )
    if flow.empty:
        st.info("표시할 루트 조합이 없습니다.")
    else:
        origins = flow["기점유형"].astype(str).unique().tolist()
        connectors = flow["연결선수"].astype(str).unique().tolist()
        attackers = flow["공격수"].astype(str).unique().tolist()
        node_labels = [f"기점 | {x}" for x in origins] + [f"연결 | {x}" for x in connectors] + [f"공격 | {x}" for x in attackers]
        idx = {v:i for i,v in enumerate(node_labels)}

        left = flow.groupby(["기점유형","연결선수"], as_index=False)["루트수"].sum()
        source=[]; target=[]; value=[]; hover=[]
        for _,r in left.iterrows():
            source.append(idx[f"기점 | {r['기점유형']}"])
            target.append(idx[f"연결 | {r['연결선수']}"])
            value.append(int(r["루트수"]))
            hover.append(f"{r['기점유형']} → {r['연결선수']}: {int(r['루트수']):,}회")
        right = flow.groupby(["연결선수","공격수"], as_index=False)["루트수"].sum()
        for _,r in right.iterrows():
            source.append(idx[f"연결 | {r['연결선수']}"])
            target.append(idx[f"공격 | {r['공격수']}"])
            value.append(int(r["루트수"]))
            hover.append(f"{r['연결선수']} → {r['공격수']}: {int(r['루트수']):,}회")

        fig = go.Figure(go.Sankey(
            arrangement="snap",
            node=dict(label=node_labels, pad=22, thickness=18, line=dict(color="rgba(0,0,0,0.35)", width=0.7)),
            link=dict(source=source, target=target, value=value, customdata=hover, hovertemplate="%{customdata}<extra></extra>"),
        ))
        fig.update_layout(height=max(540, 42*len(node_labels)), margin=dict(l=20,r=20,t=20,b=20), font=dict(size=15, color="black"))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"선 굵기는 상위 {top_n}개 기록 조합의 빈도를 나타냅니다.")

st.divider()
st.subheader("기점 유형별 공격 결과")
origin = (
    filtered.assign(기점=filtered["기점유형"].fillna("기타").astype(str))
    .groupby("기점")
    .agg(공격시도=("공격수","size"), 공격성공=("공격성공","sum"), 공격범실=("공격범실","sum"), 블로킹당함=("블로킹당함","sum"))
    .reset_index()
)
origin["공격성공률_%"] = origin["공격성공"]/origin["공격시도"]*100
origin["공격효율_%"] = (origin["공격성공"]-origin["공격범실"]-origin["블로킹당함"])/origin["공격시도"]*100
origin = origin.sort_values("공격시도", ascending=False)

fig_o = px.bar(origin, x="기점", y="공격성공률_%",
    text=[f"{r:.1f}%<br>({n:,}회)" for r,n in zip(origin["공격성공률_%"],origin["공격시도"])],
    custom_data=["공격시도","공격효율_%"],
    labels={"기점":"","공격성공률_%":"공격 성공률 (%)"})
fig_o.update_traces(textposition="outside", cliponaxis=False, textfont=dict(size=BAR_LABEL_SIZE,color="black"),
    hovertemplate="%{x}<br>공격 성공률 %{y:.1f}%<br>기록 %{customdata[0]:,}회<br>공격 효율 %{customdata[1]:.1f}%<extra></extra>")
fig_o.update_layout(height=500, showlegend=False, margin=dict(t=55,b=40),
    font=dict(size=BODY_TEXT_SIZE,color="black"),
    xaxis=dict(tickfont=dict(size=AXIS_TICK_SIZE,color="black")),
    yaxis=dict(range=[0,max(origin["공격성공률_%"].max()+12,12)],ticksuffix="%",tickfont=dict(size=AXIS_TICK_SIZE,color="black"),title_font=dict(size=AXIS_TITLE_SIZE,color="black"),gridcolor="rgba(0,0,0,0.12)"))
st.plotly_chart(fig_o,use_container_width=True)

table = origin[["기점","공격시도","공격성공률_%","공격효율_%"]].copy()
table.columns=["기점","기록 수","공격 성공률 (%)","공격 효율 (%)"]
table["공격 성공률 (%)"]=table["공격 성공률 (%)"].round(1)
table["공격 효율 (%)"]=table["공격 효율 (%)"].round(1)
st.dataframe(table,use_container_width=True,hide_index=True)

st.divider()
st.subheader("연결선수 → 공격수 조합 TOP 10")
pairs = (
    filtered.dropna(subset=["연결선수","공격수"])
    .groupby(["연결선수","공격수"])
    .agg(루트수=("공격수","size"),공격성공=("공격성공","sum"),공격범실=("공격범실","sum"),블로킹당함=("블로킹당함","sum"))
    .reset_index()
)
pairs["공격성공률_%"]=pairs["공격성공"]/pairs["루트수"]*100
pairs["공격효율_%"]=(pairs["공격성공"]-pairs["공격범실"]-pairs["블로킹당함"])/pairs["루트수"]*100
pairs["조합"]=pairs["연결선수"].astype(str)+" → "+pairs["공격수"].astype(str)
pairs=pairs.sort_values(["루트수","공격성공률_%"],ascending=[False,False]).head(10).sort_values("루트수")

fig_p=px.bar(pairs,x="루트수",y="조합",orientation="h",
    text=[f"{n:,}회 | {r:.1f}%" for n,r in zip(pairs["루트수"],pairs["공격성공률_%"])],
    custom_data=["공격성공률_%","공격효율_%"],
    labels={"루트수":"기록 수","조합":""})
fig_p.update_traces(textposition="outside",cliponaxis=False,textfont=dict(size=14,color="black"),
    hovertemplate="%{y}<br>기록 %{x:,}회<br>공격 성공률 %{customdata[0]:.1f}%<br>공격 효율 %{customdata[1]:.1f}%<extra></extra>")
fig_p.update_layout(height=600,showlegend=False,margin=dict(l=20,r=130,t=30,b=40),
    font=dict(size=BODY_TEXT_SIZE,color="black"),
    xaxis=dict(tickfont=dict(size=AXIS_TICK_SIZE,color="black"),title_font=dict(size=AXIS_TITLE_SIZE,color="black"),gridcolor="rgba(0,0,0,0.12)"),
    yaxis=dict(tickfont=dict(size=15,color="black")))
st.plotly_chart(fig_p,use_container_width=True)
st.caption("막대는 조합이 기록된 횟수이며, 막대 끝의 %는 해당 조합 뒤 공격 성공률입니다.")

st.markdown("### 연결선수별 공격수 성공률")
st.caption("연결선수를 선택하면 해당 선수의 연결 이후 공격수를 공격 성공률 순으로 비교합니다.")

connector_options = sorted(
    filtered["연결선수"].dropna().astype(str).unique().tolist()
)
if connector_options:
    fc1, fc2 = st.columns([2, 1])
    with fc1:
        selected_connector = st.selectbox(
            "연결선수",
            connector_options,
            key="route_connector_detail",
        )
    connector_base = filtered[
        filtered["연결선수"].astype(str) == selected_connector
    ].copy()
    max_connection_count = max(
        int(connector_base.groupby("공격수").size().max()),
        1,
    )
    default_min_connection = min(30, max_connection_count)
    with fc2:
        min_connection_count = st.number_input(
            "최소 연결 수",
            min_value=1,
            max_value=max_connection_count,
            value=default_min_connection,
            step=1,
            key="route_min_connection_count",
        )

    connector_attackers = (
        connector_base.dropna(subset=["공격수"])
        .groupby("공격수")
        .agg(
            연결수=("공격수", "size"),
            공격성공=("공격성공", "sum"),
            공격범실=("공격범실", "sum"),
            블로킹당함=("블로킹당함", "sum"),
        )
        .reset_index()
    )
    connector_attackers["공격성공률_%"] = (
        connector_attackers["공격성공"] / connector_attackers["연결수"] * 100
    )
    connector_attackers["공격효율_%"] = (
        connector_attackers["공격성공"]
        - connector_attackers["공격범실"]
        - connector_attackers["블로킹당함"]
    ) / connector_attackers["연결수"] * 100
    connector_attackers = connector_attackers[
        connector_attackers["연결수"] >= min_connection_count
    ].sort_values(
        ["공격성공률_%", "연결수"],
        ascending=[False, False],
    )

    if connector_attackers.empty:
        st.info("현재 최소 연결 수 기준을 충족하는 공격수가 없습니다.")
    else:
        connector_chart = connector_attackers.sort_values(
            ["공격성공률_%", "연결수"],
            ascending=[True, True],
        )
        fig_connector_attackers = px.bar(
            connector_chart,
            x="공격성공률_%",
            y="공격수",
            orientation="h",
            text=[
                f"{rate:.1f}% | {count:,}회"
                for rate, count in zip(
                    connector_chart["공격성공률_%"],
                    connector_chart["연결수"],
                )
            ],
            custom_data=["연결수", "공격효율_%"],
            labels={
                "공격성공률_%": "공격 성공률 (%)",
                "공격수": "",
            },
        )
        fig_connector_attackers.update_traces(
            textposition="outside",
            cliponaxis=False,
            textfont=dict(size=14, color="black"),
            hovertemplate=(
                "%{y}<br>"
                "공격 성공률 %{x:.1f}%<br>"
                "연결 수 %{customdata[0]:,}회<br>"
                "공격 효율 %{customdata[1]:.1f}%"
                "<extra></extra>"
            ),
        )
        fig_connector_attackers.update_layout(
            height=max(360, 70 * len(connector_chart)),
            showlegend=False,
            margin=dict(l=20, r=130, t=30, b=45),
            font=dict(size=BODY_TEXT_SIZE, color="black"),
            xaxis=dict(
                range=[0, max(connector_chart["공격성공률_%"].max() + 12, 12)],
                ticksuffix="%",
                tickfont=dict(size=AXIS_TICK_SIZE, color="black"),
                title_font=dict(size=AXIS_TITLE_SIZE, color="black"),
                gridcolor="rgba(0,0,0,0.12)",
            ),
            yaxis=dict(tickfont=dict(size=15, color="black")),
        )
        st.plotly_chart(fig_connector_attackers, use_container_width=True)
        st.caption(
            f"{selected_connector}의 연결이 최소 {min_connection_count:,}회 이상 기록된 공격수만 표시합니다. "
            "정렬은 공격 성공률이 높은 순입니다."
        )
else:
    st.info("선택한 조건에서 연결선수 기록이 없습니다.")


st.divider()
st.subheader("특수 루트")
special=[]
self_df=filtered[filtered["기점선수"].notna() & (filtered["기점선수"].astype(str)==filtered["공격수"].astype(str))]
sn,sr,se=summarize(self_df)
special.append({"상황":"기점선수 = 공격수","기록 수":sn,"공격 성공률 (%)":round(sr,1),"공격 효율 (%)":round(se,1)})
if "연결선수포지션" in filtered.columns:
    ns=filtered[filtered["연결선수포지션"].notna() & (filtered["연결선수포지션"].astype(str)!="S")]
    nn,nr,ne=summarize(ns)
    special.insert(0,{"상황":"비세터 연결","기록 수":nn,"공격 성공률 (%)":round(nr,1),"공격 효율 (%)":round(ne,1)})
st.dataframe(pd.DataFrame(special),use_container_width=True,hide_index=True)
st.caption("※ 모든 루트 수치는 기록된 기점 → 연결선수 → 공격수 조합을 기준으로 합니다.")
