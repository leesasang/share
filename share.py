import time
import uuid
from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text


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

ADMIN_PASSWORD = get_secret("ADMIN_PASSWORD", "1234")

TEAM_CODES = {
    "1팀": get_secret("TEAM1_CODE", "1111"),
    "2팀": get_secret("TEAM2_CODE", "2222"),
    "3팀": get_secret("TEAM3_CODE", "3333"),
}

TEAM_NAMES = ["1팀", "2팀", "3팀"]
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
운영자가 다음 공시로 넘어갈 때마다 고정된 스토리에 따라 주가가 변동됩니다.
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
        "summary": "신제품, 화재, 신곡, 콘솔 출시 등 기업별 개별 이슈 발생",
        "news": """
Codein에서 새로운 메신저 어플 코코오톡을 개발하여 이목을 이끌고 있습니다.

가천전자가 오늘 오전 자사 소유의 반도체 생산 공장에서 화재가 발생했다고 발표했습니다.
이로 인해 재산 손실이 약 5천억 원으로 예상되며, 막대한 손해가 발생할 것이라는 전망입니다.

Gil bio는 연구 성과에 대한 긍정적 기대감이 형성되고 있습니다.

Gasla에서 최근 새로운 자율 주행 자동차를 선보이며 시장의 관심을 받고 있습니다.

Ganoja에서 새로운 패키지 상품을 선보이며 상승하는 듯했으나,
가성비가 부족하다는 의견이 나오고 있습니다.

LGY 엔터 소속 밴드 Blue Sound가 신곡을 발표했습니다.
곡이 나온 지 1주일 만에 음원차트 TOP10 안에 들며 호평을 받고 있고,
이에 따라 전국투어 일정도 공개했습니다.

코텐도에서 새로운 콘솔 기기인 코텐도 스위치를 오늘 출시하였습니다.
""",
        "changes": {
            "LGY 엔터": [20],
            "Codein": [20],
            "가천전자": [-50],
            "Gil bio": [10],
            "Gasla": [20],
            "Ganoja": [10, -20],
            "코텐도": [30],
        },
    },
    2: {
        "title": "2차 공시",
        "summary": "전세계적인 전염병 발발, 여행 제한 및 수출입 차질 발생",
        "news": """
전세계적인 전염병이 발발했습니다.
여행 제한이 시작되었고, 주요 산업의 수출입에도 큰 어려움이 생기고 있습니다.

Codein은 전염병으로 인해 외출을 하지 못하는 사람들이 늘어나며,
온라인 메신저 어플 코코오톡의 사용량이 급증하고 있습니다.
또한 Codein은 코코오톡과 연계되는 코코오페이와 코코오뱅크를 출시하며
온라인 뱅킹 시스템의 편의성을 높여 많은 관심을 받고 있습니다.

가천전자는 전염병 확산으로 인해 반도체 핵심 재료 수입에 어려움을 겪고 있습니다.
현재 운영 중인 반도체 공장 10곳 중 5곳이 가동 중지 직전이라고 발표했습니다.

Gil bio는 전염병 백신 개발에 집중하며 1차 샘플이 나왔다고 발표했습니다.
하지만 1차 샘플의 성능이 무의미하다는 소식이 퍼지며 개발이 다시 원점으로 돌아갔습니다.

Ganoja는 전세계적인 여행 제한으로 큰 타격을 입었습니다.
전문가들에 따르면 손실 규모는 약 300억 원으로 추정됩니다.
전염병 전에 출시한 패키지 상품의 환불 및 취소 문의가 급증한 영향으로 보입니다.

Gasla는 가천전자로부터 공급받던 반도체 물량이 급격히 줄어들며
자동차 생산에 큰 타격이 예상됩니다.
또한 새롭게 출시한 자율주행 자동차가 자율주행 중 인명사고를 내며 큰 이슈가 되고 있습니다.

LGY 엔터 소속 밴드 Blue Sound는 신곡 흥행에도 불구하고
예고했던 전국 투어 일정이 취소되며 팬들의 원성을 사고 있습니다.
하지만 소속사는 예매자 전액 환불과 굿즈 보상을 진행하며
후속처리에 대해 팬들에게 호평을 받고 있습니다.

코텐도는 전염병으로 인해 집에서 보내는 시간이 늘어나며
신제품 코텐도 스위치 주문이 폭주하고 있습니다.
각 매장과 온라인 쇼핑몰에서 품절 대란이 발생하고 있습니다.
""",
        "changes": {
            "LGY 엔터": [-20, 30],
            "Codein": [40],
            "가천전자": [-60],
            "Gil bio": [30, -50],
            "Gasla": [-40],
            "Ganoja": [-30],
            "코텐도": [50],
        },
    },
    3: {
        "title": "3차 공시",
        "summary": "전염병 완화, 여행 제한 해제, 월드컵 개최, AI 반도체 수요 증가",
        "news": """
전염병이 점차 완화되며 여행 제한이 해제되고 있습니다.
또한 예고되어 있던 월드컵 개최와 AI 반도체 수요 증가가 시장의 핵심 이슈로 떠오르고 있습니다.

Codein이 소유하고 있던 성남시 소재 데이터센터에 화재가 발생했습니다.
이로 인해 약 8시간 동안 서비스 장애가 발생하며 큰 이슈가 되었습니다.
또한 이 충격으로 Codein 윤회장의 지병이 악화되어 회장직을 사퇴하였고,
회장 공백으로 투자자들의 불안감이 커지고 있습니다.

가천전자는 미국의 GPU 회사 N사와 반도체 독점계약을 따내며
약 1조 원 규모의 투자를 받은 것으로 전해집니다.
또한 전염병 완화로 반도체 핵심 소재 수입이 정상화되며
생산에 박차를 가할 전망입니다.

Gil bio는 전염병의 핵심 구조를 파악하는 데 성공했고,
백신 개발에도 성공했다고 전해집니다.
이 백신은 실제 효과가 있는 것으로 알려졌으며,
전세계적으로 백신 요청이 이어지고 있습니다.

Ganoja는 전염병 완화와 여행 제한 해제로 인해
사람들이 다시 여행을 떠나기 시작하며 회복세를 보이고 있습니다.
또한 예정되어 있던 월드컵 개최로 여행 수요가 크게 증가할 전망입니다.

Gasla는 지난 사고를 교훈 삼아 새로운 자율주행 AI를 개발했습니다.
이번 AI는 이전의 실수를 반복하지 않도록 안전성에 더욱 신경 쓴 것으로 보입니다.

LGY 엔터 소속 밴드 Blue Sound가 소속사와 재계약 문제로 불화를 겪고 있다는 소식이 전해졌습니다.
또한 밴드 리더 김**은 군입대를 앞두고 있어 팬들의 불안감이 커지고 있습니다.

코텐도는 전염병 완화와 여행 제한 해제로 인해 인기가 줄어들고 있습니다.
전염병이 빠르게 완화될 것을 예측하지 못한 코텐도는
스위치를 과하게 생산해 상당한 손해가 예상됩니다.
""",
        "changes": {
            "LGY 엔터": [-40],
            "Codein": [-80],
            "가천전자": [70],
            "Gil bio": [100],
            "Gasla": [30],
            "Ganoja": [40],
            "코텐도": [-30],
        },
    },
    4: {
        "title": "4차 공시",
        "summary": "반도체 수요 급증, AI 기술 경쟁, 기업별 최종 대형 이슈",
        "news": """
전세계적으로 반도체 수요가 급증하며 반도체 시장이 호황을 맞이했습니다.

Codein은 회장 공백을 이사회를 통해 새롭게 선출된 이** 회장으로 마무리했습니다.
이 회장은 선출 직후 새로운 LLM인 Copt를 선보이며 많은 관심을 끌었습니다.
전문가들은 Copt가 타사의 LLM보다 압도적인 성능을 보인다고 평가했습니다.

가천전자는 전세계적인 반도체 수요 급증으로 큰 호황을 맞이했습니다.
특히 박** 연구원을 필두로 한 연구팀이 새로운 반도체 공정법을 선보이며
전세계의 이목을 받고 있습니다.
전문가들은 가천전자의 이번 수익이 역대 최고치를 갱신할 것이라고 전망합니다.

Gil bio의 전염병 백신에서 알 수 없는 부작용이 발견되었습니다.
현재 이 부작용은 10명 중 3명에게 나타나며, 치사율이 50%에 달한다고 합니다.
이에 따라 Gil bio 대표는 조사를 받고 있고 회사의 불확실성이 커졌습니다.

Ganoja가 한국항공을 인수합병하며 자체 여행 플랫폼과 항공사를 모두 보유한
여행 전문 기업으로 도약했다고 발표했습니다.

Gasla의 대표 나일론 마스크씨가 새로운 회사 스페이스O를 만들었습니다.
스페이스O는 등장과 동시에 엄청난 우주기술을 선보였다고 합니다.
마스크씨는 곧 있을 시험 발사에서 지금까지 보지 못했던 기술을 보여주겠다고 말하며
전문가와 대중의 관심을 끌고 있습니다.

LGY 엔터 소속 밴드 Blue Sound는 결국 소속사와 재계약 합의에 실패했고,
리더 김**의 군입대가 확실해지며 해체되었다고 합니다.
이로 인해 LGY 엔터는 큰 타격을 입을 것으로 보입니다.

코텐도는 코텐도 스위치2를 출시하며 큰 관심을 받고 있습니다.
또한 스위치2 전용 게임인 코드의 전설을 선보이며 게이머들의 기대감을 높였습니다.
전문가들은 코드의 전설이 역대 최고의 명작이 될 수 있다고 평가했습니다.
""",
        "changes": {
            "LGY 엔터": [-50],
            "Codein": [50],
            "가천전자": [200],
            "Gil bio": [-80],
            "Gasla": [50],
            "Ganoja": [20],
            "코텐도": [50],
        },
    },
    5: {
        "title": "보너스 이벤트",
        "summary": "예상치 못한 사고와 우주선 발사 실패",
        "news": """
보너스 이벤트가 발생했습니다.

새로운 반도체 생산 공정을 개발한 박** 연구팀은
Ganoja가 인수한 한국항공의 비행기를 타고 휴가를 가던 중
불의의 사고로 비행기가 추락하며 모두 세상을 떠났다고 발표되었습니다.
이로 인해 가천전자와 Ganoja 모두 큰 손해가 예상됩니다.

또한 Gasla의 대표 나일론 마스크씨가 설립한 우주회사 스페이스O가
오늘 아침 시험 발사에 도전했으나,
발사 10초 만에 우주선이 폭파하며 전문가와 대중의 비판을 받고 있습니다.
전문가들은 이 손해가 Gasla에도 큰 악영향을 줄 것으로 전망합니다.
""",
        "changes": {
            "LGY 엔터": [],
            "Codein": [],
            "가천전자": [-30],
            "Gil bio": [],
            "Gasla": [-60],
            "Ganoja": [-60],
            "코텐도": [],
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
# 5. DB initialization
# =========================================================

def create_tables():
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS game_state (
                id INTEGER PRIMARY KEY,
                current_notice INTEGER NOT NULL
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


def save_price_history(conn, notice_index, stock_name, price):
    exists = conn.execute(
        text("""
            SELECT 1
            FROM price_history
            WHERE notice_index = :notice_index AND stock_name = :stock_name
        """),
        {"notice_index": notice_index, "stock_name": stock_name},
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


def init_db():
    create_tables()
    engine = get_engine()

    with engine.begin() as conn:
        state = conn.execute(text("SELECT current_notice FROM game_state WHERE id = 1")).fetchone()

        if state is None:
            conn.execute(
                text("INSERT INTO game_state (id, current_notice) VALUES (1, 0)")
            )

        for team_name in TEAM_NAMES:
            team = conn.execute(
                text("SELECT 1 FROM teams WHERE team_name = :team_name"),
                {"team_name": team_name},
            ).fetchone()

            if team is None:
                conn.execute(
                    text("""
                        INSERT INTO teams (team_name, cash)
                        VALUES (:team_name, :cash)
                    """),
                    {"team_name": team_name, "cash": INITIAL_CASH},
                )

        for stock_name, info in STOCKS.items():
            stock = conn.execute(
                text("SELECT 1 FROM stocks WHERE stock_name = :stock_name"),
                {"stock_name": stock_name},
            ).fetchone()

            if stock is None:
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

            price_row = conn.execute(
                text("""
                    SELECT 1
                    FROM price_history
                    WHERE notice_index = 0 AND stock_name = :stock_name
                """),
                {"stock_name": stock_name},
            ).fetchone()

            if price_row is None:
                save_price_history(conn, 0, stock_name, info["initial_price"])


# =========================================================
# 6. Calculation helpers
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


def get_current_notice():
    row = fetch_one("SELECT current_notice FROM game_state WHERE id = 1")
    return row["current_notice"] if row else 0


def get_next_notice():
    current = get_current_notice()
    next_notice = current + 1

    if next_notice > FINAL_NOTICE_INDEX:
        return None

    return next_notice


# =========================================================
# 7. Data getters
# =========================================================

def get_stocks_df():
    rows = fetch_all("""
        SELECT stock_name, description, initial_price, current_price
        FROM stocks
    """)

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    order_map = {name: idx for idx, name in enumerate(STOCK_ORDER)}
    df["sort"] = df["stock_name"].map(order_map)
    df = df.sort_values("sort").drop(columns=["sort"])

    return df


def get_price_map():
    df = get_stocks_df()
    return {row["stock_name"]: row["current_price"] for _, row in df.iterrows()}


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
        "SELECT cash FROM teams WHERE team_name = :team_name",
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

    cash = team["cash"] if team else 0
    stock_value = 0

    for item in holdings:
        stock_value += prices[item["stock_name"]] * item["qty"]

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
        qty = row["qty"]
        avg_price = row["avg_price"]
        current_price = prices[stock_name]

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
# 8. Trading
# =========================================================

def buy_stock(team_name, stock_name, qty):
    if get_current_notice() >= FINAL_NOTICE_INDEX:
        return False, "최종 이벤트가 종료되어 더 이상 매수할 수 없습니다."

    if qty <= 0:
        return False, "매수 수량은 1주 이상이어야 합니다."

    engine = get_engine()

    with engine.begin() as conn:
        stock = conn.execute(
            text("SELECT current_price FROM stocks WHERE stock_name = :stock_name"),
            {"stock_name": stock_name},
        ).fetchone()

        team = conn.execute(
            text("SELECT cash FROM teams WHERE team_name = :team_name"),
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
            {"team_name": team_name, "stock_name": stock_name},
        ).fetchone()

        conn.execute(
            text("""
                UPDATE teams
                SET cash = cash - :total_price
                WHERE team_name = :team_name
            """),
            {"total_price": total_price, "team_name": team_name},
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
            {"team_name": team_name, "stock_name": stock_name},
        ).fetchone()

        if holding is None:
            return False, "보유하지 않은 종목입니다."

        owned_qty = int(holding._mapping["qty"])

        if qty > owned_qty:
            return False, "보유 수량보다 많이 매도할 수 없습니다."

        stock = conn.execute(
            text("SELECT current_price FROM stocks WHERE stock_name = :stock_name"),
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
            {"total_price": total_price, "team_name": team_name},
        )

        if remain_qty == 0:
            conn.execute(
                text("""
                    DELETE FROM portfolio
                    WHERE team_name = :team_name AND stock_name = :stock_name
                """),
                {"team_name": team_name, "stock_name": stock_name},
            )
        else:
            conn.execute(
                text("""
                    UPDATE portfolio
                    SET qty = :qty
                    WHERE team_name = :team_name AND stock_name = :stock_name
                """),
                {"qty": remain_qty, "team_name": team_name, "stock_name": stock_name},
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
# 9. Notice progression
# =========================================================

def apply_next_notice():
    current_notice = get_current_notice()
    next_notice = current_notice + 1

    if next_notice > FINAL_NOTICE_INDEX:
        return False, "이미 모든 공시와 이벤트가 종료되었습니다."

    notice = ANNOUNCEMENTS[next_notice]
    changes = notice["changes"]

    engine = get_engine()

    with engine.begin() as conn:
        for stock_name in STOCK_ORDER:
            stock = conn.execute(
                text("SELECT current_price FROM stocks WHERE stock_name = :stock_name"),
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
                {"current_price": new_price, "stock_name": stock_name},
            )

            save_price_history(conn, next_notice, stock_name, new_price)

        conn.execute(
            text("""
                UPDATE game_state
                SET current_notice = :current_notice
                WHERE id = 1
            """),
            {"current_notice": next_notice},
        )

    return True, f"{notice['title']} 적용 완료"


def reset_game():
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM trade_history"))
        conn.execute(text("DELETE FROM portfolio"))
        conn.execute(text("DELETE FROM price_history"))
        conn.execute(text("DELETE FROM stocks"))
        conn.execute(text("DELETE FROM teams"))
        conn.execute(text("DELETE FROM game_state"))

    init_db()


# =========================================================
# 10. UI helpers
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
    current_notice = get_current_notice()
    current_title = ANNOUNCEMENTS[current_notice]["title"]

    if current_notice >= FINAL_NOTICE_INDEX:
        st.markdown(
            f'<div class="status-close">장 마감 · {current_title}</div>',
            unsafe_allow_html=True,
        )
    else:
        next_notice = current_notice + 1
        st.markdown(
            f'<div class="status-open">장 운영중 · 현재 {current_title} · 다음 {ANNOUNCEMENTS[next_notice]["title"]}</div>',
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


def smooth_stock_chart_data(stock_name, steps_per_segment=20):
    chart_df = get_stock_chart_df(stock_name)

    if chart_df.empty or len(chart_df) == 1:
        return chart_df

    points = []

    notices = list(chart_df.index)
    prices = list(chart_df[stock_name])

    for idx in range(len(notices) - 1):
        start_notice = notices[idx]
        end_notice = notices[idx + 1]
        start_price = prices[idx]
        end_price = prices[idx + 1]

        for step in range(steps_per_segment):
            ratio = step / steps_per_segment
            x = start_notice + (end_notice - start_notice) * ratio
            y = start_price + (end_price - start_price) * ratio
            points.append({"공시": x, stock_name: y})

    points.append({"공시": notices[-1], stock_name: prices[-1]})

    smooth_df = pd.DataFrame(points)
    smooth_df = smooth_df.set_index("공시")

    return smooth_df


def render_animated_stock_chart(stock_name):
    smooth_df = smooth_stock_chart_data(stock_name)

    if smooth_df.empty:
        st.info("아직 차트 데이터가 없습니다.")
        return

    placeholder = st.empty()

    for i in range(2, len(smooth_df) + 1):
        placeholder.line_chart(smooth_df.iloc[:i], use_container_width=True)
        time.sleep(0.035)


def render_static_stock_chart(stock_name):
    chart_df = get_stock_chart_df(stock_name)

    if chart_df.empty:
        st.info("아직 차트 데이터가 없습니다.")
    else:
        st.line_chart(chart_df, use_container_width=True)


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
    else:
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
# 11. Pages
# =========================================================

def admin_page(view_mode):
    st.markdown('<div class="section-title">운영자 페이지</div>', unsafe_allow_html=True)

    password = st.text_input("운영자 비밀번호", type="password")

    if password != ADMIN_PASSWORD:
        st.warning("운영자 비밀번호를 입력하세요.")
        return

    current_notice = get_current_notice()
    render_status()

    st.divider()

    if view_mode == "모바일":
        card("현재 공시", ANNOUNCEMENTS[current_notice]["title"], ANNOUNCEMENTS[current_notice]["summary"])

        next_notice = get_next_notice()
        if next_notice is not None:
            card("다음 공시", ANNOUNCEMENTS[next_notice]["title"], ANNOUNCEMENTS[next_notice]["summary"])
        else:
            card("다음 공시", "없음", "모든 공시가 종료되었습니다.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            card("현재 공시", ANNOUNCEMENTS[current_notice]["title"], ANNOUNCEMENTS[current_notice]["summary"])

        with col2:
            next_notice = get_next_notice()
            if next_notice is not None:
                card("다음 공시", ANNOUNCEMENTS[next_notice]["title"], ANNOUNCEMENTS[next_notice]["summary"])
            else:
                card("다음 공시", "없음", "모든 공시가 종료되었습니다.")

    next_notice = get_next_notice()

    st.markdown('<div class="section-title">다음 공시 미리보기</div>', unsafe_allow_html=True)

    if next_notice is None:
        st.success("모든 공시와 보너스 이벤트가 종료되었습니다.")
    else:
        render_notice_box(next_notice, "다음 공시")
        render_change_table(next_notice)

        if st.button("다음 공시로 넘어가기", use_container_width=True):
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

    st.markdown('<div class="section-title">종목별 개별 차트</div>', unsafe_allow_html=True)
    st.caption("아래 종목 버튼을 누르면 해당 종목의 차트가 천천히 변화하는 방식으로 표시됩니다.")

    if view_mode == "모바일":
        for stock_name in STOCK_ORDER:
            if st.button(stock_name, key=f"admin_chart_{stock_name}", use_container_width=True):
                render_animated_stock_chart(stock_name)
    else:
        cols = st.columns(4)

        clicked_stock = None

        for idx, stock_name in enumerate(STOCK_ORDER):
            with cols[idx % 4]:
                if st.button(stock_name, key=f"admin_chart_{stock_name}", use_container_width=True):
                    clicked_stock = stock_name

        if clicked_stock:
            render_animated_stock_chart(clicked_stock)
        else:
            st.info("차트를 보고 싶은 종목을 선택하세요.")

    st.divider()

    with st.expander("전체 주가 차트 보기"):
        render_all_chart()

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
                        {"team_name": team_name, "stock_name": stock_name},
                    )

                    owned_qty = holding["qty"]
                    price = prices[stock_name]

                    qty = st.number_input(
                        "매도 수량",
                        min_value=1,
                        max_value=int(owned_qty),
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
# 12. Sidebar and main
# =========================================================

def render_sidebar():
    st.sidebar.markdown("## 📌 메뉴")

    role = st.sidebar.radio(
        "접속 페이지",
        ["운영자", "1팀", "2팀", "3팀"],
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
    else:
        team_page(role, view_mode)


if __name__ == "__main__":
    main()
