# 시즌별 팀 시각화 설정
# 팀명은 데이터의 시즌별 팀명을 그대로 사용하고,
# 색상만 시즌코드 + 팀코드 기준으로 관리합니다.
# 새 시즌을 추가할 때 해당 시즌의 팀 색만 이 파일에 추가하면 됩니다.

DEFAULT_TEAM_COLOR = "#4C6EF5"

TEAM_COLOR_BY_SEASON_CODE = {
    "022": {  # 2025-26
        "2001": "#F5B335",  # 현대건설 힐스테이트
        "2002": "#174A7E",  # 한국도로공사 하이패스
        "2003": "#C8102E",  # 정관장 레드스파크스
        "2004": "#E6007E",  # 흥국생명 핑크스파이더스
        "2005": "#00A19A",  # GS칼텍스 서울KIXX - 제이드그린 계열
        "2006": "#005BAC",  # IBK기업은행 알토스
        "2007": "#E61E4D",  # 페퍼저축은행 AI PEPPERS
    },
}


def get_team_color(season_code, team_code):
    season_code = str(season_code)
    team_code = str(team_code)

    return TEAM_COLOR_BY_SEASON_CODE.get(
        season_code,
        {}
    ).get(
        team_code,
        DEFAULT_TEAM_COLOR
    )
