import uuid
from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, inspect, text


# =========================================================
# 0. Page config
# =========================================================

st.set_page_config(
    page_title="MT 모의주식 거래소",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# 1. Basic config
# =========================================================

def get_secret(key, default=None):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


DATABASE_URL = get_secret("DATABASE_URL", "sqlite:///mt_stock_game.db")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


GAME_VERSION = "dopamine_stock_game_final_v1"

ADMIN_PASSWORD = get_secret("ADMIN_PASSWORD", "102938")

TEAM_NAMES = ["1팀", "2팀", "3팀"]

TEAM_CODES = {
    "1팀": get_secret("TEAM1_CODE", "1111"),
    "2팀": get_secret("TEAM2_CODE", "2222"),
    "3팀": get_secret("TEAM3_CODE", "3333"),
}

INITIAL_CASH = 500_000

STOCKS = {
    "LGY 엔터": {
        "description": "엔터테이먼트 회사",
        "initial_price": 70_000,
    },
    "Codein": {
        "description": "IT그룹",
        "initial_price": 100_000,
    },
    "가천전자": {
        "description": "반도체 전문 그룹",
        "initial_price": 150_000,
    },
    "Gil bio": {
        "description": "제약 전문 기업",
        "initial_price": 100_000,
    },
    "Gasla": {
        "description": "전기 자동차 전문 기업",
        "initial_price": 50_000,
    },
    "Ganoja": {
        "description": "여행 전문 기업",
        "initial_price": 30_000,
    },
    "코텐도": {
        "description": "게임 개발 및 게임기 개발 회사",
        "initial_price": 50_000,
    },
}

STOCK_ORDER = list(STOCKS.keys())


# =========================================================
# 2. Fixed announcement story
# =========================================================

ANNOUNCEMENTS = {
    0: {
        "title": "0차 공시 - 게임 시작",
        "summary": "모든 기업의 시작가가 공개되었습니다.",
        "news": """
모의주식 거래소가 개장되었습니다.

각 팀은 시작 자금 500,000원을 바탕으로 7개 기업의 주식을 자유롭게 매수/매도할 수 있습니다.

현재 시장은 큰 이슈 없이 안정적으로 출발하고 있습니다.
다만 각 기업은 서로 다른 산업에 속해 있기 때문에, 앞으로 공개될 공시에 따라 주가 흐름이 크게 달라질 수 있습니다.
""",
        "changes": {
            "LGY 엔터": [],
            "Codein": [],
            "가천전자": [],
            "Gil bio": [],
            "Gasla": [],
            "Ganoja": [],
            "코텐도": [],
        },
    },
    1: {
        "title": "1차 공시",
        "summary": "첫 번째 성장 모멘텀과 개별 악재",
        "news": """
본격적인 시장 변화가 시작되었습니다.

여러 기업이 신제품과 새로운 사업을 발표하며 투자자들의 관심을 받고 있습니다.
다만 일부 기업에서는 예상치 못한 사고와 소비자 반응 악화가 발생하며, 기업별로 주가 흐름이 갈리고 있습니다.

Codein에서 새로운 메신저 어플 코코오톡을 공개했습니다.
출시 초기부터 빠른 가입자 증가세를 보이며, 기존 메신저 시장을 흔들 수 있다는 평가가 나오고 있습니다.

가천전자가 보유한 반도체 생산 공장에서 화재가 발생했습니다.
핵심 생산 라인 일부가 중단되며 단기 생산 차질이 불가피해졌습니다.

Gil bio가 차세대 감염병 대응 연구에서 의미 있는 초기 성과를 냈다고 발표했습니다.

Gasla가 새로운 자율주행 전기차 모델을 공개했습니다.
기존 모델보다 주행 보조 기능이 강화되었고, 배터리 효율 면에서도 좋은 평가를 받고 있습니다.

Ganoja가 새로운 여행 패키지 상품을 공개했습니다.
출시 직후에는 관심을 받았지만, 이후 가격 대비 구성이 아쉽다는 평가가 나오며 상승분 일부를 반납했습니다.

LGY 엔터 소속 밴드 Blue Sound가 신곡을 발표했습니다.
발매 1주일 만에 음원차트 TOP10에 진입했고, 전국투어 일정까지 공개되며 기대감이 커지고 있습니다.

코텐도가 새로운 콘솔 기기 코텐도 스위치를 출시했습니다.
휴대성과 독점 게임 라인업이 좋은 평가를 받으며 안정적인 성장세를 보이고 있습니다.
""",
        "changes": {
            "LGY 엔터": [25],
            "Codein": [25],
            "가천전자": [-50],
            "Gil bio": [15],
            "Gasla": [20],
            "Ganoja": [15, -10],
            "코텐도": [20],
        },
    },
    2: {
        "title": "2차 공시",
        "summary": "전염병 발발과 산업별 명암",
        "news": """
전세계적인 전염병이 확산되며 경제 전반에 큰 변화가 나타나고 있습니다.

외출 제한, 여행 제한, 물류 차질이 발생하면서 오프라인 산업과 제조업은 타격을 받고 있습니다.
반면 온라인 서비스, 게임, 일부 바이오 산업은 새로운 기회를 맞이하고 있습니다.

Codein은 전염병 확산으로 사람들이 집에 머무는 시간이 늘어나며 코코오톡 사용량이 급증했습니다.
Codein은 코코오톡과 연계되는 코코오페이와 코코오뱅크를 출시하며 온라인 금융 서비스까지 확장했습니다.

가천전자는 반도체 핵심 소재 수입 차질을 겪고 있습니다.
1차 공시의 화재 피해가 완전히 복구되지 않은 상황에서 추가 악재가 겹치며 주가는 큰 폭으로 하락했습니다.

Gil bio는 전염병 백신 개발에 착수했고, 1차 샘플을 공개했습니다.
초기에는 빠른 개발 속도에 대한 기대감으로 주가가 올랐지만, 이후 예방 효과가 기대보다 낮다는 평가가 나오며 상승분 일부를 반납했습니다.

Gasla는 가천전자로부터 공급받던 반도체 물량이 줄어들며 생산 차질을 겪고 있습니다.
여기에 자율주행 기능 안전성 논란까지 발생하며 소비자 신뢰가 흔들리고 있습니다.

Ganoja는 여행 제한으로 큰 타격을 받았습니다.
기존 예약 상품의 환불 요청이 급증했고, 신규 패키지 판매도 사실상 중단되었습니다.

LGY 엔터는 Blue Sound의 전국투어가 취소되며 공연 매출 손실이 예상되었습니다.
하지만 예매자 전액 환불, 한정 굿즈 보상, 온라인 라이브 공연 전환을 빠르게 발표하며 팬들의 반응이 긍정적으로 돌아섰습니다.

코텐도는 집에서 보내는 시간이 늘어나며 코텐도 스위치의 수요가 꾸준히 증가했습니다.
회사는 무리한 생산 확대보다 안정적인 공급 확대를 선택하며 완만한 상승세를 이어갑니다.
""",
        "changes": {
            "LGY 엔터": [-25, 15],
            "Codein": [35],
            "가천전자": [-60],
            "Gil bio": [40, -25],
            "Gasla": [-30],
            "Ganoja": [-35],
            "코텐도": [15],
        },
    },
    3: {
        "title": "3차 공시",
        "summary": "전염병 완화와 시장 반전",
        "news": """
전염병 상황이 점차 완화되며 경제가 회복 국면에 들어서고 있습니다.

여행 제한이 풀리고, 월드컵 개최가 확정되며 소비 심리가 살아나고 있습니다.
동시에 AI 산업과 반도체 수요가 빠르게 증가하면서 일부 기업에는 새로운 성장 기회가 열리고 있습니다.

Codein이 운영하던 성남 데이터센터에서 화재가 발생했습니다.
약 8시간 동안 코코오톡, 코코오페이, 코코오뱅크 서비스 장애가 발생하며 이용자들의 불만이 커졌습니다.
또한 윤회장이 건강 문제로 회장직을 사퇴하며 경영 공백 우려가 제기되었습니다.

가천전자는 미국 GPU 기업 N사와 반도체 공급 계약을 체결했습니다.
AI 반도체 수요 증가와 핵심 소재 수입 정상화로 생산 회복 기대감이 커지고 있습니다.
2차 공시에서 30,000원까지 떨어졌던 가천전자는 이번 공시를 계기로 강한 반등에 성공했습니다.

Gil bio가 전염병의 핵심 구조를 분석하는 데 성공하고, 개선된 백신 개발에 성공했다고 발표했습니다.
여러 국가에서 긴급 공급 요청이 이어지고 있습니다.

Ganoja는 여행 제한 해제로 예약량이 빠르게 회복되고 있습니다.
월드컵 개최까지 확정되며 해외 여행과 단체 패키지 수요가 급증했습니다.

Gasla는 지난 자율주행 사고 이후 안전성 개선에 집중했습니다.
새롭게 공개한 자율주행 AI는 사고 방지 알고리즘과 긴급 제어 기능이 강화되었습니다.

LGY 엔터 소속 밴드 Blue Sound가 소속사와 재계약 문제로 갈등을 겪고 있다는 소식이 전해졌습니다.
또한 밴드 리더 김**의 군입대 가능성이 커지며 팬덤 내 불안감이 확산되고 있습니다.

코텐도는 전염병 완화 이후에도 독점 게임 라인업과 충성 고객층을 기반으로 안정적인 판매량을 유지하고 있습니다.
폭발적인 상승은 아니지만 안정성이 부각되며 주가는 소폭 상승했습니다.
""",
        "changes": {
            "LGY 엔터": [-25],
            "Codein": [-45],
            "가천전자": [200],
            "Gil bio": [80],
            "Gasla": [35],
            "Ganoja": [50],
            "코텐도": [10],
        },
    },
    4: {
        "title": "4차 공시",
        "summary": "AI, 반도체, 신제품 경쟁",
        "news": """
세계 경제는 본격적인 회복 국면에 들어섰습니다.

특히 AI 기술, 반도체, 신제품 경쟁이 시장의 중심이 되고 있습니다.
기업마다 위기를 극복한 곳과 새로운 위기에 직면한 곳이 뚜렷하게 갈리고 있습니다.

Codein은 회장 공백을 이사회를 통해 새롭게 선출된 이** 회장으로 마무리했습니다.
이 회장은 취임 직후 새로운 LLM 서비스 Copt를 공개했습니다.
Copt는 코코오톡과 연동되는 기능으로 관심을 받았지만, 아직 수익 모델과 안정성 검증이 충분하지 않다는 평가도 함께 나오고 있습니다.

가천전자는 전세계적인 AI 반도체 수요 급증으로 큰 수혜를 받고 있습니다.
박** 연구원을 중심으로 한 연구팀이 새로운 반도체 공정법을 개발했다고 발표했습니다.
이 공정법은 생산 효율을 크게 높이고 불량률을 낮출 수 있는 기술로 평가받고 있습니다.
시장에서는 가천전자가 이번 호황의 최대 수혜 기업 중 하나가 될 것으로 보고 있으며, 주가는 최고가인 약 270,000원까지 상승했습니다.

Gil bio의 백신 접종자 일부에게서 심각한 부작용이 나타났다는 소식이 전해졌습니다.
아직 부작용이 백신 자체 때문인지 명확히 밝혀지지는 않았지만, 여론은 빠르게 악화되고 있습니다.

Ganoja가 한국항공을 인수합병했다고 발표했습니다.
이를 통해 Ganoja는 여행 플랫폼뿐만 아니라 항공 운송까지 직접 보유한 종합 여행 기업으로 도약하게 되었습니다.

Gasla의 대표 나일론 마스크씨가 우주기업 스페이스O를 설립했습니다.
스페이스O는 새로운 발사체 기술을 공개하며 큰 관심을 받고 있습니다.

Blue Sound는 결국 소속사와 재계약 합의에 실패했습니다.
리더 김**의 군입대까지 확정되며 팀 활동은 장기간 중단될 가능성이 커졌습니다.

코텐도가 코텐도 스위치2를 공개했습니다.
기기 성능이 향상되었고, 독점 게임 코드의 전설이 전문가와 게이머 모두에게 좋은 평가를 받고 있습니다.
""",
        "changes": {
            "LGY 엔터": [-35],
            "Codein": [30],
            "가천전자": [200],
            "Gil bio": [-50],
            "Gasla": [45],
            "Ganoja": [30],
            "코텐도": [20],
        },
    },
    5: {
        "title": "보너스 이벤트",
        "summary": "마지막 변수 발생",
        "news": """
예상치 못한 보너스 이벤트가 발생했습니다.

새로운 반도체 생산 공정을 개발한 박** 연구팀은 Ganoja가 인수한 한국항공의 비행기를 타고 휴가를 가던 중,
불의의 사고로 비행기가 추락하며 모두 세상을 떠났다고 발표되었습니다.
이로 인해 가천전자와 Ganoja 모두 큰 타격을 받을 것이라는 전망입니다.

또한 Gasla의 대표 나일론 마스크씨의 우주회사 스페이스O가 시험 발사에 도전했습니다.
하지만 발사 도중 스페이스O의 우주선이 발사 10초 만에 하늘에서 폭파하며, 많은 전문가와 대중의 비판을 받고 있습니다.

한편 Gil bio는 백신 부작용 논란에 대해 공식 해명을 발표했습니다.
조사 결과, 문제가 된 사례 대부분은 기존 지병을 가진 접종자였고,
Gil bio는 해당 위험성을 사전에 고지했던 것으로 확인되었습니다.
전문가들도 Gil bio의 주장이 사실일 가능성이 높다고 평가하며, Gil bio는 억울했던 누명을 벗는 분위기가 형성되었습니다.

Codein의 Copt는 여러 기업과 학교에서 업무 보조 AI로 도입되기 시작했습니다.
대형 폭등은 아니지만, 안정적인 AI 서비스 매출이 기대되며 추가 상승했습니다.

LGY 엔터는 Blue Sound 해체 이후 빠르게 후속 프로젝트를 발표했습니다.
기존 멤버 일부가 참여한 추모 앨범과 신인 밴드 프로젝트가 공개되며 팬덤의 반응이 예상보다 좋게 나타났습니다.

코텐도 스위치2와 코드의 전설은 출시 직후 좋은 판매 흐름을 보이고 있습니다.
코텐도는 마지막까지 꾸준한 상승세를 유지합니다.
""",
        "changes": {
            "LGY 엔터": [20],
            "Codein": [15],
            "가천전자": [-20],
            "Gil bio": [60],
            "Gasla": [-45],
            "Ganoja": [-50],
            "코텐도": [15],
        },
    },
}

FINAL_NOTICE_INDEX = max(ANNOUNCEMENTS.keys())


# =========================================================
# 3. Styling
# =========================================================

def inject_css(view_mode):
    st.markdown(
        """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        header[data-testid="stHeader"] {
            background: rgba(0, 0, 0, 0);
        }

        .stApp {
            background: linear-gradient(180deg, #0b1220 0%, #0f172a 55%, #020617 100%);
            color: #e5e7eb;
        }

        .block-container {
            max-width: 1450px;
            padding-top: 3.2rem !important;
            padding-bottom: 3rem !important;
        }

        [data-testid="stSidebar"] {
            background: #020617;
            border-right: 1px solid #1e293b;
        }

        h1, h2, h3, h4, h5, h6, p, span, div, label {
            color: #e5e7eb;
        }

        .app-title {
            font-size: 2.25rem;
            font-weight: 900;
            color: #f8fafc;
            margin-bottom: 0.3rem;
            letter-spacing: -0.04em;
        }

        .app-subtitle {
            color: #94a3b8;
            font-size: 0.98rem;
            margin-bottom: 1rem;
        }

        .section-title {
            font-size: 1.18rem;
            font-weight: 900;
            color: #f8fafc;
            margin: 12px 0 12px 0;
        }

        .status-open {
            display: inline-block;
            background: rgba(34, 197, 94, 0.13);
            border: 1px solid rgba(34, 197, 94, 0.32);
            color: #86efac;
            padding: 7px 12px;
            border-radius: 999px;
            font-size: 0.85rem;
            font-weight: 800;
            margin-bottom: 14px;
        }

        .status-close {
            display: inline-block;
            background: rgba(239, 68, 68, 0.13);
            border: 1px solid rgba(239, 68, 68, 0.32);
            color: #fecaca;
            padding: 7px 12px;
            border-radius: 999px;
            font-size: 0.85rem;
            font-weight: 800;
            margin-bottom: 14px;
        }

        .card {
            background: linear-gradient(135deg, rgba(30,41,59,0.95), rgba(15,23,42,0.95));
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 18px;
            padding: 18px 20px;
            box-shadow: 0 10px 24px rgba(0,0,0,0.22);
            margin-bottom: 12px;
        }

        .metric-label {
            color: #94a3b8;
            font-size: 0.85rem;
            margin-bottom: 7px;
        }

        .metric-value {
            color: #f8fafc;
            font-size: 1.55rem;
            font-weight: 900;
            letter-spacing: -0.03em;
        }

        .metric-sub {
            color: #cbd5e1;
            font-size: 0.80rem;
            margin-top: 5px;
        }

        .news-box {
            background: rgba(250, 204, 21, 0.08);
            border: 1px solid rgba(250, 204, 21, 0.22);
            border-radius: 18px;
            padding: 18px 20px;
            margin-bottom: 14px;
        }

        .news-title {
            font-size: 1.1rem;
            font-weight: 900;
            color: #fde68a;
            margin-bottom: 8px;
        }

        .news-body {
            color: #fef3c7;
            white-space: pre-wrap;
            line-height: 1.65;
        }

        .up { color: #ef4444; font-weight: 900; }
        .down { color: #3b82f6; font-weight: 900; }
        .same { color: #cbd5e1; font-weight: 900; }

        .stButton > button,
        div[data-testid="stFormSubmitButton"] button,
        button[kind="primary"],
        button[kind="secondary"],
        button[kind="formSubmit"] {
            border-radius: 12px !important;
            font-weight: 800 !important;
            min-height: 42px !important;
            background-color: #1e293b !important;
            color: #f8fafc !important;
            -webkit-text-fill-color: #f8fafc !important;
            border: 1px solid #475569 !important;
            box-shadow: 0 6px 14px rgba(0, 0, 0, 0.20) !important;
        }

        .stButton > button:hover,
        div[data-testid="stFormSubmitButton"] button:hover,
        button[kind="primary"]:hover,
        button[kind="secondary"]:hover,
        button[kind="formSubmit"]:hover {
            background-color: #334155 !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            border: 1px solid #64748b !important;
        }

        .stTextInput input,
        .stNumberInput input,
        .stTextArea textarea {
            background: #0f172a !important;
            color: #f8fafc !important;
            -webkit-text-fill-color: #f8fafc !important;
            border: 1px solid #334155 !important;
            border-radius: 10px !important;
        }

        div[data-baseweb="select"] > div {
            background-color: #0f172a !important;
            border: 1px solid #334155 !important;
            border-radius: 10px !important;
            color: #f8fafc !important;
            -webkit-text-fill-color: #f8fafc !important;
        }

        div[data-baseweb="select"] *,
        [data-baseweb="popover"] * {
            color: #f8fafc !important;
            -webkit-text-fill-color: #f8fafc !important;
        }

        div[data-baseweb="select"] svg {
            fill: #f8fafc !important;
            color: #f8fafc !important;
        }

        [data-baseweb="popover"],
        ul[role="listbox"],
        div[role="listbox"],
        li[role="option"],
        div[role="option"] {
            background-color: #0f172a !important;
            border-color: #334155 !important;
        }

        li[role="option"]:hover,
        div[role="option"]:hover,
        li[role="option"]:hover *,
        div[role="option"]:hover * {
            background-color: #1e293b !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }

        [data-testid="stDataFrame"] {
            border-radius: 14px;
            overflow: hidden;
        }

        button[data-baseweb="tab"] {
            font-weight: 800;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if view_mode == "모바일":
        st.markdown(
            """
            <style>
            .block-container {
                max-width: 100% !important;
                padding-left: 0.75rem !important;
                padding-right: 0.75rem !important;
                padding-top: 2rem !important;
            }

            .app-title {
                font-size: 1.55rem !important;
                line-height: 1.25 !important;
            }

            .app-subtitle {
                font-size: 0.85rem !important;
                line-height: 1.5 !important;
            }

            .section-title {
                font-size: 1.05rem !important;
                margin-top: 12px !important;
            }

            .card {
                padding: 14px 15px !important;
                border-radius: 15px !important;
            }

            .metric-value {
                font-size: 1.25rem !important;
            }

            .metric-label {
                font-size: 0.78rem !important;
            }

            .metric-sub {
                font-size: 0.73rem !important;
            }

            .news-box {
                padding: 14px 15px !important;
            }

            .news-title {
                font-size: 0.98rem !important;
            }

            .news-body {
                font-size: 0.85rem !important;
                line-height: 1.55 !important;
            }

            .stButton > button,
            div[data-testid="stFormSubmitButton"] button {
                min-height: 50px !important;
                font-size: 1rem !important;
                width: 100% !important;
            }

            .stTextInput input,
            .stNumberInput input,
            .stTextArea textarea {
                min-height: 44px !important;
                font-size: 1rem !important;
            }

            div[data-baseweb="select"] > div {
                min-height: 44px !important;
            }

            button[data-baseweb="tab"] {
                font-size: 0.82rem !important;
                padding-left: 5px !important;
                padding-right: 5px !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )


# =========================================================
# 4. DB engine
# =========================================================

@st.cache_resource
def get_engine():
    if DATABASE_URL.startswith("sqlite"):
        return create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            future=True,
        )

    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        future=True,
    )


def fetch_all(sql, params=None):
    engine = get_engine()

    with engine.begin() as conn:
        result = conn.execute(text(sql), params or {})
        return [dict(row._mapping) for row in result.fetchall()]


def fetch_one(sql, params=None):
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


# =========================================================
# 5. Utility
# =========================================================

def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def money(value):
    return f"{int(round(value)):,}원"


def percent_text(value):
    return f"{value:+.2f}%"


def percent_class(value):
    if value > 0:
        return "up"
    if value < 0:
        return "down"
    return "same"


def normalize_changes(changes):
    if changes is None:
        return []

    if isinstance(changes, list):
        return changes

    return [changes]


def apply_change_sequence(price, changes):
    result = float(price)

    for rate in normalize_changes(changes):
        result = result * (1 + rate / 100)

    return int(round(result))


def format_changes(changes):
    changes = normalize_changes(changes)

    if not changes:
        return "변동 없음"

    return " → ".join([f"{rate:+g}%" for rate in changes])


# =========================================================
# 6. DB initialization
# =========================================================

def create_tables():
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS game_state (
                id INTEGER PRIMARY KEY,
                current_notice INTEGER NOT NULL,
                trading_open INTEGER NOT NULL DEFAULT 1,
                schema_version TEXT NOT NULL DEFAULT ''
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS teams (
                team_name TEXT PRIMARY KEY,
                cash INTEGER NOT NULL
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS stocks (
                stock_name TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                initial_price INTEGER NOT NULL,
                current_price INTEGER NOT NULL
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS portfolio (
                team_name TEXT NOT NULL,
                stock_name TEXT NOT NULL,
                qty INTEGER NOT NULL,
                avg_price REAL NOT NULL,
                PRIMARY KEY (team_name, stock_name)
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS trade_history (
                id TEXT PRIMARY KEY,
                team_name TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                stock_name TEXT NOT NULL,
                qty INTEGER NOT NULL,
                price INTEGER NOT NULL,
                total_price INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS price_history (
                notice_index INTEGER NOT NULL,
                stock_name TEXT NOT NULL,
                price INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (notice_index, stock_name)
            )
        """))


def add_missing_columns():
    engine = get_engine()
    inspector = inspect(engine)

    try:
        columns = [col["name"] for col in inspector.get_columns("game_state")]
    except Exception:
        return

    if "trading_open" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE game_state ADD COLUMN trading_open INTEGER NOT NULL DEFAULT 1"))

    if "schema_version" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE game_state ADD COLUMN schema_version TEXT NOT NULL DEFAULT ''"))


def clear_all_data(conn):
    conn.execute(text("DELETE FROM trade_history"))
    conn.execute(text("DELETE FROM portfolio"))
    conn.execute(text("DELETE FROM price_history"))
    conn.execute(text("DELETE FROM stocks"))
    conn.execute(text("DELETE FROM teams"))
    conn.execute(text("DELETE FROM game_state"))


def save_price_history(conn, notice_index, stock_name, price):
    exists = conn.execute(
        text("""
            SELECT 1
            FROM price_history
            WHERE notice_index = :notice_index AND stock_name = :stock_name
        """),
        {
            "notice_index": notice_index,
            "stock_name": stock_name,
        },
    ).fetchone()

    if exists:
        conn.execute(
            text("""
                UPDATE price_history
                SET price = :price, created_at = :created_at
                WHERE notice_index = :notice_index AND stock_name = :stock_name
            """),
            {
                "price": price,
                "created_at": now_text(),
                "notice_index": notice_index,
                "stock_name": stock_name,
            },
        )
    else:
        conn.execute(
            text("""
                INSERT INTO price_history
                (notice_index, stock_name, price, created_at)
                VALUES (:notice_index, :stock_name, :price, :created_at)
            """),
            {
                "notice_index": notice_index,
                "stock_name": stock_name,
                "price": price,
                "created_at": now_text(),
            },
        )


def seed_game(conn):
    conn.execute(
        text("""
            INSERT INTO game_state
            (id, current_notice, trading_open, schema_version)
            VALUES (1, 0, 1, :schema_version)
        """),
        {"schema_version": GAME_VERSION},
    )

    for team_name in TEAM_NAMES:
        conn.execute(
            text("""
                INSERT INTO teams (team_name, cash)
                VALUES (:team_name, :cash)
            """),
            {
                "team_name": team_name,
                "cash": INITIAL_CASH,
            },
        )

    for stock_name, info in STOCKS.items():
        conn.execute(
            text("""
                INSERT INTO stocks
                (stock_name, description, initial_price, current_price)
                VALUES (:stock_name, :description, :initial_price, :current_price)
            """),
            {
                "stock_name": stock_name,
                "description": info["description"],
                "initial_price": info["initial_price"],
                "current_price": info["initial_price"],
            },
        )

        save_price_history(conn, 0, stock_name, info["initial_price"])


def init_db():
    create_tables()
    add_missing_columns()

    engine = get_engine()

    with engine.begin() as conn:
        state = conn.execute(
            text("""
                SELECT current_notice, trading_open, schema_version
                FROM game_state
                WHERE id = 1
            """)
        ).fetchone()

        if state is None:
            seed_game(conn)
            return

        current_version = state._mapping.get("schema_version", "")

        if current_version != GAME_VERSION:
            clear_all_data(conn)
            seed_game(conn)


# =========================================================
# 7. State getters
# =========================================================

def get_game_state():
    row = fetch_one("""
        SELECT current_notice, trading_open, schema_version
        FROM game_state
        WHERE id = 1
    """)

    if not row:
        return {
            "current_notice": 0,
            "trading_open": True,
            "schema_version": GAME_VERSION,
        }

    return {
        "current_notice": int(row["current_notice"]),
        "trading_open": bool(int(row["trading_open"])),
        "schema_version": row.get("schema_version", ""),
    }


def get_current_notice():
    return get_game_state()["current_notice"]


def is_trading_open():
    return get_game_state()["trading_open"]


def get_next_notice():
    current = get_current_notice()
    next_notice = current + 1

    if next_notice > FINAL_NOTICE_INDEX:
        return None

    return next_notice


def set_trading_open(open_value):
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE game_state
                SET trading_open = :trading_open
                WHERE id = 1
            """),
            {"trading_open": 1 if open_value else 0},
        )


# =========================================================
# 8. Data getters
# =========================================================

def get_stocks_df():
    rows = fetch_all("""
        SELECT stock_name, description, initial_price, current_price
        FROM stocks
    """)

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df = df[df["stock_name"].isin(STOCK_ORDER)].copy()

    order_map = {name: idx for idx, name in enumerate(STOCK_ORDER)}
    df["sort"] = df["stock_name"].map(order_map)
    df = df.sort_values("sort").drop(columns=["sort"])

    return df


def get_price_map():
    df = get_stocks_df()

    if df.empty:
        return {
            stock_name: info["initial_price"]
            for stock_name, info in STOCKS.items()
        }

    return {
        row["stock_name"]: int(row["current_price"])
        for _, row in df.iterrows()
    }


def get_price_history_df(stock_name=None):
    if stock_name:
        rows = fetch_all(
            """
            SELECT notice_index, stock_name, price
            FROM price_history
            WHERE stock_name = :stock_name
            ORDER BY notice_index ASC
            """,
            {"stock_name": stock_name},
        )
    else:
        rows = fetch_all("""
            SELECT notice_index, stock_name, price
            FROM price_history
            ORDER BY notice_index ASC
        """)

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def get_all_chart_df():
    df = get_price_history_df()

    if df.empty:
        return pd.DataFrame()

    chart_df = df.pivot(
        index="notice_index",
        columns="stock_name",
        values="price",
    )

    chart_df = chart_df.reindex(columns=STOCK_ORDER)
    chart_df = chart_df.sort_index()
    chart_df.index.name = "공시"

    return chart_df


def get_stock_chart_df(stock_name):
    df = get_price_history_df(stock_name)

    if df.empty:
        return pd.DataFrame()

    chart_df = df[["notice_index", "price"]].copy()
    chart_df = chart_df.sort_values("notice_index")
    chart_df = chart_df.set_index("notice_index")
    chart_df.index.name = "공시"
    chart_df = chart_df.rename(columns={"price": stock_name})

    return chart_df


def get_team_asset(team_name):
    prices = get_price_map()

    team = fetch_one(
        """
        SELECT cash
        FROM teams
        WHERE team_name = :team_name
        """,
        {"team_name": team_name},
    )

    holdings = fetch_all(
        """
        SELECT stock_name, qty
        FROM portfolio
        WHERE team_name = :team_name
        """,
        {"team_name": team_name},
    )

    cash = int(team["cash"]) if team else 0
    stock_value = 0

    for item in holdings:
        stock_name = item["stock_name"]
        qty = int(item["qty"])
        stock_value += int(prices[stock_name]) * qty

    total_asset = cash + stock_value
    profit = total_asset - INITIAL_CASH
    profit_rate = (profit / INITIAL_CASH) * 100

    return {
        "cash": cash,
        "stock_value": stock_value,
        "total_asset": total_asset,
        "profit": profit,
        "profit_rate": profit_rate,
    }


def get_ranking_df():
    rows = []

    for team_name in TEAM_NAMES:
        asset = get_team_asset(team_name)

        rows.append({
            "팀": team_name,
            "현금": money(asset["cash"]),
            "주식 평가액": money(asset["stock_value"]),
            "총 자산": money(asset["total_asset"]),
            "손익": money(asset["profit"]),
            "수익률": percent_text(asset["profit_rate"]),
            "_rate": asset["profit_rate"],
        })

    df = pd.DataFrame(rows)
    df = df.sort_values("_rate", ascending=False).reset_index(drop=True)
    df.insert(0, "순위", df.index + 1)
    df = df.drop(columns=["_rate"])

    return df


def get_portfolio_df(team_name):
    prices = get_price_map()

    rows = fetch_all(
        """
        SELECT stock_name, qty, avg_price
        FROM portfolio
        WHERE team_name = :team_name
        """,
        {"team_name": team_name},
    )

    if not rows:
        return pd.DataFrame()

    result = []

    for row in rows:
        stock_name = row["stock_name"]
        qty = int(row["qty"])
        avg_price = float(row["avg_price"])
        current_price = int(prices[stock_name])

        buy_amount = avg_price * qty
        current_amount = current_price * qty
        profit = current_amount - buy_amount
        profit_rate = 0 if buy_amount == 0 else (profit / buy_amount) * 100

        result.append({
            "종목": stock_name,
            "보유 수량": qty,
            "평균 매수가": money(avg_price),
            "현재가": money(current_price),
            "매수 금액": money(buy_amount),
            "평가 금액": money(current_amount),
            "손익": money(profit),
            "수익률": percent_text(profit_rate),
        })

    df = pd.DataFrame(result)

    order_map = {name: idx for idx, name in enumerate(STOCK_ORDER)}
    df["sort"] = df["종목"].map(order_map)
    df = df.sort_values("sort").drop(columns=["sort"])

    return df


def get_trade_history_df(team_name=None):
    if team_name:
        rows = fetch_all(
            """
            SELECT team_name, trade_type, stock_name, qty, price, total_price, created_at
            FROM trade_history
            WHERE team_name = :team_name
            ORDER BY created_at DESC
            """,
            {"team_name": team_name},
        )
    else:
        rows = fetch_all("""
            SELECT team_name, trade_type, stock_name, qty, price, total_price, created_at
            FROM trade_history
            ORDER BY created_at DESC
        """)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    df = df.rename(columns={
        "team_name": "팀",
        "trade_type": "구분",
        "stock_name": "종목",
        "qty": "수량",
        "price": "가격",
        "total_price": "총액",
        "created_at": "거래 시각",
    })

    df["가격"] = df["가격"].apply(money)
    df["총액"] = df["총액"].apply(money)

    return df


# =========================================================
# 9. Trading
# =========================================================

def buy_stock(team_name, stock_name, qty):
    if get_current_notice() >= FINAL_NOTICE_INDEX:
        return False, "최종 이벤트가 종료되어 더 이상 매수할 수 없습니다."

    if not is_trading_open():
        return False, "현재 거래가 마감되어 있습니다. 운영자가 거래를 열어야 매수할 수 있습니다."

    if qty <= 0:
        return False, "매수 수량은 1주 이상이어야 합니다."

    engine = get_engine()

    with engine.begin() as conn:
        stock = conn.execute(
            text("""
                SELECT current_price
                FROM stocks
                WHERE stock_name = :stock_name
            """),
            {"stock_name": stock_name},
        ).fetchone()

        team = conn.execute(
            text("""
                SELECT cash
                FROM teams
                WHERE team_name = :team_name
            """),
            {"team_name": team_name},
        ).fetchone()

        if stock is None or team is None:
            return False, "팀 또는 종목 정보가 없습니다."

        price = int(stock._mapping["current_price"])
        cash = int(team._mapping["cash"])
        total_price = price * qty

        if cash < total_price:
            return False, "보유 현금이 부족합니다."

        holding = conn.execute(
            text("""
                SELECT qty, avg_price
                FROM portfolio
                WHERE team_name = :team_name AND stock_name = :stock_name
            """),
            {
                "team_name": team_name,
                "stock_name": stock_name,
            },
        ).fetchone()

        conn.execute(
            text("""
                UPDATE teams
                SET cash = cash - :total_price
                WHERE team_name = :team_name
            """),
            {
                "total_price": total_price,
                "team_name": team_name,
            },
        )

        if holding:
            old_qty = int(holding._mapping["qty"])
            old_avg = float(holding._mapping["avg_price"])

            new_qty = old_qty + qty
            new_avg = ((old_qty * old_avg) + (qty * price)) / new_qty

            conn.execute(
                text("""
                    UPDATE portfolio
                    SET qty = :qty, avg_price = :avg_price
                    WHERE team_name = :team_name AND stock_name = :stock_name
                """),
                {
                    "qty": new_qty,
                    "avg_price": new_avg,
                    "team_name": team_name,
                    "stock_name": stock_name,
                },
            )
        else:
            conn.execute(
                text("""
                    INSERT INTO portfolio
                    (team_name, stock_name, qty, avg_price)
                    VALUES (:team_name, :stock_name, :qty, :avg_price)
                """),
                {
                    "team_name": team_name,
                    "stock_name": stock_name,
                    "qty": qty,
                    "avg_price": price,
                },
            )

        conn.execute(
            text("""
                INSERT INTO trade_history
                (id, team_name, trade_type, stock_name, qty, price, total_price, created_at)
                VALUES (:id, :team_name, :trade_type, :stock_name, :qty, :price, :total_price, :created_at)
            """),
            {
                "id": str(uuid.uuid4()),
                "team_name": team_name,
                "trade_type": "매수",
                "stock_name": stock_name,
                "qty": qty,
                "price": price,
                "total_price": total_price,
                "created_at": now_text(),
            },
        )

    return True, f"{stock_name} {qty}주 매수 완료"


def sell_stock(team_name, stock_name, qty):
    if get_current_notice() >= FINAL_NOTICE_INDEX:
        return False, "최종 이벤트가 종료되어 더 이상 매도할 수 없습니다."

    if not is_trading_open():
        return False, "현재 거래가 마감되어 있습니다. 운영자가 거래를 열어야 매도할 수 있습니다."

    if qty <= 0:
        return False, "매도 수량은 1주 이상이어야 합니다."

    engine = get_engine()

    with engine.begin() as conn:
        holding = conn.execute(
            text("""
                SELECT qty
                FROM portfolio
                WHERE team_name = :team_name AND stock_name = :stock_name
            """),
            {
                "team_name": team_name,
                "stock_name": stock_name,
            },
        ).fetchone()

        if holding is None:
            return False, "보유하지 않은 종목입니다."

        owned_qty = int(holding._mapping["qty"])

        if qty > owned_qty:
            return False, "보유 수량보다 많이 매도할 수 없습니다."

        stock = conn.execute(
            text("""
                SELECT current_price
                FROM stocks
                WHERE stock_name = :stock_name
            """),
            {"stock_name": stock_name},
        ).fetchone()

        price = int(stock._mapping["current_price"])
        total_price = price * qty
        remain_qty = owned_qty - qty

        conn.execute(
            text("""
                UPDATE teams
                SET cash = cash + :total_price
                WHERE team_name = :team_name
            """),
            {
                "total_price": total_price,
                "team_name": team_name,
            },
        )

        if remain_qty == 0:
            conn.execute(
                text("""
                    DELETE FROM portfolio
                    WHERE team_name = :team_name AND stock_name = :stock_name
                """),
                {
                    "team_name": team_name,
                    "stock_name": stock_name,
                },
            )
        else:
            conn.execute(
                text("""
                    UPDATE portfolio
                    SET qty = :qty
                    WHERE team_name = :team_name AND stock_name = :stock_name
                """),
                {
                    "qty": remain_qty,
                    "team_name": team_name,
                    "stock_name": stock_name,
                },
            )

        conn.execute(
            text("""
                INSERT INTO trade_history
                (id, team_name, trade_type, stock_name, qty, price, total_price, created_at)
                VALUES (:id, :team_name, :trade_type, :stock_name, :qty, :price, :total_price, :created_at)
            """),
            {
                "id": str(uuid.uuid4()),
                "team_name": team_name,
                "trade_type": "매도",
                "stock_name": stock_name,
                "qty": qty,
                "price": price,
                "total_price": total_price,
                "created_at": now_text(),
            },
        )

    return True, f"{stock_name} {qty}주 매도 완료"


# =========================================================
# 10. Notice progression
# =========================================================

def apply_next_notice():
    current_notice = get_current_notice()
    next_notice = current_notice + 1

    if next_notice > FINAL_NOTICE_INDEX:
        return False, "이미 모든 공시와 이벤트가 종료되었습니다."

    if is_trading_open():
        return False, "공시 적용 전 거래를 먼저 마감하세요."

    notice = ANNOUNCEMENTS[next_notice]
    changes = notice["changes"]

    engine = get_engine()

    with engine.begin() as conn:
        for stock_name in STOCK_ORDER:
            stock = conn.execute(
                text("""
                    SELECT current_price
                    FROM stocks
                    WHERE stock_name = :stock_name
                """),
                {"stock_name": stock_name},
            ).fetchone()

            current_price = int(stock._mapping["current_price"])
            new_price = apply_change_sequence(current_price, changes.get(stock_name, []))

            conn.execute(
                text("""
                    UPDATE stocks
                    SET current_price = :current_price
                    WHERE stock_name = :stock_name
                """),
                {
                    "current_price": new_price,
                    "stock_name": stock_name,
                },
            )

            save_price_history(conn, next_notice, stock_name, new_price)

        conn.execute(
            text("""
                UPDATE game_state
                SET current_notice = :current_notice,
                    trading_open = 0
                WHERE id = 1
            """),
            {"current_notice": next_notice},
        )

    return True, f"{notice['title']} 적용 완료"


def reset_game():
    engine = get_engine()

    with engine.begin() as conn:
        clear_all_data(conn)
        seed_game(conn)


# =========================================================
# 11. UI helpers
# =========================================================

def card(label, value, sub=""):
    st.markdown(
        f"""
        <div class="card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    st.markdown(
        """
        <div class="app-title">📈 MT 모의주식 거래소</div>
        <div class="app-subtitle">
        고정된 공시 스토리에 따라 주가가 변동되는 팀 대항 모의주식 레크레이션 게임입니다.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status():
    state = get_game_state()

    current_notice = state["current_notice"]
    trading_open = state["trading_open"]
    current_title = ANNOUNCEMENTS[current_notice]["title"]

    if current_notice >= FINAL_NOTICE_INDEX:
        st.markdown(
            f'<div class="status-close">장 마감 · {current_title}</div>',
            unsafe_allow_html=True,
        )
        return

    trading_text = "거래 가능" if trading_open else "거래 마감"
    trading_class = "status-open" if trading_open else "status-close"

    next_notice = current_notice + 1

    st.markdown(
        f'<div class="{trading_class}">현재 {current_title} · 다음 {ANNOUNCEMENTS[next_notice]["title"]} · {trading_text}</div>',
        unsafe_allow_html=True,
    )


def render_notice_box(notice_index, title_prefix="현재 공시"):
    notice = ANNOUNCEMENTS[notice_index]

    st.markdown(
        f"""
        <div class="news-box">
            <div class="news-title">{title_prefix}: {notice["title"]}</div>
            <div class="news-body">{notice["news"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_change_table(notice_index):
    notice = ANNOUNCEMENTS[notice_index]
    rows = []

    for stock_name in STOCK_ORDER:
        rows.append({
            "종목": stock_name,
            "변화율": format_changes(notice["changes"].get(stock_name, [])),
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_all_chart():
    chart_df = get_all_chart_df()

    if chart_df.empty:
        st.info("아직 차트 데이터가 없습니다.")
        return

    st.line_chart(chart_df, use_container_width=True)


def render_static_stock_chart(stock_name):
    chart_df = get_stock_chart_df(stock_name)

    if chart_df.empty:
        st.info("아직 차트 데이터가 없습니다.")
    else:
        st.line_chart(chart_df, use_container_width=True)


def render_stock_cards(view_mode):
    stocks_df = get_stocks_df()

    if stocks_df.empty:
        st.info("종목 데이터가 없습니다.")
        return

    if view_mode == "모바일":
        for _, row in stocks_df.iterrows():
            stock_name = row["stock_name"]
            initial_price = int(row["initial_price"])
            current_price = int(row["current_price"])
            change_rate = ((current_price - initial_price) / initial_price) * 100
            cls = percent_class(change_rate)

            st.markdown(
                f"""
                <div class="card">
                    <div class="metric-label">{stock_name}</div>
                    <div class="metric-value">{money(current_price)}</div>
                    <div class="metric-sub">{row["description"]} · 시작가 대비 <span class="{cls}">{percent_text(change_rate)}</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        return

    cols = st.columns(4)

    for idx, row in stocks_df.iterrows():
        stock_name = row["stock_name"]
        initial_price = int(row["initial_price"])
        current_price = int(row["current_price"])
        change_rate = ((current_price - initial_price) / initial_price) * 100
        cls = percent_class(change_rate)

        with cols[idx % 4]:
            st.markdown(
                f"""
                <div class="card">
                    <div class="metric-label">{stock_name}</div>
                    <div class="metric-value">{money(current_price)}</div>
                    <div class="metric-sub">{row["description"]} · 시작가 대비 <span class="{cls}">{percent_text(change_rate)}</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_team_summary(team_name, view_mode):
    asset = get_team_asset(team_name)

    if view_mode == "모바일":
        card("보유 현금", money(asset["cash"]), "현재 사용 가능한 현금")
        card("주식 평가액", money(asset["stock_value"]), "현재가 기준 보유 주식 가치")
        card("총 자산", money(asset["total_asset"]), "현금 + 주식 평가액")

        cls = percent_class(asset["profit_rate"])
        st.markdown(
            f"""
            <div class="card">
                <div class="metric-label">내 팀 수익률</div>
                <div class="metric-value {cls}">{percent_text(asset["profit_rate"])}</div>
                <div class="metric-sub">손익 {money(asset["profit"])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        card("보유 현금", money(asset["cash"]), "현재 사용 가능한 현금")

    with col2:
        card("주식 평가액", money(asset["stock_value"]), "현재가 기준 보유 주식 가치")

    with col3:
        card("총 자산", money(asset["total_asset"]), "현금 + 주식 평가액")

    with col4:
        cls = percent_class(asset["profit_rate"])
        st.markdown(
            f"""
            <div class="card">
                <div class="metric-label">내 팀 수익률</div>
                <div class="metric-value {cls}">{percent_text(asset["profit_rate"])}</div>
                <div class="metric-sub">손익 {money(asset["profit"])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# =========================================================
# 12. Pages
# =========================================================

def admin_page(view_mode):
    st.markdown('<div class="section-title">운영자 페이지</div>', unsafe_allow_html=True)

    password = st.text_input("운영자 비밀번호", type="password")

    if password != ADMIN_PASSWORD:
        st.warning("운영자 비밀번호를 입력하세요.")
        return

    render_status()

    state = get_game_state()
    current_notice = state["current_notice"]
    trading_open = state["trading_open"]
    next_notice = get_next_notice()

    st.divider()

    if view_mode == "모바일":
        card("현재 공시", ANNOUNCEMENTS[current_notice]["title"], ANNOUNCEMENTS[current_notice]["summary"])
        card("거래 상태", "거래 가능" if trading_open else "거래 마감", "운영자가 직접 열고 닫을 수 있습니다.")

        if next_notice is None:
            card("다음 공시", "없음", "모든 공시가 종료되었습니다.")
        else:
            card("다음 공시", ANNOUNCEMENTS[next_notice]["title"], ANNOUNCEMENTS[next_notice]["summary"])
    else:
        c1, c2, c3 = st.columns(3)

        with c1:
            card("현재 공시", ANNOUNCEMENTS[current_notice]["title"], ANNOUNCEMENTS[current_notice]["summary"])

        with c2:
            card("거래 상태", "거래 가능" if trading_open else "거래 마감", "운영자가 직접 열고 닫을 수 있습니다.")

        with c3:
            if next_notice is None:
                card("다음 공시", "없음", "모든 공시가 종료되었습니다.")
            else:
                card("다음 공시", ANNOUNCEMENTS[next_notice]["title"], ANNOUNCEMENTS[next_notice]["summary"])

    st.markdown('<div class="section-title">거래 제어</div>', unsafe_allow_html=True)

    control_col1, control_col2 = st.columns(2)

    with control_col1:
        if st.button("거래 열기", use_container_width=True, disabled=trading_open or current_notice >= FINAL_NOTICE_INDEX):
            set_trading_open(True)
            st.success("거래가 열렸습니다.")
            st.rerun()

    with control_col2:
        if st.button("거래 마감", use_container_width=True, disabled=not trading_open):
            set_trading_open(False)
            st.success("거래가 마감되었습니다.")
            st.rerun()

    st.divider()

    st.markdown('<div class="section-title">다음 공시 미리보기</div>', unsafe_allow_html=True)

    if next_notice is None:
        st.success("모든 공시와 보너스 이벤트가 종료되었습니다.")
    else:
        render_notice_box(next_notice, "다음 공시")
        render_change_table(next_notice)

        apply_disabled = trading_open

        if trading_open:
            st.warning("공시를 적용하려면 먼저 거래를 마감하세요.")

        if st.button("다음 공시로 넘어가기", use_container_width=True, disabled=apply_disabled):
            success, message = apply_next_notice()

            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    st.divider()

    st.markdown('<div class="section-title">팀별 수익률 순위표</div>', unsafe_allow_html=True)
    st.dataframe(get_ranking_df(), use_container_width=True, hide_index=True)

    st.divider()

    with st.expander("전체 거래 기록 보기"):
        trade_df = get_trade_history_df()

        if trade_df.empty:
            st.info("거래 기록이 없습니다.")
        else:
            st.dataframe(trade_df, use_container_width=True, hide_index=True)

    with st.expander("게임 초기화"):
        st.warning("초기화하면 팀 현금, 포트폴리오, 거래내역, 주가 기록이 모두 초기화됩니다.")

        reset_text = st.text_input("초기화하려면 '초기화'라고 입력하세요.")

        if st.button("게임 초기화", use_container_width=True):
            if reset_text == "초기화":
                reset_game()
                st.success("게임이 초기화되었습니다.")
                st.rerun()
            else:
                st.error("'초기화'라고 정확히 입력해야 합니다.")


def spectator_page(view_mode):
    render_status()

    st.markdown('<div class="section-title">관전자 페이지</div>', unsafe_allow_html=True)

    current_notice = get_current_notice()
    next_notice = get_next_notice()

    if view_mode == "모바일":
        card("현재 공시", ANNOUNCEMENTS[current_notice]["title"], ANNOUNCEMENTS[current_notice]["summary"])

        if next_notice is None:
            card("다음 공시", "없음", "모든 공시가 종료되었습니다.")
        else:
            card("다음 공시", ANNOUNCEMENTS[next_notice]["title"], ANNOUNCEMENTS[next_notice]["summary"])
    else:
        c1, c2 = st.columns(2)

        with c1:
            card("현재 공시", ANNOUNCEMENTS[current_notice]["title"], ANNOUNCEMENTS[current_notice]["summary"])

        with c2:
            if next_notice is None:
                card("다음 공시", "없음", "모든 공시가 종료되었습니다.")
            else:
                card("다음 공시", ANNOUNCEMENTS[next_notice]["title"], ANNOUNCEMENTS[next_notice]["summary"])

    st.divider()

    tab_dashboard, tab_all, tab_single, tab_rank = st.tabs([
        "대시보드",
        "전체 종목 차트",
        "종목별 상세 차트",
        "팀 순위",
    ])

    with tab_dashboard:
        st.markdown('<div class="section-title">현재 종목 현황</div>', unsafe_allow_html=True)
        render_stock_cards(view_mode)

        st.markdown('<div class="section-title">현재 팀 순위</div>', unsafe_allow_html=True)
        st.dataframe(get_ranking_df(), use_container_width=True, hide_index=True)

    with tab_all:
        st.markdown('<div class="section-title">전체 종목 주가 흐름</div>', unsafe_allow_html=True)
        st.caption("모든 종목의 공시별 가격 변화를 한 번에 확인할 수 있습니다.")
        render_all_chart()

        st.markdown('<div class="section-title">공시별 변화율</div>', unsafe_allow_html=True)
        render_change_table(current_notice)

    with tab_single:
        st.markdown('<div class="section-title">종목별 상세 차트</div>', unsafe_allow_html=True)

        selected_stock = st.selectbox(
            "종목 선택",
            STOCK_ORDER,
            key="spectator_stock_select",
        )

        stocks_df = get_stocks_df()
        selected_info = stocks_df[stocks_df["stock_name"] == selected_stock]

        if not selected_info.empty:
            row = selected_info.iloc[0]

            initial_price = int(row["initial_price"])
            current_price = int(row["current_price"])
            change_rate = ((current_price - initial_price) / initial_price) * 100
            cls = percent_class(change_rate)

            if view_mode == "모바일":
                card("기업명", selected_stock, row["description"])
                card("시작가", money(initial_price), "게임 시작 기준 가격")

                st.markdown(
                    f"""
                    <div class="card">
                        <div class="metric-label">현재가</div>
                        <div class="metric-value">{money(current_price)}</div>
                        <div class="metric-sub">시작가 대비 <span class="{cls}">{percent_text(change_rate)}</span></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                c1, c2, c3 = st.columns(3)

                with c1:
                    card("기업명", selected_stock, row["description"])

                with c2:
                    card("시작가", money(initial_price), "게임 시작 기준 가격")

                with c3:
                    st.markdown(
                        f"""
                        <div class="card">
                            <div class="metric-label">현재가</div>
                            <div class="metric-value">{money(current_price)}</div>
                            <div class="metric-sub">시작가 대비 <span class="{cls}">{percent_text(change_rate)}</span></div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        st.markdown('<div class="section-title">개별 주가 차트</div>', unsafe_allow_html=True)
        render_static_stock_chart(selected_stock)

        st.markdown('<div class="section-title">공시별 가격 기록</div>', unsafe_allow_html=True)

        history_df = get_price_history_df(selected_stock)

        if history_df.empty:
            st.info("가격 기록이 없습니다.")
        else:
            history_df = history_df.rename(columns={
                "notice_index": "공시",
                "stock_name": "종목",
                "price": "가격",
            })

            history_df["공시"] = history_df["공시"].apply(lambda x: f"{x}차 공시")
            history_df["가격"] = history_df["가격"].apply(money)

            st.dataframe(history_df, use_container_width=True, hide_index=True)

    with tab_rank:
        st.markdown('<div class="section-title">현재 팀 순위</div>', unsafe_allow_html=True)
        st.dataframe(get_ranking_df(), use_container_width=True, hide_index=True)


def team_page(team_name, view_mode):
    st.markdown(f'<div class="section-title">{team_name} 페이지</div>', unsafe_allow_html=True)

    team_code = st.text_input(f"{team_name} 팀 코드 입력", type="password")

    if TEAM_CODES[team_name] != team_code:
        st.warning("팀 코드를 입력하면 거래 화면이 열립니다.")
        return

    render_status()

    st.divider()

    st.markdown('<div class="section-title">전체 종목 주가 그래프</div>', unsafe_allow_html=True)
    render_all_chart()

    st.divider()

    current_notice = get_current_notice()
    render_notice_box(current_notice, "현재 공시")

    st.divider()

    st.markdown('<div class="section-title">현재 종목 가격</div>', unsafe_allow_html=True)

    stocks_df = get_stocks_df()

    if stocks_df.empty:
        st.info("종목 데이터가 없습니다.")
    else:
        display_stock_df = stocks_df.rename(columns={
            "stock_name": "종목",
            "description": "기업 설명",
            "initial_price": "시작가",
            "current_price": "현재가",
        })

        display_stock_df["시작가"] = display_stock_df["시작가"].apply(money)
        display_stock_df["현재가"] = display_stock_df["현재가"].apply(money)

        st.dataframe(display_stock_df, use_container_width=True, hide_index=True)

    st.divider()

    st.markdown('<div class="section-title">매수 / 매도</div>', unsafe_allow_html=True)

    if get_current_notice() >= FINAL_NOTICE_INDEX:
        st.error("최종 이벤트가 종료되어 더 이상 거래할 수 없습니다.")
    elif not is_trading_open():
        st.warning("현재 거래가 마감되어 있습니다. 운영자가 거래를 열면 매수/매도가 가능합니다.")
    else:
        prices = get_price_map()

        if view_mode == "모바일":
            buy_area = st.container()
            sell_area = st.container()
        else:
            buy_area, sell_area = st.columns(2)

        with buy_area:
            st.markdown("### 매수")

            with st.form(f"buy_form_{team_name}"):
                stock_name = st.selectbox("매수 종목", STOCK_ORDER, key=f"buy_stock_{team_name}")
                qty = st.number_input("매수 수량", min_value=1, step=1, key=f"buy_qty_{team_name}")

                price = prices[stock_name]
                total_price = price * qty

                st.write(f"현재가: **{money(price)}**")
                st.write(f"예상 매수 금액: **{money(total_price)}**")

                submitted = st.form_submit_button("매수하기", use_container_width=True)

                if submitted:
                    success, message = buy_stock(team_name, stock_name, int(qty))

                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

        with sell_area:
            st.markdown("### 매도")

            portfolio_df = get_portfolio_df(team_name)

            if portfolio_df.empty:
                st.info("보유 중인 주식이 없습니다.")
            else:
                owned_stocks = portfolio_df["종목"].tolist()

                with st.form(f"sell_form_{team_name}"):
                    stock_name = st.selectbox("매도 종목", owned_stocks, key=f"sell_stock_{team_name}")

                    holding = fetch_one(
                        """
                        SELECT qty
                        FROM portfolio
                        WHERE team_name = :team_name AND stock_name = :stock_name
                        """,
                        {
                            "team_name": team_name,
                            "stock_name": stock_name,
                        },
                    )

                    owned_qty = int(holding["qty"])
                    price = prices[stock_name]

                    qty = st.number_input(
                        "매도 수량",
                        min_value=1,
                        max_value=owned_qty,
                        step=1,
                        key=f"sell_qty_{team_name}",
                    )

                    total_price = price * qty

                    st.write(f"보유 수량: **{owned_qty}주**")
                    st.write(f"현재가: **{money(price)}**")
                    st.write(f"예상 매도 금액: **{money(total_price)}**")

                    submitted = st.form_submit_button("매도하기", use_container_width=True)

                    if submitted:
                        success, message = sell_stock(team_name, stock_name, int(qty))

                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

    st.divider()

    st.markdown('<div class="section-title">내 포트폴리오</div>', unsafe_allow_html=True)

    portfolio_df = get_portfolio_df(team_name)

    if portfolio_df.empty:
        st.info("아직 보유 중인 주식이 없습니다.")
    else:
        st.dataframe(portfolio_df, use_container_width=True, hide_index=True)

    st.divider()

    st.markdown('<div class="section-title">내 거래 내역</div>', unsafe_allow_html=True)

    trade_df = get_trade_history_df(team_name)

    if trade_df.empty:
        st.info("아직 거래 내역이 없습니다.")
    else:
        st.dataframe(trade_df, use_container_width=True, hide_index=True)

    st.divider()

    st.markdown('<div class="section-title">내 팀 수익률</div>', unsafe_allow_html=True)
    render_team_summary(team_name, view_mode)


# =========================================================
# 13. Sidebar and main
# =========================================================

def render_sidebar():
    st.sidebar.markdown("## 📌 메뉴")

    role = st.sidebar.radio(
        "접속 페이지",
        ["운영자", "관전자", "1팀", "2팀", "3팀"],
    )

    view_mode = st.sidebar.radio(
        "화면 모드",
        ["PC", "모바일"],
        help="노트북은 PC, 휴대폰은 모바일을 추천합니다.",
    )

    st.sidebar.divider()

    if st.sidebar.button("새로고침", use_container_width=True):
        st.rerun()

    return role, view_mode


def main():
    role, view_mode = render_sidebar()

    inject_css(view_mode)
    init_db()
    render_header()

    if role == "운영자":
        admin_page(view_mode)
    elif role == "관전자":
        spectator_page(view_mode)
    else:
        team_page(role, view_mode)


if __name__ == "__main__":
    main()
