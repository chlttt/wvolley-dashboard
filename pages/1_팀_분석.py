import pandas as pd
import plotly.express as px
import streamlit as st

from team_config import get_team_color

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
CHART_TEXT_COLOR = "black"



st.set_page_config(
    page_title="팀 분석 | 여자배구 데이터 대시보드",
    page_icon="🏐",
    layout="wide",
)

st.markdown(
    f"""
    <style>
    html, body, [class*="css"] {{
        color: black; font-size: {BODY_TEXT_SIZE}px; }}
    .stMarkdown, .stCaption, .stMetric, label, p, div {{
        color: black; font-size: {BODY_TEXT_SIZE}px; }}
    h1 {{ font-size: {PAGE_TITLE_SIZE}px !important; }}
    h2 {{ font-size: {SECTION_TITLE_SIZE}px !important; }}
    h3 {{ font-size: {SUBSECTION_TITLE_SIZE}px !important; }}
    [data-testid="stMetricValue"] {{ font-size: {METRIC_VALUE_SIZE}px !important; }}
    [data-testid="stMetricLabel"] {{ font-size: {METRIC_LABEL_SIZE}px !important; }}
    </style>
    """,
    unsafe_allow_html=True,
)

def add_smart_scatter_labels(
    fig,
    data,
    x_col,
    y_col,
    label_col,
    font_size=15,
    point_size=14,
):
    """
    산점도 라벨 자동 배치 규칙
    - 라벨끼리 겹치지 않음
    - 라벨이 다른 점을 덮지 않음
    - 연결선이 다른 라벨을 가로지르지 않음
    - 가능한 한 짧고 단순한 연결선을 사용
    - 첫 화면에서 모든 점과 라벨이 보이도록 여백 확보
    """

    if data.empty:
        return None

    x_min = float(data[x_col].min())
    x_max = float(data[x_col].max())
    y_min = float(data[y_col].min())
    y_max = float(data[y_col].max())

    x_span = max(x_max - x_min, 1.0)
    y_span = max(y_max - y_min, 1.0)

    # 실제 차트 비율에 가까운 가상 픽셀 좌표계
    plot_w = 1100
    plot_h = 520

    def to_px(x, y):
        px = (float(x) - x_min) / x_span * plot_w
        py = (y_max - float(y)) / y_span * plot_h
        return px, py

    def boxes_overlap(a, b, gap=8):
        return not (
            a[2] + gap < b[0]
            or a[0] - gap > b[2]
            or a[3] + gap < b[1]
            or a[1] - gap > b[3]
        )

    def point_in_box(px, py, box, pad=10):
        return (
            box[0] - pad <= px <= box[2] + pad
            and box[1] - pad <= py <= box[3] + pad
        )

    def segment_hits_box(x1, y1, x2, y2, box, samples=24):
        # 선을 여러 점으로 나눠 다른 라벨 박스를 통과하는지 확인
        for j in range(1, samples):
            t = j / samples
            sx = x1 + (x2 - x1) * t
            sy = y1 + (y2 - y1) * t
            if point_in_box(sx, sy, box, pad=4):
                return True
        return False

    def segments_too_close(seg1, seg2, threshold=10):
        # 두 연결선이 서로 지나치게 가까워지는지 근사 검사
        (x1, y1, x2, y2) = seg1
        (a1, b1, a2, b2) = seg2

        pts1 = [
            (
                x1 + (x2 - x1) * t / 12,
                y1 + (y2 - y1) * t / 12,
            )
            for t in range(1, 12)
        ]
        pts2 = [
            (
                a1 + (a2 - a1) * t / 12,
                b1 + (b2 - b1) * t / 12,
            )
            for t in range(1, 12)
        ]

        for px1, py1 in pts1:
            for px2, py2 in pts2:
                if (
                    (px1 - px2) ** 2 + (py1 - py2) ** 2
                ) ** 0.5 < threshold:
                    return True

        return False

    # 가까운 위치부터 탐색. 단순 수직/수평을 먼저 사용.
    candidates = [
        (0, 46),
        (0, -46),
        (58, 0),
        (-58, 0),
        (52, 38),
        (-52, 38),
        (52, -38),
        (-52, -38),
        (0, 68),
        (0, -68),
        (78, 0),
        (-78, 0),
        (70, 48),
        (-70, 48),
        (70, -48),
        (-70, -48),
        (0, 92),
        (0, -92),
        (98, 0),
        (-98, 0),
    ]

    placed_boxes = []
    placed_segments = []

    point_positions = [
        to_px(row[x_col], row[y_col])
        for _, row in data.iterrows()
    ]

    # 밀집된 점부터 먼저 배치하면 충돌 회피가 더 안정적
    work = data.copy().reset_index(drop=True)

    density = []
    for i, row in work.iterrows():
        px, py = to_px(row[x_col], row[y_col])
        nearest = []
        for j, other in work.iterrows():
            if i == j:
                continue
            ox, oy = to_px(other[x_col], other[y_col])
            nearest.append(((px - ox) ** 2 + (py - oy) ** 2) ** 0.5)
        density.append(min(nearest) if nearest else 9999)

    work["_nearest_distance"] = density
    work = work.sort_values("_nearest_distance").drop(
        columns="_nearest_distance"
    )

    for _, row in work.iterrows():
        label = str(row[label_col])
        point_x, point_y = to_px(row[x_col], row[y_col])

        # 한글 라벨 폭을 넉넉하게 계산
        label_w = max(62, len(label) * font_size * 1.28)
        label_h = font_size * 2.05

        best = None
        best_score = float("inf")

        for ax, ay in candidates:
            label_cx = point_x + ax
            label_cy = point_y + ay

            box = (
                label_cx - label_w / 2,
                label_cy - label_h / 2,
                label_cx + label_w / 2,
                label_cy + label_h / 2,
            )

            segment = (
                point_x,
                point_y,
                label_cx,
                label_cy,
            )

            # 기본적으로 짧은 선을 선호
            score = ((ax ** 2 + ay ** 2) ** 0.5) * 0.08

            # 차트 밖으로 나가는 후보는 사실상 제외
            if box[0] < 8:
                score += 20000 + abs(box[0]) * 30
            if box[2] > plot_w - 8:
                score += 20000 + (box[2] - plot_w) * 30
            if box[1] < 8:
                score += 20000 + abs(box[1]) * 30
            if box[3] > plot_h - 8:
                score += 20000 + (box[3] - plot_h) * 30

            # 기존 라벨과 겹치면 강하게 제외
            for prev_box in placed_boxes:
                if boxes_overlap(box, prev_box, gap=10):
                    score += 50000

                # 새 연결선이 기존 라벨을 관통하지 않게 함
                if segment_hits_box(
                    point_x,
                    point_y,
                    label_cx,
                    label_cy,
                    prev_box,
                ):
                    score += 30000

            # 새 라벨이 다른 점을 덮지 않게 함
            for other_x, other_y in point_positions:
                if (
                    abs(other_x - point_x) < 1
                    and abs(other_y - point_y) < 1
                ):
                    continue

                if point_in_box(
                    other_x,
                    other_y,
                    box,
                    pad=point_size + 5,
                ):
                    score += 30000

            # 연결선끼리도 최대한 겹치거나 교차하지 않게 함
            for prev_segment in placed_segments:
                if segments_too_close(
                    segment,
                    prev_segment,
                    threshold=8,
                ):
                    score += 12000

            if score < best_score:
                best_score = score
                best = (
                    ax,
                    ay,
                    box,
                    segment,
                )

        ax, ay, box, segment = best
        placed_boxes.append(box)
        placed_segments.append(segment)

        fig.add_annotation(
            x=row[x_col],
            y=row[y_col],
            text=label,
            showarrow=True,
            arrowhead=0,
            arrowsize=1,
            arrowwidth=1,
            arrowcolor="black",
            ax=ax,
            ay=ay,
            font=dict(
                size=font_size,
                color="black",
            ),
            # 완전 불투명 흰색: 그리드/선이 글자를 통과해 보이지 않게 함
            bgcolor="white",
            bordercolor="rgba(0,0,0,0)",
            borderpad=3,
        )

    # 첫 화면에서 점과 라벨이 모두 보이도록 넉넉한 범위
    x_padding = max(x_span * 0.18, 2.0)
    y_padding = max(y_span * 0.22, 2.0)

    return (
        [x_min - x_padding, x_max + x_padding],
        [y_min - y_padding, y_max + y_padding],
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

selected_season_code = team_df["시즌코드"].astype(str).iloc[0]
selected_team_code = team_df["팀코드"].astype(str).iloc[0]

selected_team_color = get_team_color(
    selected_season_code,
    selected_team_code
)

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
    marker_color=selected_team_color,
    text=[
        f"{rate:.1f}%<br>({attempt:,}회)"
        for rate, attempt in zip(
            set_summary["공격성공률_%"],
            set_summary["공격시도"]
        )
    ],
    textposition="outside",
    cliponaxis=False,
    textfont=dict(size=BAR_LABEL_SIZE, color=CHART_TEXT_COLOR),
)

fig_set.update_layout(
    height=520,
    margin=dict(l=20, r=20, t=70, b=20),
    font=dict(size=BODY_TEXT_SIZE, color=CHART_TEXT_COLOR),
    xaxis=dict(
        tickmode="linear",
        dtick=1,
        tickfont=dict(size=BODY_TEXT_SIZE, color=X_AXIS_TEXT_COLOR),
        title_font=dict(size=AXIS_TITLE_SIZE, color=X_AXIS_TEXT_COLOR),
    ),
    yaxis=dict(
        tickfont=dict(size=BODY_TEXT_SIZE, color=CHART_TEXT_COLOR),
        title_font=dict(size=AXIS_TITLE_SIZE, color=CHART_TEXT_COLOR),
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
    marker_color=selected_team_color,
    text=[
        f"{rate:.1f}%<br>({attempt:,}회)"
        for rate, attempt in zip(
            score_summary["공격성공률_%"],
            score_summary["공격시도"]
        )
    ],
    textposition="outside",
    cliponaxis=False,
    textfont=dict(size=BAR_LABEL_SIZE, color=CHART_TEXT_COLOR),
)

fig_score.update_layout(
    height=500,
    margin=dict(l=20, r=20, t=70, b=20),
    font=dict(size=BODY_TEXT_SIZE, color=CHART_TEXT_COLOR),
    xaxis=dict(tickfont=dict(size=BODY_TEXT_SIZE, color=X_AXIS_TEXT_COLOR)),
    yaxis=dict(
        tickfont=dict(size=BODY_TEXT_SIZE, color=CHART_TEXT_COLOR),
        title_font=dict(size=AXIS_TITLE_SIZE, color=CHART_TEXT_COLOR),
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
    marker_color=selected_team_color,
    text=[
        f"{share:.1f}%"
        for share in player_summary["공격점유율_%"]
    ],
    textposition="outside",
    cliponaxis=False,
    textfont=dict(size=TEAM_NAME_SIZE, color=CHART_TEXT_COLOR),
)

fig_player.update_layout(
    height=540,
    margin=dict(l=20, r=20, t=70, b=80),
    font=dict(size=BODY_TEXT_SIZE, color=CHART_TEXT_COLOR),
    xaxis=dict(tickfont=dict(size=TEAM_NAME_SIZE, color=X_AXIS_TEXT_COLOR)),
    yaxis=dict(
        tickfont=dict(size=BODY_TEXT_SIZE, color=CHART_TEXT_COLOR),
        title_font=dict(size=AXIS_TITLE_SIZE, color=CHART_TEXT_COLOR),
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

st.divider()

st.subheader("교차 분석")

analysis_level = st.selectbox(
    "비교 대상",
    ["선수", "팀"],
    key="cross_analysis_level",
)

if analysis_level == "선수":
    metric_option = st.selectbox(
        "지표 조합",
        [
            "공격점유율 × 공격효율",
            "공격점유율 × 공격성공률",
            "공격성공률 × 공격효율",
        ],
        key="player_cross_metric",
    )

    cross_df = (
        team_df
        .groupby(["공격수", "공격수포지션"], dropna=False)
        .agg(
            공격시도=("공격수", "size"),
            공격성공=("공격성공", "sum"),
            공격범실=("공격범실", "sum"),
            블로킹당함=("블로킹당함", "sum"),
        )
        .reset_index()
    )

    cross_df["공격점유율_%"] = (
        cross_df["공격시도"] / cross_df["공격시도"].sum() * 100
    ).round(1)

    cross_df["공격성공률_%"] = (
        cross_df["공격성공"] / cross_df["공격시도"] * 100
    ).round(1)

    cross_df["공격효율_%"] = (
        (
            cross_df["공격성공"]
            - cross_df["공격범실"]
            - cross_df["블로킹당함"]
        )
        / cross_df["공격시도"]
        * 100
    ).round(1)

    if selected_scope in ["전체", "정규리그"]:
        default_min_attempts = 20
    elif selected_scope == "포스트시즌" or selected_scope.endswith("라운드"):
        default_min_attempts = 10
    else:
        default_min_attempts = 5

    min_attempts = st.number_input(
        "최소 공격 시도",
        min_value=1,
        max_value=max(int(cross_df["공격시도"].max()), 1),
        value=min(
            default_min_attempts,
            max(int(cross_df["공격시도"].max()), 1),
        ),
        step=1,
        key="player_cross_min_attempts",
    )

    cross_df = cross_df[
        cross_df["공격시도"] >= min_attempts
    ].copy()

    metric_map = {
        "공격점유율 × 공격효율": ("공격점유율_%", "공격효율_%"),
        "공격점유율 × 공격성공률": ("공격점유율_%", "공격성공률_%"),
        "공격성공률 × 공격효율": ("공격성공률_%", "공격효율_%"),
    }

    x_col, y_col = metric_map[metric_option]

    fig_cross = px.scatter(
        cross_df,
        x=x_col,
        y=y_col,
        hover_name="공격수",
        hover_data={
            "공격수포지션": True,
            "공격시도": ":,",
            "공격성공": ":,",
            "공격범실": ":,",
            "블로킹당함": ":,",
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
            "공격성공": "공격 성공",
            "공격범실": "공격 범실",
            "블로킹당함": "블로킹 당함",
        },
    )

    fig_cross.update_traces(
        marker=dict(
            size=14,
            color=selected_team_color,
            line=dict(width=1, color="black"),
        ),
    )

    player_ranges = add_smart_scatter_labels(
        fig=fig_cross,
        data=cross_df,
        x_col=x_col,
        y_col=y_col,
        label_col="공격수",
        font_size=15,
        point_size=14,
    )

    player_x_range = None
    player_y_range = None

    if player_ranges is not None:
        player_x_range, player_y_range = player_ranges

    fig_cross.update_layout(
        height=620,
        margin=dict(l=90, r=120, t=90, b=100),
        font=dict(size=BODY_TEXT_SIZE, color=CHART_TEXT_COLOR),
        xaxis=dict(
            range=player_x_range,
            automargin=True,
            showgrid=False,
            tickfont=dict(size=AXIS_TICK_SIZE, color=CHART_TEXT_COLOR),
            title_font=dict(size=AXIS_TITLE_SIZE, color=CHART_TEXT_COLOR),
        ),
        yaxis=dict(
            range=player_y_range,
            automargin=True,
            showgrid=False,
            tickfont=dict(size=AXIS_TICK_SIZE, color=CHART_TEXT_COLOR),
            title_font=dict(size=AXIS_TITLE_SIZE, color=CHART_TEXT_COLOR),
        ),
    )

    st.plotly_chart(fig_cross, use_container_width=True)

    st.caption(
        "점 옆에 선수 이름을 표시하며, 마우스를 올리면 세부 기록을 확인할 수 있습니다. "
        "공격효율 = (공격성공 - 공격범실 - 블로킹당함) ÷ 공격시도."
    )

else:
    metric_option = st.selectbox(
        "지표 조합",
        [
            "공격성공률 × 공격효율",
            "TOP1 공격집중도 × 팀 공격효율",
            "TOP3 공격집중도 × 팀 공격효율",
            "클러치 공격비중 × 클러치 성공률",
        ],
        key="team_cross_metric",
    )

    # 선택된 시즌과 경기 구분을 모든 팀에 동일하게 적용
    compare_base = season_base.copy()

    if selected_scope == "정규리그":
        compare_base = compare_base[
            compare_base["대회구분"].astype(str) == "정규리그"
        ]

    elif selected_scope == "포스트시즌":
        compare_base = compare_base[
            compare_base["대회구분"].astype(str).isin(postseason_competitions)
        ]

    elif selected_scope in [
        "1라운드",
        "2라운드",
        "3라운드",
        "4라운드",
        "5라운드",
        "6라운드",
    ]:
        compare_base = compare_base[
            (compare_base["대회구분"].astype(str) == "정규리그")
            & (compare_base["경기구분"].astype(str) == selected_scope)
        ]

    elif selected_scope in postseason_competitions:
        compare_base = compare_base[
            compare_base["대회구분"].astype(str) == selected_scope
        ]

    team_compare = (
        compare_base
        .groupby(
            ["시즌코드", "팀코드", "팀"],
            dropna=False
        )
        .agg(
            공격시도=("공격수", "size"),
            공격성공=("공격성공", "sum"),
            공격범실=("공격범실", "sum"),
            블로킹당함=("블로킹당함", "sum"),
        )
        .reset_index()
    )

    team_compare["공격성공률_%"] = (
        team_compare["공격성공"] / team_compare["공격시도"] * 100
    ).round(1)

    team_compare["공격효율_%"] = (
        (
            team_compare["공격성공"]
            - team_compare["공격범실"]
            - team_compare["블로킹당함"]
        )
        / team_compare["공격시도"]
        * 100
    ).round(1)

    # 팀별 선수 공격 점유율 → TOP1/TOP3 집중도
    player_share = (
        compare_base
        .groupby(["팀코드", "팀", "공격수"], dropna=False)
        .size()
        .reset_index(name="공격시도")
    )

    team_total = (
        player_share
        .groupby(["팀코드", "팀"])["공격시도"]
        .sum()
        .rename("팀공격시도")
        .reset_index()
    )

    player_share = player_share.merge(
        team_total,
        on=["팀코드", "팀"],
        how="left",
    )

    player_share["공격점유율_%"] = (
        player_share["공격시도"] / player_share["팀공격시도"] * 100
    )

    concentration_rows = []

    for (team_code, team_name), group in player_share.groupby(["팀코드", "팀"]):
        shares = group["공격점유율_%"].sort_values(ascending=False).tolist()

        concentration_rows.append({
            "팀코드": team_code,
            "팀": team_name,
            "TOP1집중도_%": round(sum(shares[:1]), 1),
            "TOP3집중도_%": round(sum(shares[:3]), 1),
        })

    concentration_df = pd.DataFrame(concentration_rows)

    team_compare = team_compare.merge(
        concentration_df,
        on=["팀코드", "팀"],
        how="left",
    )

    clutch_base = compare_base[
        compare_base["후반3점차이내"] == True
    ].copy()

    clutch_summary = (
        clutch_base
        .groupby(["팀코드", "팀"], dropna=False)
        .agg(
            클러치공격시도=("공격수", "size"),
            클러치공격성공=("공격성공", "sum"),
        )
        .reset_index()
    )

    clutch_summary["클러치성공률_%"] = (
        clutch_summary["클러치공격성공"]
        / clutch_summary["클러치공격시도"]
        * 100
    ).round(1)

    team_compare = team_compare.merge(
        clutch_summary,
        on=["팀코드", "팀"],
        how="left",
    )

    team_compare["클러치공격비중_%"] = (
        team_compare["클러치공격시도"].fillna(0)
        / team_compare["공격시도"]
        * 100
    ).round(1)

    metric_map = {
        "공격성공률 × 공격효율": ("공격성공률_%", "공격효율_%"),
        "TOP1 공격집중도 × 팀 공격효율": ("TOP1집중도_%", "공격효율_%"),
        "TOP3 공격집중도 × 팀 공격효율": ("TOP3집중도_%", "공격효율_%"),
        "클러치 공격비중 × 클러치 성공률": ("클러치공격비중_%", "클러치성공률_%"),
    }

    x_col, y_col = metric_map[metric_option]

    team_compare["팀색상"] = team_compare.apply(
        lambda row: get_team_color(
            row["시즌코드"],
            row["팀코드"]
        ),
        axis=1,
    )

    color_map = dict(
        zip(
            team_compare["팀"],
            team_compare["팀색상"]
        )
    )

    fig_cross = px.scatter(
        team_compare,
        x=x_col,
        y=y_col,
        color="팀",
        color_discrete_map=color_map,
        hover_name="팀",
        hover_data={
            "공격시도": ":,",
            "공격성공률_%": ":.1f",
            "공격효율_%": ":.1f",
            "TOP1집중도_%": ":.1f",
            "TOP3집중도_%": ":.1f",
            "클러치공격비중_%": ":.1f",
            "클러치성공률_%": ":.1f",
        },
        labels={
            "공격성공률_%": "공격 성공률 (%)",
            "공격효율_%": "공격 효율 (%)",
            "TOP1집중도_%": "TOP1 공격 집중도 (%)",
            "TOP3집중도_%": "TOP3 공격 집중도 (%)",
            "클러치공격비중_%": "클러치 공격 비중 (%)",
            "클러치성공률_%": "클러치 공격 성공률 (%)",
            "공격시도": "공격 시도",
        },
    )

    for trace in fig_cross.data:
        trace.update(
            marker=dict(
                size=16,
                line=dict(width=1, color="black"),
            ),
        )

    team_ranges = add_smart_scatter_labels(
        fig=fig_cross,
        data=team_compare,
        x_col=x_col,
        y_col=y_col,
        label_col="팀",
        font_size=16,
        point_size=16,
    )

    team_x_range = None
    team_y_range = None

    if team_ranges is not None:
        team_x_range, team_y_range = team_ranges

    fig_cross.update_layout(
        height=640,
        margin=dict(l=90, r=130, t=90, b=100),
        showlegend=False,
        font=dict(size=BODY_TEXT_SIZE, color=CHART_TEXT_COLOR),
        xaxis=dict(
            range=team_x_range,
            automargin=True,
            showgrid=False,
            tickfont=dict(size=AXIS_TICK_SIZE, color=CHART_TEXT_COLOR),
            title_font=dict(size=AXIS_TITLE_SIZE, color=CHART_TEXT_COLOR),
        ),
        yaxis=dict(
            range=team_y_range,
            automargin=True,
            showgrid=False,
            tickfont=dict(size=AXIS_TICK_SIZE, color=CHART_TEXT_COLOR),
            title_font=dict(size=AXIS_TITLE_SIZE, color=CHART_TEXT_COLOR),
        ),
    )

    st.plotly_chart(fig_cross, use_container_width=True)

    st.caption(
        "팀 비교는 현재 선택한 시즌과 경기 구분을 모든 팀에 동일하게 적용합니다. "
        "포스트시즌 세부 구분을 선택하면 해당 경기에 참가한 팀만 표시됩니다."
    )

