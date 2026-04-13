import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import re
from src.validator import DataValidator
from src.occupancy_engine import OccupancyEngine
from src.transformer import DataTransformer
from src.forecast_engine import ForecastEngine, ForecastParams
from datetime import datetime, date, timedelta # [Fix] Explicit import

st.set_page_config(page_title="공장 점유 현황 시뮬레이터", layout="wide", initial_sidebar_state="collapsed")

# --- 상단 타이틀 및 업데이트 로그 (작고 눈에 띄지 않게) ---
t_col1, t_col_guide, t_col_log = st.columns([0.76, 0.12, 0.12], vertical_alignment="bottom")
with t_col1:
    st.markdown("<h1 style='margin-bottom: 0;'>🏭 공장 점유율 현황 시스템</h1>", unsafe_allow_html=True)
with t_col_guide:
    with st.popover("📖 주요 기능 안내", help="프로그램 주요 기능 요약 확인"):
        st.markdown("""<div style='font-size: 0.9rem; color: #333;'>
<h4 style='margin-top:0; color:#007bff;'>🚀 시스템 주요 기능 안내</h4>
<p>본 시스템은 생산관리일정표의 수주 납기 및 소요 면적 데이터를 기반으로 <b>공장 면적 점유율을 분석·시뮬레이션 및 예측</b>하여 최적의 생산 스케줄링을 지원하는 종합 대시보드입니다.</p>

<h5 style='margin-bottom:5px;'>1. 📊 공장 점유율 현황 (메인 대시보드)</h5>
<ul style='margin-top:0; padding-left:20px; font-size: 0.85rem;'>
    <li><b>자동화된 데이터 전처리:</b> 복잡한 일정표 데이터를 자동으로 정제하고 동급(1동~5동)별 실사용 면적 점유율을 계산합니다.</li>
    <li><b>직관적인 데이터 시각화:</b> 설정된 임계치(예: 80%)에 따라 색상이 동적으로 변하는 히트맵과 라인/바 차트를 제공합니다.</li>
    <li><b>초과 수용 리스크 관리:</b> 과부하가 예상되는 위험 구간을 식별하고, 공장별 점유 동향 및 피크 시점을 요약 보고합니다.</li>
</ul>

<h5 style='margin-bottom:5px;'>2. 🧪 조건 설정 시뮬레이션 (What-If 분석)</h5>
<ul style='margin-top:0; padding-left:20px; font-size: 0.85rem;'>
    <li><b>가상 수주 투입:</b> 향후 예상되는 대형 수주나 긴급 신규 오더를 가상으로 시스템에 투입해 볼 수 있습니다.</li>
    <li><b>영향도 확인:</b> 오더 투입 전(기준선)과 투입 후의 점유율 변화량(Delta)을 전용 히트맵을 통해 한눈에 비교 분석해 줍니다.</li>
</ul>

<h5 style='margin-bottom:5px;'>3. 🔮 AI 점유율 예측 (수요 및 포화도 예측)</h5>
<ul style='margin-top:0; padding-left:20px; font-size: 0.85rem;'>
    <li><b>정밀 알고리즘 최적화:</b> 선형 회귀(Linear Regression), 이동 평균(MA), 통계/시계열(ARIMA) 모델을 복합 적용해 향후 최대 1년(52주)간의 점유율 추세를 투사합니다.</li>
    <li><b>사전 대응 알림:</b> 공장 캐파(Capacity)를 초과할 위험이 있는 예상 기간(연속 초과 일수) 등을 지능적으로 탐지하여 사전 대응을 돕습니다.</li>
</ul>

<h5 style='margin-bottom:5px;'>4. 🗂️ 구역별 드릴다운 추적 (현미경 뷰)</h5>
<ul style='margin-top:0; padding-left:20px; font-size: 0.85rem;'>
    <li><b>양방향 인터랙티브 분석:</b> 전체 현황 히트맵에서 문제가 의심되는 특정 날짜와 생산 동을 클릭하면, 즉시 역추적하여 해당 시점에 가동 중인 전체 상세 오더 리스트(순번, 면적, 수량 등)를 보여줍니다.</li>
</ul>
</div>""", unsafe_allow_html=True)
with t_col_log:
    with st.popover("📜 업데이트 로그", help="시스템 업데이트 기록 확인"):
        st.markdown("""
            <div style='font-size: 0.85rem; color: #555;'>
                <div style='display: flex; align-items: baseline; gap: 8px; margin-bottom: 8px;'>
                    <span style='font-weight: 700; color: #000; font-size: 0.95rem;'>📜 시스템 업데이트 로그</span>
                    <span style='color: #888; font-size: 0.8rem;'>made by Seokgi.Kim</span>
                </div>
                <hr style='margin: 8px 0;'>
                <p><strong>v1.2.2 (2026-04-10)</strong></p>
                <ul style='padding-left: 20px; margin-top: 4px;'>
                    <li>🔄 실험실 탭(비동기 히트맵) 클릭-상세내역 드릴다운 완벽 연동</li>
                    <li>🎨 테스트 탭의 히트맵 레이아웃 및 디자인을 핵심 메인 탭과 완벽 동일하게 렌더링하도록 개선</li>
                </ul>
                <p><strong>v1.2.1 (2026-04-01)</strong></p>
                <ul style='padding-left: 20px; margin-top: 4px;'>
                    <li>🏷️ 상세 내역(드릴다운)에 '면적' 컬럼 추가 및 정수형 표기 보정</li>
                    <li>🎨 테스트 탭의 히트맵 색상을 설정 임계치 기반 동적 알고리즘으로 메인탭과 동일하게 변경</li>
                    <li>📖 메인 화면 주요 기능 요약 가이드 추가</li>
                </ul>
                <p><strong>v1.2.0 (2026-04-01)</strong></p>
                <ul style='padding-left: 20px; margin-top: 4px;'>
                    <li>🔄 화면 드릴다운 동기화 오류 완전 수정 (히트맵 클릭 시 상세내역 갱신)</li>
                    <li>🔨 상세 내역 조회 시 발생하는 직렬화 오류(ArrowTypeError) 해결</li>
                </ul>
                <p><strong>v1.1.0 (2026-03-31)</strong></p>
                <ul style='padding-left: 20px; margin-top: 4px;'>
                    <li>🚩 포화 임계치(%) 가변 분석 엔진 연동</li>
                    <li>📊 리스크 히스토리 및 종합 리포트 동적 업데이트</li>
                    <li>🎨 UI/UX 고도화 (슬라이더 폭 조정, 제목 가시성 개선)</li>
                    <li>🐛 데이터 정렬 및 KeyError 오류 수정</li>
                    <li>🚀 실시간 클라우드 배포 최적화</li>
                </ul>
                <p><strong>v1.0.0 (2026-03-31)</strong></p>
                <ul style='padding-left: 20px; margin-top: 4px;'>
                    <li>🚀 시스템 초기 릴리즈</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)

# --- 데이터 로드 함수 ---
# --- 데이터 로드 함수 ---
def load_data(file):
    if file is None:
        return None
    try:
        # 파일 포인터 초기화 (재시도 시 필수)
        file.seek(0)
        
        # 파일 시그니처(Magic Bytes) 확인
        header = file.read(8)
        file.seek(0)
        
        is_zip = header.startswith(b'PK')
        is_ole = header.startswith(b'\xD0\xCF\x11\xE0')
        
        # 1. CSV 처리 (메모리 최적화를 위한 청크 단위 처리)
        if file.name.lower().endswith('.csv'):
            # 파일 크기 확인
            file.seek(0, 2)  # 파일 끝으로 이동
            file_size = file.tell()
            file.seek(0)     # 파일 시작으로 이동
            
            # 10MB 이상인 경우 청크 단위로 처리
            if file_size > 10 * 1024 * 1024:  # 10MB
                chunks = []
                chunk_size = 1000  # 한 번에 처리할 행 수
                for chunk in pd.read_csv(file, chunksize=chunk_size):
                    chunks.append(chunk)
                return pd.concat(chunks, ignore_index=True)
            else:
                return pd.read_csv(file)
            
        # 2. Excel (XLSB)
        elif file.name.lower().endswith('.xlsb'):
            return pd.read_excel(file, engine='pyxlsb', header=None)
            
        # 3. Excel (XLSX, XLS)
        elif file.name.lower().endswith(('.xlsx', '.xls')):
            try:
                # 1차 시도: 최신/가장 빠른 엔진 (calamine) 또는 openpyxl
                engine = 'calamine' if file.name.lower().endswith(('.xlsx', '.xlsb', '.xls')) else 'openpyxl'
                return pd.read_excel(file, engine=engine, header=None)
            except Exception as e:
                # 2차 시도: 엔진 교차 테스트 (확장자 불일치 대응)
                try:
                    file.seek(0)
                    fallback_engine = 'openpyxl' if file.name.lower().endswith('.xlsx') else 'xlrd'
                    return pd.read_excel(file, engine=fallback_engine, header=None)
                except Exception:
                    # 3차 시도: pyxlsb 엔진 지정 (xlsb 특이 케이스)
                    try:
                        file.seek(0)
                        return pd.read_excel(file, engine='pyxlsb', header=None)
                    except Exception as final_e:
                        # 4차 시도: 확장자만 엑셀이고 실제로는 CSV/TSV 형식인 경우
                        import io
                        try:
                            file.seek(0)
                            success_df = None
                            for sep in [',', '\t', '|']:
                                for enc in ['utf-8', 'cp949', 'euc-kr', 'utf-16']:
                                    try:
                                        file.seek(0)
                                        df_csv = pd.read_csv(file, sep=sep, encoding=enc, engine='python', on_bad_lines='skip')
                                        if not df_csv.empty and len(df_csv.columns) >= 1:
                                            success_df = df_csv
                                            break
                                    except:
                                        pass
                                if success_df is not None:
                                    break
                            
                            if success_df is not None:
                                return success_df
                            raise Exception("CSV parsing failed")
                        except:
                            # 5차 시도: 실제로는 HTML 테이블로 내보낸 파일인 경우
                            try:
                                html_tables = None
                                for enc in ['utf-8', 'cp949', 'euc-kr', 'utf-16']:
                                    try:
                                        file.seek(0)
                                        tables = pd.read_html(file, encoding=enc)
                                        if tables:
                                            html_tables = tables[0]
                                            break
                                    except:
                                        pass
                                if html_tables is not None:
                                    return html_tables
                                raise Exception("HTML parsing failed")
                            except:
                                pass
                                
                        # 모든 시도에서 실패했을 때, 원인 분석 및 안내
                        file.seek(0)
                        file_header = file.read(8).hex()
                        
                        if file.name.lower().endswith('.xlsx'):
                            if not is_zip:
                                if is_ole:
                                    st.error("❌ 업로드된 파일이 암호화(비밀번호)되어 있거나, .xls 포맷인데 확장자만 .xlsx로 되어 있습니다. '다른 이름으로 저장' > '.xlsx' (비밀번호 해제) 후 다시 올려주세요.")
                                else:
                                    st.error(f"❌ 파일이 손상되었거나 DRM(보안문서)이 적용되어 있습니다. (헤더정보: {file_header}) 일반 엑셀 파일이라면 보안 해제 후 업로드하거나, 시스템에서 CSV 파일 형식으로 다운로드하여 올려주세요.")
                            else:
                                st.error("❌ 엑셀 파일을 처리하는 도중 파일 크기 초과 또는 내부 구조적 오류가 발생했습니다. (파일이 지나치게 크거나 일부 손상됨)")
                            return None
                        raise e # 최종 에러 발생
                        
        # 4. JSON 처리
        elif file.name.lower().endswith('.json'):
            import json
            try:
                data = json.load(file)
                # JSON 데이터를 DataFrame으로 변환
                if isinstance(data, list):
                    return pd.DataFrame(data)
                elif isinstance(data, dict):
                    # 딕셔너리의 경우 키를 컬럼으로 사용
                    return pd.DataFrame([data])
                else:
                    st.error("지원하지 않는 JSON 형식입니다.")
                    return None
            except Exception as e:
                st.error(f"JSON 파일 로드 실패: {str(e)}")
                return None
                
        # 5. XML 처리
        elif file.name.lower().endswith('.xml'):
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(file)
                root = tree.getroot()
                
                # XML 데이터를 DataFrame으로 변환
                data = []
                for child in root:
                    row = {}
                    for subchild in child:
                        row[subchild.tag] = subchild.text
                    data.append(row)
                
                return pd.DataFrame(data)
            except Exception as e:
                st.error(f"XML 파일 로드 실패: {str(e)}")
                return None
                        
    except Exception as e:
        st.error(f"📂 파일 로드 실패: {file.name}\n원인: {str(e)}")
        return None
    return None

def load_sample_data():
    try:
        orders = pd.read_csv("orders_sample.csv")
        capa = pd.read_csv("capacity_sample.csv")
        return orders, capa
    except:
        return None, None

# --- 구글 시트 연동 설정 ---
try:
    from streamlit_gsheets import GSheetsConnection
except ImportError:
    # 라이브러리 설치 대기 시 로컬 모드로 전환
    pass

GSHEET_URL = "https://docs.google.com/spreadsheets/d/11JhawrE8mwdPekmldSPk--_yZ5DBOSapk8_tlyQZk-M/edit?usp=sharing"

def save_capa_data(df):
    """공장 마스터 정보를 구글 시트(인터넷)와 로컬(JSON) 모두에 저장"""
    try:
        # 1. 로컬 저장 (DRM 회피용 백업)
        df.to_json(CAPA_FILE_JSON, orient="records", date_format="iso")
        
        # 2. 구글 시트 저장 (인터넷 영구 저장)
        conn = st.connection("gsheets", type=GSheetsConnection)
        # 구글 시트는 형식이 엄격하므로 날짜를 텍스트로 변환하여 안전하게 저장
        save_df = df.copy()
        for col in ['effective_from', 'effective_to']:
            save_df[col] = save_df[col].dt.strftime('%Y-%m-%d')
            
        conn.update(spreadsheet=GSHEET_URL, data=save_df)
        return True
    except Exception as e:
        st.warning(f"인터넷 저장(구글 시트)에 실패했습니다. 로컬 파일에만 저장됩니다.\n원인: {e}")
        return False

CAPA_FILE_JSON = "capacity_master.json"
ORDERS_FILE_JSON = "orders_master.json"

def save_orders_data(df):
    """업로드된 주문 데이터를 JSON으로 저장 (DRM 회피)"""
    try:
        df.to_json(ORDERS_FILE_JSON, orient="records", date_format="iso")
        return True
    except Exception as e:
        st.error(f"주문 데이터 저장 실패: {e}")
        return False

import json

# --- 시스템 설정(날짜 등) 영구 저장 ---
# --- 시스템 설정(날짜 등) 영구 저장 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "system_config.json")
USER_CONFIG_FILE = os.path.join(BASE_DIR, "user_config.json")

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Config load error: {e}")
    return {}

def save_config(key, value):
    try:
        config = load_config()
        config[key] = value
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Config save failed: {e}")
        return False

def load_user_config():
    try:
        if os.path.exists(USER_CONFIG_FILE):
            with open(USER_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"User config load error: {e}")
    return {}

def save_user_config(key, value):
    try:
        config = load_user_config()
        config[key] = value
        with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"User config save failed: {e}")
        return False

# [System Config] 초기 로드
def to_date(val):
    if val is None: return None
    try:
        # [Fix] Type Check Priority
        if isinstance(val, date) and not isinstance(val, datetime):
            return val
        if isinstance(val, (int, float)):
            if val > 100000000000: 
                return pd.to_datetime(val, unit='ms').date()
            else:
                return pd.to_datetime(val, unit='s').date()
        if isinstance(val, str):
            return pd.to_datetime(val).date()
        if hasattr(val, 'date'):
             if callable(val.date): return val.date()
             return val.date
        if isinstance(val, (pd.Timestamp, datetime)):
            return val.date()
    except:
        pass
    return val

if "analysis_start" not in st.session_state or "analysis_end" not in st.session_state:
    config = load_config()
    if "analysis_start" not in st.session_state and "analysis_start" in config:
        st.session_state["analysis_start"] = to_date(config["analysis_start"])
    if "analysis_end" not in st.session_state and "analysis_end" in config:
        st.session_state["analysis_end"] = to_date(config["analysis_end"])

# [Senior Debug] 세션 상태 초기화 및 데이터 복구 (구글 시트 우선)
if "capa_data" not in st.session_state:
    df_c = None
    # 1순위: 인터넷(구글 시트)에서 가져오기
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_c = conn.read(spreadsheet=GSHEET_URL)
        for col in ['effective_from', 'effective_to']:
            df_c[col] = pd.to_datetime(df_c[col])
    except Exception as e:
        # 2순위: 로컬 백업 파일에서 가져오기
        if os.path.exists(CAPA_FILE_JSON):
            try:
                df_c = pd.read_json(CAPA_FILE_JSON)
                for col in ['effective_from', 'effective_to']:
                    df_c[col] = pd.to_datetime(df_c[col])
            except: pass
    
    if df_c is None:
        # 3순위: 기본 샘플 로드 (실패 시 긴급 생성)
        try:
            df_c = pd.read_csv("capacity_sample.csv")
            for col in ['effective_from', 'effective_to']:
                    df_c[col] = pd.to_datetime(df_c[col], errors='coerce')
        except:
             df_c = pd.DataFrame({
                'plant': [1, 2, 3, 4, 5],
                'total_area_m2': [1000.0] * 5,
                'usage_rate': [100.0] * 5,
                'capacity_m2': [1000.0] * 5,
                'effective_from': pd.to_datetime(['2000-01-01'] * 5),
                'effective_to': pd.to_datetime(['2099-12-31'] * 5)
            })
    st.session_state["capa_data"] = df_c

# [무조건 1동~5동 규격 유지]
if len(st.session_state["capa_data"]) != 5 or not all(p in st.session_state["capa_data"]['plant'].values for p in [1, 2, 3, 4, 5]):
    curr = st.session_state["capa_data"]
    new_df = pd.DataFrame({
        'plant': [1, 2, 3, 4, 5],
        'total_area_m2': [1000.0] * 5,
        'usage_rate': [100.0] * 5,
        'capacity_m2': [1000.0] * 5,
        'effective_from': pd.to_datetime(['2000-01-01'] * 5),
        'effective_to': pd.to_datetime(['2099-12-31'] * 5)
    })
    for p in [1, 2, 3, 4, 5]:
        match = curr[curr['plant'] == p]
        if not match.empty:
            if 'total_area_m2' in match.columns:
                new_df.loc[new_df['plant'] == p, 'total_area_m2'] = float(match.iloc[-1]['total_area_m2'])
            else:
                new_df.loc[new_df['plant'] == p, 'total_area_m2'] = float(match.iloc[-1]['capacity_m2'])
            
            if 'usage_rate' in match.columns:
                new_df.loc[new_df['plant'] == p, 'usage_rate'] = float(match.iloc[-1]['usage_rate'])
                
            new_df.loc[new_df['plant'] == p, 'capacity_m2'] = new_df.loc[new_df['plant'] == p, 'total_area_m2'] * (new_df.loc[new_df['plant'] == p, 'usage_rate'] / 100.0)
    st.session_state["capa_data"] = new_df
    save_capa_data(new_df)

if "orders_data" not in st.session_state:
    df_o = None
    if os.path.exists(ORDERS_FILE_JSON):
        try:
            df_o = pd.read_json(ORDERS_FILE_JSON)
            for col in ['due_date', 'start_in', 'end_out']:
                df_o[col] = pd.to_datetime(df_o[col])
        except: pass
    
    if df_o is None:
        # JSON 없으면 샘플 로드
        sample_o, _ = load_sample_data()
        df_o = sample_o if sample_o is not None else pd.DataFrame()
    st.session_state["orders_data"] = df_o

# --- UI 레이아웃 ---
# 1. Sidebar - 마온 정보 관리
with st.sidebar:
    st.header("⚙️ 환경 설정")
    
    with st.expander("🏢 공장 마스터 정보 관리", expanded=False):
        st.markdown("<p style='font-size: 0.85rem; color: #aaa; margin-bottom: 10px; white-space: nowrap;'>각 동별 전체면적(m2)을 수정하세요.</p>", unsafe_allow_html=True)
        
        # 데이터 에디터: 소수점 입력을 위해 데이터 타입을 명시적으로 float으로 유지
        # [User Request] 제목 및 첫 번째 열 데이터 가운데 정렬 구현
        # st.data_editor의 정렬 한계를 극복하기 위해 st.columns와 HTML 스타일링 활용
        st.markdown("""
            <div style="display: flex; background-color: rgba(255,255,255,0.05); padding: 8px 0; border-radius: 4px; border-bottom: 2px solid #555; margin-bottom: 10px;">
                <div style="flex: 0.5; text-align: center; font-weight: bold; font-size: 0.7rem;">공장</div>
                <div style="flex: 1.2; text-align: center; font-weight: bold; font-size: 0.7rem;">전체면적</div>
                <div style="flex: 1.1; text-align: center; font-weight: bold; font-size: 0.7rem;">실사용률</div>
                <div style="flex: 1.2; text-align: center; font-weight: bold; font-size: 0.7rem;">가용면적</div>
                <div style="flex: 0.1;"></div>
            </div>
        """, unsafe_allow_html=True)
        
        # 데이터 업데이트 감지용
        new_capa = st.session_state["capa_data"].copy()
        is_changed = False
        
        for i, row in new_capa.iterrows():
            c1, c2, c3, c4, c5 = st.columns([0.5, 1.2, 1.1, 1.2, 0.1])
            with c1:
                st.markdown(f"<div style='text-align: center; padding-top: 8px; font-size: 0.9rem; font-weight: 500;'>{int(row['plant'])}동</div>", unsafe_allow_html=True)
            with c2:
                # 전체면적 입력
                new_total = st.number_input(
                    f"total_val_{i}", 
                    value=int(row['total_area_m2']), 
                    min_value=0, 
                    step=1, 
                    format="%d", 
                    label_visibility="collapsed", 
                    key=f"total_input_{i}"
                )
                if abs(new_total - row['total_area_m2']) > 0.001:
                    new_capa.at[i, 'total_area_m2'] = new_total
                    new_capa.at[i, 'capacity_m2'] = new_total * (row['usage_rate'] / 100.0)
                    is_changed = True
            with c3:
                # 실사용률 입력
                new_rate = st.number_input(
                    f"rate_val_{i}", 
                    value=int(row['usage_rate']), 
                    min_value=0, 
                    max_value=1000,
                    step=1, 
                    format="%d", 
                    label_visibility="collapsed", 
                    key=f"rate_input_{i}"
                )
                if abs(new_rate - row['usage_rate']) > 0.001:
                    new_capa.at[i, 'usage_rate'] = new_rate
                    new_capa.at[i, 'capacity_m2'] = row['total_area_m2'] * (new_rate / 100.0)
                    is_changed = True
            with c4:
                # 가용면적 (자동 계산 결과 표시)
                # 계산값 고정 및 가독성을 위해 disabled=True 처리하여 강조 효과
                st.markdown(f"""
                    <div style="
                        background-color: #f0f2f6; 
                        padding: 8px 0; 
                        border-radius: 4px; 
                        text-align: center; 
                        font-family: 'Malgun Gothic', monospace;
                        font-size: 0.85rem;
                        border: 1px solid #ccc;
                        color: #000000;
                        font-weight: 800;
                    ">
                        {int(row['capacity_m2']):,d}
                    </div>
                """, unsafe_allow_html=True)
        
        if is_changed:
            st.session_state["capa_data"] = new_capa
            save_capa_data(new_capa)
            st.rerun()

    st.divider()
    st.info("전체면적이나 실사용률 수정 시 실시간으로 점유율 추이가 갱신되며 파일에 저장됩니다.")

# --- 주문 데이터 영구 저장 로직 ---
ORDERS_FILE = "orders_sample.csv"

def save_orders_data(df):
    """업로드된 주문 데이터를 로컬 파일에 저장하여 새로고침 시에도 유지되게 함"""
    try:
        df.to_csv(ORDERS_FILE, index=False)
        return True
    except Exception as e:
        st.error(f"주문 데이터 저장 중 오류 발생: {e}")
        return False

# --- 커스텀 CSS (UI 타이포그래피 개선) ---
st.markdown("""
<style>
    /* Streamlit 탭 메뉴 폰트 크기를 약 2배로 키우기 */
    button[data-baseweb="tab"] > div[data-testid="stMarkdownContainer"] > p {
        font-size: 28px !important;
        font-weight: 700 !important;
    }
    /* 라디오 버튼 옵션 글씨 크기 조정 */
    div[data-testid="stRadio"] label p {
        font-size: 1.0rem !important;
        font-weight: 500 !important;
    }
    /* 팝오버 버튼(주요 기능 안내 등) 글씨 크기 조정 */
    div[data-testid="stPopover"] button p {
        font-size: 0.85rem !important;
    }
    /* 사이드바 전체 너비 축소 (시인성 확보를 위해 이전보다 약간 확대) */
    [data-testid="stSidebar"] {
        min-width: 380px !important;
        max-width: 380px !important;
    }
    /* 페이지 최상단 여백 줄이기 */
    .main .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    /* number_input의 + / - 버튼 숨기기 */
    button[data-testid="stNumberInputStepUp"],
    button[data-testid="stNumberInputStepDown"] {
        display: none !important;
    }
    /* 버튼이 사라진 후 입력창의 너비와 가독성 확보 및 가운데 정렬 */
    div[data-testid="stNumberInput"] input {
        padding-right: 10px !important;
        text-align: center !important;
    }
    /* 날짜 입력창 텍스트 가운데 정렬 */
    div[data-testid="stDateInput"] input {
        text-align: center !important;
    }
    /* 데이터프레임 및 테이블 전체 텍스트 가운데 정렬 (Header & Cell) */
    [data-testid="stTable"] td, [data-testid="stTable"] th {
        text-align: center !important;
    }
    /* 데이터프레임(st.dataframe) 내의 모든 요소 가운데 정렬 시도 */
    div[data-testid="stDataFrame"] [role="columnheader"] p,
    div[data-testid="stDataFrame"] [role="gridcell"] {
        text-align: center !important;
        justify-content: center !important;
    }
    /* 4번째 탭(테스트용) 글씨 크기 축소 */
    div[data-testid="stTabs"] button[id^="tabs-bui"][id$="-tab-3"] div p,
    div[data-testid="stTabs"] button[id^="tabs-bui"][id$="-tab-4"] div p {
        font-size: 0.8rem !important;
        color: #888 !important;
    }
    /* 커스텀 컴팩트 테이블 스타일 (User Request: 간격 축소 및 디자인 개선) */
    .compact-table-container {
        border: 1px solid #e6e9ef;
        border-radius: 10px;
        overflow: hidden;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        background-color: white;
    }
    .compact-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Pretendard', 'Inter', sans-serif;
        font-size: 0.9rem;
    }
    .compact-table th {
        background-color: #f8f9fa;
        color: #6c757d;
        font-weight: 700;
        text-align: center;
        padding: 10px 12px;
        border-bottom: 2px solid #edeff2;
        text-transform: uppercase;
        letter-spacing: 0.02em;
    }
    .compact-table td {
        padding: 6px 12px;
        border-bottom: 1px solid #f1f3f5;
        color: #444;
        text-align: center;
    }
    .compact-table tr:nth-child(even) {
        background-color: #fcfcfc;
    }
    .compact-table tr:hover {
        background-color: #f8f9ff;
        transition: background-color 0.2s ease;
    }
    .compact-table tr:last-child td {
        border-bottom: none;
    }
    /* 특정 컬럼 강조 (사용자명) */
    .compact-table td:first-child {
        font-weight: 600;
        color: #007bff;
    }
</style>
""", unsafe_allow_html=True)

# UI 구성 (Tabs)
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 공장 점유율 현황", "🧪 조건 설정 시뮬레이션", "🔮 AI 점유율 예측", "🧪 공장 점유율 현황_test", "🛠️ 개발중"])

with tab1:
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    # --- 상단 컨트롤 (업로드 + 임계치) ---
    col_up, col_gap, col_thresh = st.columns([2.2, 0.3, 1])
    
    with col_up:
        # [User Request] 제목과 설명을 한 줄로 배치 및 문구 수정
        st.markdown(f"""
            <div style="display: flex; align-items: baseline; gap: 12px; margin-bottom: 5px;">
                <h3 style="margin: 0; font-size: 1.35rem;">📥 데이터 업로드</h3>
                <span style="color: #aaa; font-size: 0.95rem;">"생산관리일정표" 엑셀 파일에서 자동으로 동별 점유율을 계산_ #100도장(시작일)~#140포장(종료일)</span>
            </div>
        """, unsafe_allow_html=True)
        orders_file_main = st.file_uploader('"생산관리일정표" 파일을 드래그하거나 클릭하여 업로드하세요.', 
                                            type=["csv", "xlsx", "xls", "xlsb"], key="main_orders_upload")
    
    with col_thresh:
        # [User Request] 설정 영역도 하단 카드들과 동일한 디자인으로 변경
        with st.container(border=True):
            st.markdown(f"""
                <div style="display: flex; align-items: baseline; gap: 10px; margin-bottom: 10px;">
                    <p style='font-size: 1.05rem; font-weight: 700; color: #6c757d; margin: 0;'>⚙️ 설정</p>
                    <span style="color: #aaa; font-size: 0.85rem;">시뮬레이션 분석 기준 및 임계값 설정</span>
                </div>
            """, unsafe_allow_html=True)
            
            # [Persistence] 임계치 저장 로직
            if "saturation_threshold" not in st.session_state:
                 config = load_config()
                 st.session_state["saturation_threshold"] = float(config.get("saturation_threshold", 80))
                 
            def on_threshold_change():
                val = st.session_state["threshold_slider"]
                st.session_state["saturation_threshold"] = val
                save_config("saturation_threshold", val)

            # 라벨 상단 배치 스타일
            st.write("<p style='font-size: 0.85rem; color: #aaa; margin-bottom: -5px;'>포화 임계치 (%)</p>", unsafe_allow_html=True)
            threshold = st.slider(
                "Threshold", 0, 100, 
                value=int(st.session_state["saturation_threshold"]), 
                help="이 수치 이상일 때 그래프에 붉은 점선이 표시됩니다.",
                key="threshold_slider",
                on_change=on_threshold_change,
                label_visibility="collapsed"
            ) / 100
            
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            st.write("<p style='font-size: 0.85rem; color: #aaa; margin-bottom: -5px;'>기준</p>", unsafe_allow_html=True)
            metric_opt = st.radio("Metric2", ["점유율 (%)", "면적"], horizontal=True, label_visibility="collapsed")
            metric = 'rate' if '점유율' in metric_opt else 'area'
    
    if "last_uploaded_file" not in st.session_state:
        st.session_state["last_uploaded_file"] = None

    if orders_file_main:
        # 파일이 변경되었을 때만 처리 (이름 + 크기 기준)
        file_id = f"{orders_file_main.name}_{orders_file_main.size}"
        if st.session_state["last_uploaded_file"] != file_id:
            raw_df = load_data(orders_file_main)
            if raw_df is not None:
                transformer = DataTransformer()
                transformed_df = transformer.transform_orders(raw_df)
                
                st.session_state["orders_data"] = transformed_df
                save_orders_data(transformed_df)
                st.session_state["last_uploaded_file"] = file_id # 처리 완료 마킹
                
                st.success(f"'{orders_file_main.name}' 업로드 완료 및 시스템 기본 데이터로 저장되었습니다.")
                st.rerun()

    # 데이터 및 Capa 존재 여부 확인
    if st.session_state["orders_data"] is not None and st.session_state["capa_data"] is not None:
        # --- 데이터 검증 및 분석 ---
        validator = DataValidator()
        # validator.validate_orders 는 이제 (valid_df, full_df, errors)를 반환함
        valid_orders, full_processed, order_errors = validator.validate_orders(st.session_state["orders_data"])
        clean_capa, capa_errors = validator.validate_capacity(st.session_state["capa_data"])
        
        # --- 1. 데이터 처리 통계 (전처리 요약) ---
        total_rows = len(full_processed)
        included_rows = len(valid_orders)
        structural_rows = len(full_processed[full_processed['row_type'].isin(['HEADER', 'STRUCTURAL'])])
        error_rows = total_rows - included_rows - structural_rows

        # [User Request] 기본 텍스트 색상을 흰색(Light)으로 변경하여 가시성 확보
        summary_html = f"""
        <div style="
            display: flex; 
            align-items: center; 
            gap: 20px; 
            border-left: 5px solid #007bff; 
            padding: 0.5rem 1.25rem; 
            margin: 1rem 0;
            flex-wrap: wrap;
        ">
            <h3 style="margin: 0; font-size: 1.3rem; white-space: nowrap;">📊 데이터 전처리 현황</h3>
            <span style="font-size: 1.15rem; font-weight: 500; color: #000000;">
                총 <b style="color: #007bff;">{total_rows:,}</b>건 중 
                <b style="color: #28a745;">{included_rows:,}</b>건 분석 
                <span style="font-size: 0.9rem; color: #aaa; font-weight: 400; margin-left: 4px;">
                    ({structural_rows:,}건 구조 제외, {error_rows:,}건 오류 제외)
                </span>
            </span>
        </div>
        """
        st.markdown(summary_html, unsafe_allow_html=True)

        # --- 2. 상세 결과 다운로드 및 확인 ---
        with st.expander("🛠️ 전처리 상세 로그 및 다운로드"):
            st.write("모든 추출 행에 대한 처리 상태(is_included, row_type 등)를 확인할 수 있습니다.")
            # 상세 결과 보기 (정렬 및 필터링 기능 추가)
            st.dataframe(
                full_processed, 
                width="stretch",
                height=400
            )
            
            # 다운로드 버튼
            csv_data = full_processed.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 전처리 전체 결과 다운로드 (CSV)",
                data=csv_data,
                file_name=f"processed_orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )

        if order_errors or capa_errors:
            status = st.status("⚠️ 데이터 이슈 발견 (일부 행 분석 제외)", expanded=False)
            with status:
                for err in order_errors:
                    st.error(err)
                for err in capa_errors:
                    st.warning(err)
            status.update(label="데이터 이슈 확인 완료", state="complete")
        


        if valid_orders.empty:
            st.warning("계산 가능한 유효한 주문 데이터가 없습니다.")
        else:
            try:
                # --- [User Request] 카드형 제어판 레이아웃으로 개편 ---
                st.divider()
                
                # 데이터 기반 기본값 산출 및 범위 설정
                MIN_DATE = datetime(2022, 1, 1).date()
                MAX_DATE = datetime(2042, 12, 31).date()
                today = datetime.now().date()
                
                data_min = valid_orders['start_in'].min().date() if not valid_orders['start_in'].isna().all() else today
                data_max = valid_orders['end_out'].max().date() if not valid_orders['end_out'].isna().all() else today
                def_start = max(MIN_DATE, min(data_min, MAX_DATE))
                def_end = max(MIN_DATE, min(data_max, MAX_DATE))
                
                # 세션 초기화 및 상태 유지
                if "analysis_start" not in st.session_state:
                    st.session_state["analysis_start"] = def_start
                if "analysis_end" not in st.session_state:
                    st.session_state["analysis_end"] = def_end

                # 콜백 및 도움 기능 정의
                def update_dates(s, e):
                    st.session_state["analysis_start"] = s
                    st.session_state["analysis_end"] = e
                    save_config("analysis_start", str(s))
                    save_config("analysis_end", str(e))

                def on_start_date_change():
                    val_s = st.session_state["date_start_picker"]
                    st.session_state["analysis_start"] = val_s
                    save_config("analysis_start", str(val_s))
                    
                def on_end_date_change():
                    val_e = st.session_state["date_end_picker"]
                    st.session_state["analysis_end"] = val_e
                    save_config("analysis_end", str(val_e))

                # 카드 3단 구성
                col_c1, col_c2, col_c3 = st.columns([2.5, 1.2, 1.3])

                with col_c1:
                    with st.container(border=True):
                        st.markdown("<p style='font-size: 1.05rem; font-weight: 700; color: #007bff; margin-bottom: 10px;'>🗓️ 분석 기간</p>", unsafe_allow_html=True)
                        
                        # 1. 퀵 프리셋 버튼
                        st.write("<p style='font-size: 0.85rem; color: #aaa; margin-bottom: 5px;'>퀵 기간 설정</p>", unsafe_allow_html=True)
                        q1, q2, q3 = st.columns(3)
                        if q1.button("📅 이번달", width="stretch", key="btn_this_month"):
                            import calendar
                            s = today.replace(day=1)
                            _, last_day = calendar.monthrange(today.year, today.month)
                            e = today.replace(day=last_day)
                            update_dates(s, e); st.rerun()
                        if q2.button("🗓️ 다음 3개월", width="stretch", key="btn_next_3m"):
                            import calendar
                            s = today.replace(day=1)
                            target_month = today.month + 2
                            target_year = today.year + (target_month - 1) // 12
                            target_month = (target_month - 1) % 12 + 1
                            _, last_day = calendar.monthrange(target_year, target_month)
                            e = date(target_year, target_month, last_day)
                            update_dates(s, e); st.rerun()
                        if q3.button("🌍 올해 전체", width="stretch", key="btn_full_year"):
                            update_dates(date(today.year, 1, 1), date(today.year, 12, 31)); st.rerun()

                        # 2. 날짜 직접 입력
                        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                        d1, d2 = st.columns(2)
                        with d1:
                            st.write("<p style='font-size: 0.85rem; color: #aaa; margin-bottom: -5px;'>분석 시작일</p>", unsafe_allow_html=True)
                            st.date_input("Start", value=st.session_state["analysis_start"], min_value=MIN_DATE, max_value=MAX_DATE, label_visibility="collapsed", key="date_start_picker", on_change=on_start_date_change)
                        with d2:
                            st.write("<p style='font-size: 0.85rem; color: #aaa; margin-bottom: -5px;'>분석 종료일</p>", unsafe_allow_html=True)
                            st.date_input("End", value=st.session_state["analysis_end"], min_value=MIN_DATE, max_value=MAX_DATE, label_visibility="collapsed", key="date_end_picker", on_change=on_end_date_change)

                with col_c2:
                    with st.container(border=True):
                        st.markdown("<p style='font-size: 1.05rem; font-weight: 700; color: #28a745; margin-bottom: 10px;'>🎯 분석 모드</p>", unsafe_allow_html=True)
                        
                        st.write("<p style='font-size: 0.85rem; color: #aaa; margin-bottom: -5px;'>데이터 기준 선택</p>", unsafe_allow_html=True)
                        mode_opt = st.selectbox("Mode", ["계획 (일자행)", "실적 (실행행)"], index=0, label_visibility="collapsed")
                        proc_mode = 'plan' if "계획" in mode_opt else 'actual'
                        
                        st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
                        st.write("<p style='font-size: 0.85rem; color: #aaa; margin-bottom: -5px;'>예상 데이터</p>", unsafe_allow_html=True)
                        inc_est = st.toggle("🔍 종료일 추정치 포함", value=True)

                with col_c3:
                    with st.container(border=True):
                        st.markdown("<p style='font-size: 1.05rem; font-weight: 700; color: #fd7e14; margin-bottom: 10px;'>⚙️ 표현 방식</p>", unsafe_allow_html=True)
                        
                        st.write("<p style='font-size: 0.85rem; color: #aaa; margin-bottom: -5px;'>X축 단위</p>", unsafe_allow_html=True)
                        gran_opt = st.selectbox("Granularity", ["일별 (Day)", "주별 (Week)", "월별 (Month)"], index=1, label_visibility="collapsed")
                        if "일별" in gran_opt: gran = 'D'
                        elif "주별" in gran_opt: gran = 'W'
                        else: gran = 'M'
                        
                        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                        st.write("<p style='font-size: 0.85rem; color: #aaa; margin-bottom: -5px;'>집계 방식</p>", unsafe_allow_html=True)
                        agg_opt = st.selectbox("Aggregation", ["최대값 (MAX)", "평균 (AVG)"], index=1, label_visibility="collapsed")
                        agg = 'MAX' if "최대값" in agg_opt else 'AVG'

                # 세션 연동 변수 확정
                s_date = st.session_state["analysis_start"]
                e_date = st.session_state["analysis_end"]

                # [User Request] 시각화 설정 카드 디자인 고도화
                with st.container(border=True):
                    st.markdown("<p style='font-size: 1.05rem; font-weight: 700; color: #9c27b0; margin-bottom: 10px;'>📊 시각화 설정</p>", unsafe_allow_html=True)
                    col_m1, col_m2 = st.columns([1.1, 1.4])
                    with col_m1:
                        st.write("<p style='font-size: 0.85rem; color: #aaa; margin-bottom: -5px;'>📏 표시 기준</p>", unsafe_allow_html=True)
                        metric_opt = st.radio("Metric", ["점유율 (%)", "점유면적 (㎡)"], horizontal=True, label_visibility="collapsed")
                    with col_m2:
                        # [User Request] 가로 폭 50% 축소를 위해 하위 컬럼으로 분리
                        sub_col_s1, sub_col_s2 = st.columns([1, 1])
                        with sub_col_s1:
                            # [Persistence] 날짜 개수 세션 상태 관리 (기본값 6으로 변경)
                            if "date_count" not in st.session_state:
                                st.session_state["date_count"] = 6
                            
                            # [Dynamic Label] 실시간 업데이트를 위해 빈 공간(placeholder) 생성
                            label_placeholder = st.empty()
                            
                            # 슬라이더에서 즉각적으로 상태를 받기 위한 설정
                            date_count = st.slider(
                                "Count", 6, 12, 
                                value=st.session_state["date_count"], 
                                label_visibility="collapsed", 
                                key="date_count_slider_widget"
                            )
                            st.session_state["date_count"] = date_count
                            
                            # [User Request] 제목을 조금 더 위로 올려서 6 숫자가 잘 보이게 조정 (margin-bottom: 5px)
                            label_placeholder.markdown(f"""
                                <div style='display: flex; align-items: baseline; gap: 8px; margin-bottom: 8px; margin-top: -5px;'>
                                    <p style='font-size: 0.95rem; color: #000000; font-weight: 800; margin: 0; white-space: nowrap;'>📅 표시 날짜 개수 <span style='color: #28a745;'>(현재 : {date_count}개)</span></p>
                                    <span style='font-size: 0.75rem; color: #777; font-weight: 400; white-space: nowrap;'>| 조정</span>
                                </div>
                            """, unsafe_allow_html=True)
                
                metric = 'rate' if '%' in metric_opt else 'area'

                if s_date and e_date and s_date <= e_date:
                    # [CRITICAL FIX] "표시 날짜 개수(date_count)"를 만족시키기 위해 분석 엔진의 종료일(e_date)을 일시적으로 대폭 연장
                    calc_e_date = e_date
                    if gran == 'D':
                        calc_e_date = max(e_date, s_date + timedelta(days=date_count * 2))
                    elif gran == 'W':
                        calc_e_date = max(e_date, s_date + timedelta(weeks=date_count + 2))
                    elif gran == 'M':
                        calc_e_date = max(e_date, s_date + timedelta(days=date_count * 32))

                    engine = OccupancyEngine()
                    results = engine.calculate_daily_occupancy(
                        valid_orders, clean_capa,
                        start_date=s_date, end_date=calc_e_date,
                        mode=proc_mode, include_estimated=inc_est,
                        granularity=gran, aggregation=agg,
                        threshold=threshold
                    )
                    
                    daily_df = results["daily_occupancy"]
                    final_df = results["final_df"]
                    
                    if final_df.empty:
                        st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
                    else:
                        # 히트맵용 피벗 데이터 생성
                        if gran == 'D':
                             val_col = 'OCC_RATE_D' if metric_opt == "점유율 (%)" else 'OCC_AREA_D'
                        else:
                             val_col = f'OCC_RATE_{gran}{agg}' if metric == 'rate' else f'OCC_AREA_{gran}{agg}'
                             
                        pivot_df = final_df.pivot(index='plant', columns='date', values=val_col)

                        # [Visual Logic] X축 필터링 & 슬라이싱 (User Request)
                        if gran == 'D':
                            # 1. 주말(토/일) 제거
                            valid_dates = [d for d in pivot_df.columns if d.weekday() < 5]
                            
                            # 2. 공휴일 제거 (2024~2027 주요 공휴일)
                            holidays = [
                                "2024-01-01", "2024-02-09", "2024-02-12", "2024-03-01", "2024-04-10", "2024-05-01", "2024-05-06", "2024-05-15", "2024-06-06", "2024-08-15", "2024-09-16", "2024-09-17", "2024-09-18", "2024-10-03", "2024-10-09", "2024-12-25",
                                "2025-01-01", "2025-01-27", "2025-01-28", "2025-01-29", "2025-01-30", "2025-03-03", "2025-05-01", "2025-05-05", "2025-05-06", "2025-06-06", "2025-08-15", "2025-10-03", "2025-10-06", "2025-10-07", "2025-10-08", "2025-10-09", "2025-12-25",
                                "2026-01-01", "2026-02-16", "2026-02-17", "2026-02-18", "2026-03-02", "2026-05-01", "2026-05-05", "2026-05-25", "2026-06-06", "2026-08-17", "2026-09-23", "2026-09-24", "2026-09-25", "2026-10-05", "2026-10-09", "2026-12-25",
                                "2027-01-01", "2027-02-05", "2027-02-06", "2027-02-07"
                            ]
                            valid_dates = [d for d in valid_dates if str(d.date()) not in holidays]
                            pivot_df = pivot_df[valid_dates]

                        # --- NEW: 표시 시작일 제한 ---
                        # 분석 시작일(s_date) 이후의 컬럼만 남기도록 필터링
                        # 주/월 단위 집계 시 start_date 이전 데이터가 포함되어 나오는 문제 해결
                        s_datetime = pd.to_datetime(s_date)
                        valid_columns = [d for d in pivot_df.columns if d >= s_datetime]
                        if valid_columns:
                            pivot_df = pivot_df[valid_columns]

                        # 3. 최근/앞에서부터 N개 컬럼만 유지 (Sliding Window) 
                        # - 기존에는 `iloc[:, -date_count:]`로 뒤에서부터 보여주었으나,
                        # - 시작일부터 보여주길 원한다면 `iloc[:, :date_count]`로 잘라도 됩니다.
                        # - 여기서는 분석 종료일이 과거일 수도 있으므로, 선택된 범위(s_date 이후) 중 앞쪽부터 지정된 개수만큼 자르도록 변경합니다.
                        if len(pivot_df.columns) > date_count:
                            pivot_df = pivot_df.iloc[:, :date_count]
                            
                        # 히트맵과 동일한 날짜를 추가 시각화에도 적용하기 위해 저장
                        display_dates = pivot_df.columns.tolist()
                            
                        # [Visual Logic] X축 라벨 포맷 변경 (User Request)
                        # 1. 일별: "4/21" (일 문자 제거)
                        # 2. 주별: "3/16(12w)" (주차 표시 추가)
                        # 3. 월별: "2025년 12월"
                        new_cols = []
                        for d in pivot_df.columns:
                            dt = pd.to_datetime(d)
                            if gran == 'M':
                                new_cols.append(f"{dt.year}년 {dt.month}월")
                            elif gran == 'W':
                                week_num = dt.isocalendar()[1]
                                new_cols.append(f"{dt.month}/{dt.day}({week_num}W)")
                            else: # gran == 'D'
                                new_cols.append(f"{dt.month}/{dt.day}")
                        pivot_df.columns = new_cols
                        date_format_map = dict(zip(display_dates, new_cols))
                        
                        # 히트맵 컬러 스케일 설정 (동적 임계치 보정)
                        z_max = pivot_df.max().max()
                        z_max = max(z_max, 1.0) # 최소 100%까지는 표현
                        
                        # 동적 임계치 지점 계산
                        p_thresh = threshold / z_max if z_max > 0 else 0.8
                        p_50 = 0.5 / z_max if z_max > 0 else 0.5
                        
                        color_scale = [
                            [0, "#e8f5e9"],       # 0% : 연그린
                            [min(p_50, 0.99), "#fff9c4"],    # 50% : 연노랑
                            [max(0, p_thresh - 0.01), "#ffcc80"], # 임계치 직전 : 연주황
                            [min(p_thresh, 1.0), "#ff8a80"],    # 임계치 : 연빨강 (Key Threshold)
                            [1.0, "#e53935"]      # Max (100% or above) : 기본 빨강
                        ] if metric == 'rate' else "Viridis"

                        fig_hm = px.imshow(
                            pivot_df,
                            labels=dict(x="기간", y="동", color=metric_opt),
                            x=pivot_df.columns,
                            y=[f"{p}동" for p in pivot_df.index],
                            color_continuous_scale=color_scale,
                            zmin=0,
                            zmax=z_max,
                            aspect="auto"
                        )
                        
                        # [Visual] Hover Format & Cell Text
                        if metric == 'rate':
                            fig_hm.update_traces(
                                hovertemplate="기간: %{x}<br>동: %{y}<br>점유율: %{z:.1%}<extra></extra>",
                                texttemplate="<b>%{z:.0%}</b>", # 셀 위에 표시될 텍스트
                                textfont=dict(size=22, color="#000000") # 가독성을 위해 크고 검정색
                            )
                        else:
                            fig_hm.update_traces(
                                hovertemplate="기간: %{x}<br>동: %{y}<br>점유면적: %{z:,.0f}㎡<extra></extra>",
                                texttemplate="<b>%{z:,.0f}</b>",
                                textfont=dict(size=18, color="#000000")
                            )
                        
                        # 레이아웃 정밀 조정
                        colorbar_opts = dict(title=metric_opt)
                        if metric == 'rate':
                            colorbar_opts["tickformat"] = ".0%" # 1.0 -> 100% 변환
                        
                        fig_hm.update_layout(
                            title=dict(
                                text=f"동별 {metric_opt} 현황 <span style='font-size: 18px;'>(단위: {gran_opt}, {agg_opt})</span>",
                                font=dict(size=22)
                            ),
                            xaxis=dict(title=dict(text="시간 축", font=dict(size=18, color="#000000")), tickfont=dict(size=18, color="#000000")),
                            yaxis=dict(title=dict(text="생산 동", font=dict(size=18, color="#000000")), tickfont=dict(size=18, color="#000000")),
                            coloraxis_colorbar=dict(
                                title=dict(text=metric_opt, font=dict(size=16, color="#000000")),
                                tickfont=dict(size=15, color="#000000"),
                                **({"tickformat": ".0%"} if metric == 'rate' else {})
                            )
                        )
                        
                        # 80% 이상 별도 텍스트 오버레이 제거 (texttemplate으로 통합)

                        # --- [User Request] 히트맵 상단 현재 설정 요약 문구 추가 ---
                        clean_gran = gran_opt.split(' ')[0]
                        clean_agg = agg_opt.split(' ')[0]
                        
                        # 화면에 실제로 표시된 첫 번째/마지막 날짜를 추출하여 파란색 요약 문구에 반영
                        if display_dates:
                            actual_s_date = display_dates[0].strftime('%Y-%m-%d')
                            actual_e_date = display_dates[-1].strftime('%Y-%m-%d')
                        else:
                            actual_s_date = s_date
                            actual_e_date = e_date

                        # 히트맵의 가로 길이를 1/4 축소하기 위해 3:1 비율의 컬럼으로 분할
                        col_h1, col_h2 = st.columns([3, 1])
                        with col_h1:
                            st.markdown(f"""
                                <div style="
                                    background-color: rgba(0, 123, 255, 0.05); 
                                    border: 1px solid rgba(0, 123, 255, 0.2); 
                                    border-radius: 8px; 
                                    padding: 10px 15px; 
                                    margin-bottom: 20px; 
                                    color: #000000;
                                    font-size: 0.95rem;
                                ">
                                    💡 <b>{actual_s_date} ~ {actual_e_date}</b>, <b>{mode_opt}</b> 기준, 
                                    <b>{clean_gran}·{clean_agg}</b>으로 동별 <b>{metric_opt}</b>을 분석 중입니다.
                                </div>
                            """, unsafe_allow_html=True)
                            st.plotly_chart(fig_hm, width="stretch")
                        
                        # 추가 시각화 차트
                        st.subheader("📈 추가 시각화")
                        chart_type = st.radio("차트 유형", ["라인 차트", "바 차트"], horizontal=True)
                        
                        if chart_type == "라인 차트":
                            # 라인 차트
                            line_df = final_df.copy()
                            if gran == 'D':
                                val_col = 'OCC_RATE_D' if metric == 'rate' else 'OCC_AREA_D'
                            else:
                                val_col = f'OCC_RATE_{gran}{agg}' if metric == 'rate' else f'OCC_AREA_{gran}{agg}'
                            
                            # 선택한 날짜 개수만큼만 표시 (히트맵과 동일한 날짜 적용)
                            line_df = line_df[line_df['date'].isin(display_dates)].copy()
                            line_df['date'] = line_df['date'].map(date_format_map)
                            
                            fig_line = px.line(
                                line_df, 
                                x='date', 
                                y=val_col, 
                                color='plant',
                                title=f"동별 {metric_opt} 추이 (라인 차트)",
                                labels={'date': '날짜', val_col: metric_opt, 'plant': '동'}
                            )
                            
                            fig_line.update_layout(
                                title=dict(
                                    text=f"동별 {metric_opt} 추이 <span style='font-size: 14px;'>(라인 차트)</span>",
                                    font=dict(size=22)
                                ),
                                xaxis=dict(
                                    title=dict(text="날짜", font=dict(size=18, color="#000000")), 
                                    tickfont=dict(size=18, color="#000000")
                                ),
                                yaxis=dict(
                                    title=dict(text=metric_opt, font=dict(size=18, color="#000000")), 
                                    tickfont=dict(size=18, color="#000000")
                                ),
                                legend=dict(font=dict(size=18, color="#000000")),
                                hovermode="x unified"
                            )
                            
                            if metric == 'rate':
                                fig_line.update_layout(yaxis_tickformat=".0%")
                                # 임계치 가이드라인 추가
                                fig_line.add_hline(
                                    y=threshold, 
                                    line_dash="dash", 
                                    line_color="red", 
                                    annotation_text=f"임계치 ({int(threshold*100)}%)",
                                    annotation_position="top right"
                                )
                            
                            col_l1, col_l2 = st.columns([3, 1])
                            with col_l1:
                                st.plotly_chart(fig_line, width="stretch")
                        else:
                            # 바 차트
                            bar_df = final_df.copy()
                            if gran == 'D':
                                val_col = 'OCC_RATE_D' if metric == 'rate' else 'OCC_AREA_D'
                            else:
                                val_col = f'OCC_RATE_{gran}{agg}' if metric == 'rate' else f'OCC_AREA_{gran}{agg}'
                            
                            # 선택한 날짜 개수만큼만 표시 (히트맵과 동일한 날짜 적용)
                            bar_df = bar_df[bar_df['date'].isin(display_dates)].copy()
                            bar_df['date'] = bar_df['date'].map(date_format_map)
                            
                            # 바 차트를 그룹화하여 표시 (각 날짜에 대해 5개의 동이 명확히 나오도록)
                            # plant 컬럼이 숫자형(1~5)일 경우 색상이 연속형(Colorbar)으로 들어가 누적처럼 보이는 것을 방지하기 위해 str 형태로 변환
                            bar_df['plant_str'] = bar_df['plant'].astype(str) + '동'
                            
                            fig_bar = px.bar(
                                bar_df, 
                                x='date', 
                                y=val_col, 
                                color='plant_str',
                                barmode='group',
                                title=f"동별 {metric_opt} 추이 (바 차트)",
                                labels={'date': '날짜', val_col: metric_opt, 'plant_str': '동'},
                                category_orders={'plant_str': ['1동', '2동', '3동', '4동', '5동']}
                            )
                            
                            fig_bar.update_layout(
                                title=dict(
                                    text=f"동별 {metric_opt} 추이 <span style='font-size: 14px;'>(바 차트)</span>",
                                    font=dict(size=22)
                                ),
                                xaxis=dict(
                                    title=dict(text="날짜", font=dict(size=18, color="#000000")), 
                                    tickfont=dict(size=18, color="#000000")
                                ),
                                yaxis=dict(
                                    title=dict(text=metric_opt, font=dict(size=18, color="#000000")), 
                                    tickfont=dict(size=18, color="#000000")
                                ),
                                legend=dict(font=dict(size=18, color="#000000")),
                                hovermode="x unified"
                            )
                            
                            # color 파라미터가 'plant'로 설정되도록 조정
                            fig_bar.update_traces(marker=dict(line=dict(width=1, color='white')))
                            
                            if metric == 'rate':
                                fig_bar.update_layout(yaxis_tickformat=".0%")
                                # 임계치 가이드라인 추가
                                fig_bar.add_hline(
                                    y=threshold, 
                                    line_dash="dash", 
                                    line_color="red", 
                                    annotation_text=f"임계치 ({int(threshold*100)}%)",
                                    annotation_position="top right"
                                )
                            
                            col_b1, col_b2 = st.columns([3, 1])
                            with col_b1:
                                st.plotly_chart(fig_bar, width="stretch")
                        
                        # --- [User Request] 리스크 관련 3개 섹션 순서 변경 및 가로 배치 ---
                        st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
                        
                        risk_summary = results["risk_summary"].sort_values('recent_max_rate', ascending=False)
                        threshold_history = results["threshold_history"].sort_values('highest_rate', ascending=False)
                        
                        # 순서 변경: [동별 요약] [리스크 히스토리] [주요 과부하]
                        col_r1, col_r2, col_r3 = st.columns([1.2, 1.3, 1.1])

                        # 공통 스타일 정의
                        table_css = 'width: 100%; border-collapse: collapse; text-align: center; font-size: 0.85rem; color: #000000;'
                        th_style = 'background-color: rgba(255,255,255,0.05); border-bottom: 1px solid #555; padding: 6px 2px;'
                        td_style = 'border-bottom: 1px solid #444; padding: 5px 2px; vertical-align: middle;'

                        def make_progress_bar_html(val, color="#ef5350"):
                            pct = min(100, max(0, val * 100))
                            return f"""
                            <div style="display: flex; align-items: center; gap: 5px; justify-content: center;">
                                <div style="flex-grow: 1; background-color: #333; height: 6px; border-radius: 3px; overflow: hidden; min-width: 40px;">
                                    <div style="background-color: {color}; width: {pct}%; height: 100%;"></div>
                                </div>
                                <span style="font-size: 0.75rem; min-width: 25px;">{int(pct)}%</span>
                            </div>
                            """

                        with col_r1:
                            st.markdown("<p style='font-size: 1.0rem; font-weight: 700; margin-bottom: 8px;'>🗓️ 동별 요약 (최근 3M)</p>", unsafe_allow_html=True)
                            html_t2 = f'<table style="{table_css}"><thead><tr><th style="{th_style}">동</th><th style="{th_style}">Max</th><th style="{th_style}">Avg</th><th style="{th_style}">Peak</th></tr></thead><tbody>'
                            for _, row in risk_summary.iterrows():
                                bar = make_progress_bar_html(row['recent_max_rate'])
                                avg_str = f"{int(row['recent_avg_rate']*100)}%"
                                html_t2 += f'<tr><td style="{td_style}">{row["plant"]}동</td><td style="{td_style}">{bar}</td><td style="{td_style}">{avg_str}</td><td style="{td_style}">{row["peak_month"]}</td></tr>'
                            html_t2 += "</tbody></table>"
                            st.write(html_t2, unsafe_allow_html=True)

                        with col_r2:
                            st.markdown(f"<p style='font-size: 1.0rem; font-weight: 700; margin-bottom: 8px;'>🚩 리스크 히스토리 (최근 6M)</p>", unsafe_allow_html=True)
                            html_t3 = f'<table style="{table_css}"><thead><tr><th style="{th_style}">동</th><th style="{th_style}">{int(threshold*100)}%↑</th><th style="{th_style}">연속</th><th style="{th_style}">Peak</th><th style="{th_style}">Status</th></tr></thead><tbody>'
                            for _, row in threshold_history.iterrows():
                                bar = make_progress_bar_html(row['highest_rate'])
                                status_icon = "🔴" if "위험" in row["status"] else "🟡"
                                html_t3 += f'<tr><td style="{td_style}">{row["plant"]}동</td><td style="{td_style}">{row["over_threshold_days"]}</td><td style="{td_style}">{row["max_streak"]}</td><td style="{td_style}">{bar}</td><td style="{td_style}">{status_icon} {row["status"]}</td></tr>'
                            html_t3 += "</tbody></table>"
                            st.write(html_t3, unsafe_allow_html=True)

                        with col_r3:
                            st.markdown("<p style='font-size: 1.0rem; font-weight: 700; margin-bottom: 8px;'>⚠️ 주요 과부하 구간 (주의 요망)</p>", unsafe_allow_html=True)
                            if metric == 'rate':
                                risk_df = final_df[final_df[val_col] >= threshold].sort_values(by=val_col, ascending=False).head(5)
                                if not risk_df.empty:
                                    html_t1 = f'<table style="{table_css}"><thead><tr><th style="{th_style}">날짜</th><th style="{th_style}">동</th><th style="{th_style}">점유율</th></tr></thead><tbody>'
                                    for _, row in risk_df.iterrows():
                                        date_str = row['date'].strftime('%y-%m-%d')
                                        plant_str = f"{row['plant']}동"
                                        rate_str = f"{int(row[val_col]*100)}%"
                                        html_t1 += f'<tr><td style="{td_style}">{date_str}</td><td style="{td_style}">{plant_str}</td><td style="{td_style} font-weight: bold; color: #ff5252;">{rate_str}</td></tr>'
                                    html_t1 += "</tbody></table>"
                                    st.write(html_t1, unsafe_allow_html=True)
                                else: st.success("🎉 과부하 없음")



            except Exception as e:
                st.error(f"❌ 데이터 시각화 중 오류 발생: {e}")
                import traceback
                st.code(traceback.format_exc())
                
        # --- [User Request] 업로드 데이터 확인 문구를 최하단으로 이동 및 크기 조정 ---
        st.divider()
        st.markdown("<p style='font-size: 1.15rem; font-weight: 700; margin-bottom: 10px;'>🔍 업로드 데이터 확인 (전수 추출)</p>", unsafe_allow_html=True)
        # 사용자가 상세 요청한 항목 중심 표시 (순서 및 명칭 조정)
        cols_to_show = [
            'order_id', 'customer', 'model', 'qty', 'due_date', 
            'plant', 'area_m2_unit', 'production_status', 'start_in', 'end_out'
        ]
        # 실제 컬럼이 있는지 확인 후 필터링
        available_cols = [c for c in cols_to_show if c in full_processed.columns]
        
        # [Senior Logic] 전수 추출 뷰에서는 N행(계획)과 N+1행(실행) 페어를 모두 보여줌
        mask_display = full_processed['row_type'].str.contains('DATA', na=False)
        display_df = full_processed[mask_display][available_cols].copy() if not full_processed.empty else pd.DataFrame(columns=available_cols)
        
        # UI용 한글 명칭 매칭 (특수 기호 제거)
        column_labels = {
            'order_id': 'SEQ.', 'customer': '고객', 'model': 'MODEL1', 'qty': '수량',
            'due_date': '납기', 'plant': 'Plant', 'area_m2_unit': 'area_m2_unit',
            'production_status': '제작', 'start_in': '제작_1', 'end_out': '포장'
        }
        display_df = display_df.rename(columns=column_labels)
        
        # [Senior Logic] 데이터 타입 및 포맷 사전 정제
        # 1. 날짜에서 시간 제거 (날짜/글자 혼합 데이터 대응)
        def smart_date_format_bottom(val):
            if pd.isna(val): return ""
            s_val = str(val).strip()
            if s_val.lower() in ['nat', 'none', 'nan', '']: return ""
            
            try:
                # 이미 datetime 객체인 경우
                if isinstance(val, (pd.Timestamp, datetime)):
                    return val.strftime('%Y-%m-%d')
                
                # 문자열인 경우 변환 시도
                dt = pd.to_datetime(val, errors='coerce')
                if pd.notna(dt) and not isinstance(val, str):
                    # 원래 숫자였는데 날짜로 변환된 경우 등
                    return dt.strftime('%Y-%m-%d')
                elif pd.notna(dt) and isinstance(val, str):
                    # "2024-12-04" 처럼 날짜 형식의 문자열인 경우
                    # 단, "1", "2" 처럼 너무 짧은 숫자는 날짜로 오인될 수 있으므로 체크
                    if len(s_val) >= 8: # YYYYMMDD 이상
                        return dt.strftime('%Y-%m-%d')
                
                return s_val # 변환 실패하거나 일반 글자인 경우 원본 반환
            except:
                return s_val

        for col in ['납기', '제작', '제작_1', '포장']:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(smart_date_format_bottom)

        # 2. 숫자형 데이터 소수점 제거 (정수형 표시)
        # 제작 열은 혼합형이므로 여기서 제외하고 1번 루프에서 처리
        num_cols = ['수량', '공장(동)', 'area_m2_unit']
        for col in num_cols:
            if col in display_df.columns:
                display_df[col] = pd.to_numeric(display_df[col], errors='coerce').fillna(0).astype(int)

        # 1. 데이터 전처리 (포맷팅)
        html_df = display_df.copy()
        for col in num_cols:
            if col in html_df.columns:
                html_df[col] = pd.to_numeric(html_df[col], errors='coerce').fillna(0).astype(int).map('{:,d}'.format)
        
        # 2. HTML 생성
        styles_bottom = """
        <style>
            .custom-table-container {
                width: 100%;
                overflow-x: auto;
                max-height: 800px;
                overflow-y: auto;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px;
            }
            .custom-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 13px;
                color: #000000;
            }
            .custom-table th {
                background-color: rgba(255,255,255,0.05);
                font-weight: bold !important;
                text-align: center !important;
                vertical-align: middle;
                padding: 12px 8px;
                border: 1px solid #444;
                position: sticky;
                top: 0;
                z-index: 10;
            }
            .custom-table td {
                text-align: center !important;
                vertical-align: middle;
                padding: 8px;
                border: 1px solid #444;
                background-color: transparent;
            }
            .custom-table tr:hover td {
                background-color: rgba(255,255,255,0.02);
            }
        </style>
        """
        
        table_html_bottom = f'<div class="custom-table-container">{styles_bottom}<table class="custom-table">'
        table_html_bottom += "<thead><tr>"
        for col in html_df.columns:
            table_html_bottom += f"<th>{col}</th>"
        table_html_bottom += "</tr></thead><tbody>"
        
        for _, row in html_df.iterrows():
            table_html_bottom += "<tr>"
            for val in row:
                s_val = str(val).strip()
                display_val = "" if pd.isna(val) or s_val.lower() in ['nat', 'none', 'nan', ''] else s_val
                table_html_bottom += f"<td>{display_val}</td>"
            table_html_bottom += "</tr>"
        table_html_bottom += "</tbody></table></div>"
        
        st.markdown(table_html_bottom, unsafe_allow_html=True)

        # --- [User Request] 종합 리스크 통합 리포트 추가 (맨 밑에 1줄로 통합) ---
        st.divider()
        st.markdown(f"<p style='font-size: 1.25rem; font-weight: 700; color: #000000; margin-bottom: 15px;'>📋 종합 리스크 통합 리포트 (통계 요약)</p>", unsafe_allow_html=True)
        try:
            # 리스크 요약과 히스토리 사이드-바이-사이드 통합 (1줄 레포트용 데이터 준비)
            combined_risk = pd.merge(risk_summary, threshold_history.drop(columns=['status']), on='plant')
            
            # HTML 테이블 스타일 정의 (더 넓고 가독성 있게)
            html_rep = f'<table style="width: 100%; border-collapse: collapse; text-align: center; font-size: 0.9rem; color: #000000; border: 1px solid #ddd;">'
            html_rep += f'<thead><tr style="background-color: #f8f9fa; border-bottom: 2px solid #333;">'
            html_rep += f'<th style="{th_style}">공장(동)</th><th style="{th_style}">최근Max</th><th style="{th_style}">최근Avg</th>'
            html_rep += f'<th style="{th_style}">Peak Month</th><th style="{th_style}">{int(threshold*100)}%초과(일)</th>'
            html_rep += f'<th style="{th_style}">최대연속(일)</th><th style="{th_style}">최고점유율</th>'
            html_rep += '</tr></thead><tbody>'
            
            for _, row in combined_risk.iterrows():
                # 프로그레스 바 생성
                max_bar = make_progress_bar_html(row['recent_max_rate'])
                high_bar = make_progress_bar_html(row['highest_rate'])
                avg_str = f"{int(row['recent_avg_rate']*100)}%"
                
                html_rep += f'<tr>'
                html_rep += f'<td style="{td_style}; font-weight: 700;">{row["plant"]}동</td>'
                html_rep += f'<td style="{td_style}">{max_bar}</td>'
                html_rep += f'<td style="{td_style}">{avg_str}</td>'
                html_rep += f'<td style="{td_style}">{row["peak_month"]}</td>'
                html_rep += f'<td style="{td_style}">{row["over_threshold_days"]}</td>'
                html_rep += f'<td style="{td_style}">{row["max_streak"]}</td>'
                html_rep += f'<td style="{td_style}">{high_bar}</td>'
                html_rep += '</tr>'
            
            html_rep += "</tbody></table>"
            st.write(html_rep, unsafe_allow_html=True)
        except: pass
    else:
        st.info("데이터를 업로드하거나 샘플 데이터를 생성해 주세요.")

with tab2:
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    
    # 세션 상태 초기화
    if "virtual_orders" not in st.session_state:
        st.session_state["virtual_orders"] = []
    
    # 가상 수주 입력 폼
    st.subheader("가상 수주 입력")
    
    # 기존 데이터에서 고객사 및 모델 리스트 추출 (데이터가 있을 경우)
    customer_list = ["가상고객"]
    model_list = ["MODEL-X"]
    
    if st.session_state.get("orders_data") is not None and not st.session_state["orders_data"].empty:
        if 'customer' in st.session_state["orders_data"].columns:
            customer_list = sorted([str(x) for x in st.session_state["orders_data"]['customer'].dropna().unique()]) + ["[신규 직접 입력]"]
        else:
            customer_list = ["기본고객1", "기본고객2", "[신규 직접 입력]"]
            
        if 'model' in st.session_state["orders_data"].columns:
            model_list = sorted([str(x) for x in st.session_state["orders_data"]['model'].dropna().unique()]) + ["[신규 직접 입력]"]

    with st.form("virtual_order_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            v_plant = st.selectbox("진행동", [1,2,3,4,5])
            v_qty = st.number_input("수량", min_value=1, value=1)
        
        with col2:
            v_area = st.number_input("제품 면적(m2)", min_value=0.1, value=1.0, step=0.1)
            v_start = st.date_input("시작일", datetime.now())
        
        with col3:
            v_model_sel = st.selectbox("모델명 선택", model_list)
            v_end = st.date_input("종료일", datetime.now() + pd.Timedelta(days=7))
            
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            v_customer_sel = st.selectbox("고객명 선택", customer_list)
        
        with col_c2:
             v_model_new = st.text_input("새 모델명 (직접 입력 시)", placeholder="모델명 입력")
        
        v_customer_new = st.text_input("새 고객명 (직접 입력 시)", placeholder="고객명 입력")
        
        submit = st.form_submit_button("시뮬레이션 시나리오에 추가")
        
        if submit:
            v_customer = v_customer_new if v_customer_sel == "[신규 직접 입력]" and v_customer_new else v_customer_sel
            v_model = v_model_new if v_model_sel == "[신규 직접 입력]" and v_model_new else v_model_sel
            
            # 가상 주문 추가
            new_order = {
                "order_id": f"VIRTUAL-{len(st.session_state['virtual_orders']) + 1}",
                "customer": v_customer,
                "model": v_model,
                "qty": v_qty,
                "plant": v_plant,
                "area_m2_unit": v_area,
                "start_in": v_start,
                "end_out": v_end,
                "data_mode": "plan",
                "is_estimated": False,
                "row_type": "SCENARIO"
            }
            
            st.session_state["virtual_orders"].append(new_order)
            st.success("시뮬레이션 시나리오에 추가되었습니다!")
    
    # 시나리오 목록
    if st.session_state["virtual_orders"]:
        st.subheader("시나리오 목록")
        
        # 시나리오 테이블
        scenario_df = pd.DataFrame(st.session_state["virtual_orders"])
        st.dataframe(scenario_df[["order_id", "customer", "model", "qty", "plant", "area_m2_unit", "start_in", "end_out"]], 
                     width="stretch")
        
        # 시나리오 저장 및 불러오기
        col1, col2 = st.columns(2)
        with col1:
            scenario_name = st.text_input("시나리오 이름", "새 시나리오")
            if st.button("시나리오 저장"):
                if scenario_name:
                    # 시나리오 저장
                    scenario_data = {
                        "name": scenario_name,
                        "orders": st.session_state["virtual_orders"],
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # JSON 파일로 저장
                    filename = f"scenario_{scenario_name.replace(' ', '_')}.json"
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(scenario_data, f, ensure_ascii=False, indent=2, default=str)
                    
                    st.success(f"시나리오 '{scenario_name}'이(가) 저장되었습니다.")
                else:
                    st.warning("시나리오 이름을 입력해주세요.")
        
        with col2:
            # 저장된 시나리오 목록
            scenario_files = [f for f in os.listdir() if f.startswith("scenario_") and f.endswith(".json")]
            if scenario_files:
                selected_scenario = st.selectbox("불러올 시나리오", scenario_files)
                if st.button("시나리오 불러오기"):
                    try:
                        with open(selected_scenario, 'r', encoding='utf-8') as f:
                            scenario_data = json.load(f)
                        
                        st.session_state["virtual_orders"] = scenario_data["orders"]
                        st.success(f"시나리오 '{scenario_data['name']}'이(가) 불러와졌습니다.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"시나리오 불러오기 실패: {str(e)}")
            else:
                st.info("저장된 시나리오가 없습니다.")
        
        # 시나리오 실행
        if st.button("시뮬레이션 실행", type="primary"):
            with st.spinner("시뮬레이션 중..."):
                # 데이터 검증
                validator = DataValidator()
                valid_orders, _, _ = validator.validate_orders(st.session_state["orders_data"])
                clean_capa, _ = validator.validate_capacity(st.session_state["capa_data"])
                
                if valid_orders.empty:
                    st.warning("유효한 주문 데이터가 없습니다. 데이터를 확인해주세요.")
                else:
                    # 시나리오 엔진 초기화
                    from src.scenario_engine import ScenarioEngine
                    scenario_engine = ScenarioEngine(valid_orders, clean_capa)
                    scenario_engine.load_virtual_orders(st.session_state["virtual_orders"])
                    
                    # 시뮬레이션 실행을 위한 동적 날짜 범위 산출
                    v_start_dates = [pd.to_datetime(vo['start_in']).date() for vo in st.session_state["virtual_orders"]]
                    v_end_dates = [pd.to_datetime(vo['end_out']).date() for vo in st.session_state["virtual_orders"]]
                    
                    if v_start_dates and v_end_dates:
                        min_v_start = min(v_start_dates)
                        max_v_end = max(v_end_dates)
                        # 분석 시작일/종료일과 가상 주문의 날짜 중 더 넓은 범위 선택 (사용자 가시성 확보)
                        base_s_date = st.session_state.get("analysis_start", datetime.now().date())
                        base_e_date = st.session_state.get("analysis_end", datetime.now().date() + pd.Timedelta(days=90))
                        
                        # 시뮬레이션 집중 기간 전후로 7일간의 여유 마진 추가
                        margin = pd.Timedelta(days=7)
                        s_date = min(base_s_date, min_v_start - margin)
                        e_date = max(base_e_date, max_v_end + margin)
                    else:
                        s_date = st.session_state.get("analysis_start", datetime.now().date())
                        e_date = st.session_state.get("analysis_end", datetime.now().date() + pd.Timedelta(days=90))
                    
                    results = scenario_engine.simulate(
                        start_date=s_date,
                        end_date=e_date,
                        mode='plan',
                        granularity='D',
                        aggregation='MAX'
                    )
                    
                    base_result = results["base"]
                    sim_result = results["simulation"]
                    delta_df = results["delta"]
                    
                    if sim_result["final_df"].empty:
                        st.warning("시뮬레이션 결과가 없습니다.")
                    else:
                        # 시뮬레이션 결과 시각화
                        st.subheader("시뮬레이션 결과")
                        
                        # [Visual Logic] 히트맵과 동일한 X축 날짜 필터링 적용 (주말/공휴일 제거)
                        valid_dates = [d for d in delta_df.columns if d.weekday() < 5]
                        holidays = [
                            "2024-01-01", "2024-02-09", "2024-02-12", "2024-03-01", "2024-04-10", "2024-05-01", "2024-05-06", "2024-05-15", "2024-06-06", "2024-08-15", "2024-09-16", "2024-09-17", "2024-09-18", "2024-10-03", "2024-10-09", "2024-12-25",
                            "2025-01-01", "2025-01-27", "2025-01-28", "2025-01-29", "2025-01-30", "2025-03-03", "2025-05-01", "2025-05-05", "2025-05-06", "2025-06-06", "2025-08-15", "2025-10-03", "2025-10-06", "2025-10-07", "2025-10-08", "2025-10-09", "2025-12-25",
                            "2026-01-01", "2026-02-16", "2026-02-17", "2026-02-18", "2026-03-02", "2026-05-01", "2026-05-05", "2026-05-25", "2026-06-06", "2026-08-17", "2026-09-23", "2026-09-24", "2026-09-25", "2026-10-05", "2026-10-09", "2026-12-25",
                            "2027-01-01", "2027-02-05", "2027-02-06", "2027-02-07"
                        ]
                        valid_dates = [d for d in valid_dates if str(d.date()) not in holidays]
                        
                        # [Visual Logic] X축 라벨 포맷 변경 (MM/DD일)
                        new_cols = []
                        for d in valid_dates:
                            dt = pd.to_datetime(d)
                            new_cols.append(f"{dt.month}/{dt.day}일")
                        
                        date_format_map = dict(zip(valid_dates, new_cols))
                        
                        # 변화가 있는 공장만 필터링 (불필요한 전체 라인 표시 방지)
                        affected_plants = []
                        for plant in delta_df.index:
                            if delta_df.loc[plant].sum() != 0:
                                affected_plants.append(plant)
                                
                        if not affected_plants:
                            affected_plants = delta_df.index.tolist() # 변화가 없다면 모두 표시
                        
                        # 기준선과 시뮬레이션 결과 비교
                        fig_compare = go.Figure()
                        
                        # 기준선 데이터
                        base_final = base_result["final_df"]
                        base_final = base_final[base_final['date'].isin(valid_dates)].copy()
                        base_final['date_str'] = base_final['date'].map(date_format_map)
                        
                        # 시뮬레이션 데이터
                        sim_final = sim_result["final_df"]
                        sim_final = sim_final[sim_final['date'].isin(valid_dates)].copy()
                        sim_final['date_str'] = sim_final['date'].map(date_format_map)
                        
                        for plant in affected_plants:
                            plant_base = base_final[base_final['plant'] == plant]
                            fig_compare.add_trace(go.Scatter(
                                x=plant_base['date_str'],
                                y=plant_base['OCC_RATE_D'],
                                mode='lines',
                                name=f'{plant}동 (기준)',
                                line=dict(width=2)
                            ))
                            
                            plant_sim = sim_final[sim_final['plant'] == plant]
                            # 데이터가 다른 부분만 점선으로 표시 (시뮬레이션에 따른 차이 강조)
                            if not plant_base.empty and not plant_sim.empty:
                                if not plant_base['OCC_RATE_D'].equals(plant_sim['OCC_RATE_D']):
                                    fig_compare.add_trace(go.Scatter(
                                        x=plant_sim['date_str'],
                                        y=plant_sim['OCC_RATE_D'],
                                        mode='lines',
                                        name=f'{plant}동 (시뮬레이션)',
                                        line=dict(width=2, dash='dash')
                                    ))
                        
                        # 임계치 라인
                        fig_compare.add_hline(
                            y=0.8, 
                            line_dash="dot", 
                            line_color="red",
                            annotation_text="위험 임계치 (80%)"
                        )
                        
                        fig_compare.update_layout(
                            title=f"기준선 vs 시뮬레이션 결과 비교 (수정된 {len(affected_plants)}개 동)",
                            xaxis_title="날짜",
                            yaxis_title="점유율",
                            yaxis_tickformat=".0%",
                            hovermode="x unified"
                        )
                        
                        st.plotly_chart(fig_compare, width="stretch")
                        
                        # 변화량 히트맵
                        delta_df_filtered = delta_df[valid_dates].copy()
                        delta_df_filtered.columns = new_cols
                        
                        if not delta_df_filtered.empty:
                            st.subheader("점유율 변화량")
                            
                            # 히트맵 생성 (RdBu_r 으로 변경하여 상승시 붉은색 표시)
                            # color_continuous_midpoint=0을 설정하여 변화가 없는 0일때 중간색(White)이 되도록 함
                            # 변화량이 너무 작은 경우(예: 0.001 등) 색상이 과도하게 진해지는 현상을 막기 위해 zmax/zmin 고정
                            z_max_val = max(abs(delta_df_filtered.max().max()), abs(delta_df_filtered.min().min()))
                            z_limit = max(z_max_val, 0.05) # 최소 5% 범위 확보
                            
                            fig_delta = px.imshow(
                                delta_df_filtered,
                                labels=dict(x="날짜", y="동", color="변화량"),
                                x=delta_df_filtered.columns,
                                y=[f"{p}동" for p in delta_df_filtered.index],
                                color_continuous_scale="RdBu_r",
                                aspect="auto",
                                color_continuous_midpoint=0,
                                zmin=-z_limit,
                                zmax=z_limit
                            )
                            
                            fig_delta.update_traces(
                                hovertemplate="기간: %{x}<br>동: %{y}<br>점유율 변화: %{z:+.1%}<extra></extra>",
                                texttemplate="%{z:+.1%}"
                            )
                            
                            # 컬러바 퍼센트 형식 지정
                            fig_delta.update_layout(
                                title="시뮬레이션에 따른 점유율 변화량 (기준선 대비)",
                                xaxis_title="날짜",
                                yaxis_title="생산 동",
                                coloraxis_colorbar=dict(tickformat="+.1%")
                            )
                            
                            st.plotly_chart(fig_delta, width="stretch")
        
        # 시나리오 초기화 버튼
        if st.button("시나리오 초기화"):
            st.session_state["virtual_orders"] = []
            st.rerun()
    else:
        st.info("시뮬레이션을 위해 가상 수주를 추가해주세요.")

with tab3:
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    
    # 데이터 존재 여부 확인
    if "orders_data" not in st.session_state or "capa_data" not in st.session_state:
        st.info("예측을 위해 먼저 데이터를 업로드해주세요.")
    elif st.session_state["orders_data"] is None or st.session_state["capa_data"] is None:
        st.info("예측을 위해 먼저 데이터를 업로드해주세요.")
    else:
        # 예측 설정
        st.subheader("예측 설정")
        col1, col2 = st.columns(2)
        
        with col1:
            horizon = st.slider("예측 기간 (주차)", 4, 52, 12, help="몇 주 동안 예측할지 선택하세요.")
        
        with col2:
            threshold = st.slider("위험 임계치 (%)", 50, 100, 80) / 100
            
        st.info("💡 예측 모델(AI)은 '선형 회귀, 이동 평균, ARIMA' 중 공장별로 가장 보수적인(위험을 높게 예측하는) 시나리오를 탐색하여 자동으로 선별합니다.")
        
        # 예측 실행 버튼
        if st.button("예측 실행", type="primary"):
            with st.spinner("예측 중..."):
                # 데이터 검증
                validator = DataValidator()
                valid_orders, _, _ = validator.validate_orders(st.session_state["orders_data"])
                clean_capa, _ = validator.validate_capacity(st.session_state["capa_data"])
                
                if valid_orders.empty:
                    st.warning("유효한 주문 데이터가 없습니다. 데이터를 확인해주세요.")
                else:
                    # 점유율 계산 (주차별 데이터로 변경)
                    engine = OccupancyEngine()
                    results = engine.calculate_daily_occupancy(
                        valid_orders, clean_capa,
                        mode='plan', include_estimated=True,
                        granularity='W', aggregation='MAX'
                    )
                    
                    final_df = results["final_df"]
                    
                    if final_df.empty:
                        st.warning("점유율 데이터가 없습니다.")
                    else:
                        # WMAX 컬럼을 forecast_engine이 인식할 수 있도록 컬럼명 매핑
                        val_col = 'OCC_RATE_WMAX'
                        daily_df = final_df[['date', 'plant', val_col]].copy()
                        daily_df.rename(columns={val_col: 'occupancy_rate'}, inplace=True)
                        
                        # 다중 모델 예측 수행 및 최악의(가장 높은 점유율) 시나리오 자동 선택
                        forecast_engine = ForecastEngine()
                        
                        best_forecast_dfs = []
                        all_metrics = {}
                        model_types = ["linear", "moving_average", "arima"]
                        
                        for plant in daily_df['plant'].unique():
                            plant_data = daily_df[daily_df['plant'] == plant]
                            plant_max_rate = -1
                            plant_best_df = None
                            plant_best_metric = None
                            
                            for m_type in model_types:
                                params = ForecastParams(horizon_periods=horizon, threshold=threshold, model_type=m_type, period_days=7)
                                m_result = forecast_engine.forecast_occupancy(plant_data, params)
                                f_df = m_result["forecast"]
                                
                                if not f_df.empty:
                                    max_rate = f_df['forecast_occupancy_rate'].max()
                                    if max_rate > plant_max_rate:
                                        plant_max_rate = max_rate
                                        plant_best_df = f_df.copy()
                                        plant_best_df['selected_model'] = m_type # 어떤 모델이 선택되었는지 마킹
                                        plant_best_metric = m_result["metrics"]
                            
                            if plant_best_df is not None:
                                best_forecast_dfs.append(plant_best_df)
                                if plant_best_metric:
                                    all_metrics.update(plant_best_metric)
                        
                        forecast_df = pd.concat(best_forecast_dfs) if best_forecast_dfs else pd.DataFrame()
                        metrics = all_metrics
                        
                        if forecast_df.empty:
                            st.warning("예측 결과가 없습니다.")
                        else:
                            # 예측 결과 시각화
                            st.subheader("예측 결과")
                            
                            from plotly.subplots import make_subplots
                            plants = sorted(daily_df['plant'].unique())
                            
                            # 서브플롯 생성 (공장 수만큼 세로로 배치)
                            fig_forecast = make_subplots(
                                rows=len(plants), cols=1, 
                                shared_xaxes=True, 
                                vertical_spacing=0.06,
                                subplot_titles=[f"🏢 {p}동 주차별 예측 현황" for p in plants]
                            )
                            
                            # 실제 데이터 시각화 범위를 최근 90일(12주)로 확대
                            recent_actual = daily_df[daily_df['date'] >= (daily_df['date'].max() - pd.Timedelta(days=90))]
                            
                            # 각 식물별로 서브플롯에 데이터 추가
                            for i, plant in enumerate(plants):
                                row = i + 1
                                
                                # 해당 동 데이터 필터링
                                plant_actual = recent_actual[recent_actual['plant'] == plant]
                                plant_forecast = forecast_df[forecast_df['plant'] == plant]
                                
                                # 1. 실제 데이터 (막대 그래프)
                                fig_forecast.add_trace(go.Bar(
                                    x=plant_actual['date'],
                                    y=plant_actual['occupancy_rate'],
                                    name='실제 (과거)',
                                    marker_color='#5A9BD5', # 파란색 톤
                                    opacity=0.7,
                                    showlegend=(i == 0) # 범례는 첫 번째만 표시
                                ), row=row, col=1)
                                
                                # 2. 예측 데이터 (꺾은선 그래프)
                                if not plant_forecast.empty:
                                    s_model = plant_forecast['selected_model'].iloc[0] if 'selected_model' in plant_forecast.columns else "auto"
                                    model_name_kr = "선형 회귀" if s_model == "linear" else "이동 평균" if s_model == "moving_average" else "ARIMA"
                                    
                                    # 과거와 예측 데이터의 자연스러운 연결을 위해 첫 점 이어주기
                                    plot_forecast = pd.DataFrame()
                                    if not plant_actual.empty:
                                        last_actual = pd.DataFrame({
                                            'date': [plant_actual['date'].max()],
                                            'forecast_occupancy_rate': [plant_actual['occupancy_rate'].iloc[-1]]
                                        })
                                        plot_forecast = pd.concat([last_actual, plant_forecast[['date', 'forecast_occupancy_rate']]])
                                    else:
                                        plot_forecast = plant_forecast
                                        
                                    fig_forecast.add_trace(go.Scatter(
                                        x=plot_forecast['date'],
                                        y=plot_forecast['forecast_occupancy_rate'],
                                        mode='lines+markers',
                                        name=f'자동 예측 ({model_name_kr})',
                                        line=dict(dash='dash', width=3, color='#ED7D31'), # 오렌지색 톤
                                        marker=dict(size=8, symbol='diamond'),
                                        showlegend=(i == 0)
                                    ), row=row, col=1)
                                
                                # 3. 임계치 라인
                                fig_forecast.add_hline(
                                    y=threshold, 
                                    line_dash="dot", 
                                    line_color="#C00000",
                                    annotation_text=f"위험 ({threshold*100:.0f}%)",
                                    row=row, col=1
                                )
                                
                                # Y축 눈금 포맷팅
                                fig_forecast.update_yaxes(
                                    tickformat=".0%", 
                                    range=[0, max(1.1, threshold*1.1)], 
                                    row=row, col=1
                                )
                            
                            # 전체 레이아웃 설정
                            fig_forecast.update_layout(
                                height=230 * len(plants), # 각 동당 충분한 높이
                                hovermode="x unified",
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                            )
                            fig_forecast.update_xaxes(title_text="주간(Week) 날짜", row=len(plants), col=1)
                            
                            st.plotly_chart(fig_forecast, width="stretch")
                            
                            # 위험 기간 식별
                            risk_periods = forecast_engine.evaluate_risk_periods(forecast_df, threshold)
                            
                            if not risk_periods.empty:
                                st.subheader("⚠️ 예측된 위험 기간")
                                st.write("다음 기간에 점유율이 위험 임계치를 초과할 것으로 예측됩니다:")
                                
                                # 위험 기간 테이블
                                risk_summary = risk_periods.groupby('plant').agg({
                                    'date': ['min', 'max', 'count'],
                                    'forecast_occupancy_rate': 'max'
                                }).reset_index()
                                
                                risk_summary.columns = ['동', '시작일', '종료일', '연속일수', '최대점유율']
                                risk_summary['시작일'] = risk_summary['시작일'].dt.strftime('%Y-%m-%d')
                                risk_summary['종료일'] = risk_summary['종료일'].dt.strftime('%Y-%m-%d')
                                risk_summary['최대점유율'] = risk_summary['최대점유율'].apply(lambda x: f"{x:.1%}")
                                
                                st.dataframe(risk_summary, width="stretch")
                            else:
                                st.success("예측 기간 내에 위험 임계치를 초과하는 기간이 없습니다.")
                            
                            # 모델 성능 메트릭
                            if metrics:
                                st.subheader("모델 성능")
                                metrics_df = pd.DataFrame([
                                    {"동": k.replace("plant_", ""), 
                                     "MAE": v.get("mae", "N/A"), 
                                     "RMSE": v.get("rmse", "N/A")}
                                    for k, v in metrics.items()
                                ])
                                st.dataframe(metrics_df, width="stretch")

with tab4:
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    st.info("🧪 **실험실: 히트맵 드릴다운(Drill-down) 테스트**\n\n히트맵의 특정 셀을 클릭하거나 아래의 메뉴에서 직접 날짜/동을 선택하여 상세 오더를 확인해 보세요.")
    
    

    # 세션 상태 초기화
    if "drill_date_idx" not in st.session_state:
        st.session_state["drill_date_idx"] = 0
    if "drill_plant_idx" not in st.session_state:
        st.session_state["drill_plant_idx"] = 0

    # 데이터 존재 여부 확인
    if "orders_data" not in st.session_state or "capa_data" not in st.session_state:
        st.warning("분석을 위해 먼저 데이터를 업로드해주세요.")
    elif st.session_state["orders_data"] is None or st.session_state["capa_data"] is None:
        st.warning("분석을 위해 먼저 데이터를 업로드해주세요.")
    else:

        # 내부 분석 로직 수행 (Tab 1 기반)
        validator = DataValidator()
        valid_orders, _, _ = validator.validate_orders(st.session_state["orders_data"])
        clean_capa, _ = validator.validate_capacity(st.session_state["capa_data"])
        
        s_date = st.session_state.get("analysis_start", date(2026, 3, 30))
        e_date = st.session_state.get("analysis_end", date(2026, 6, 30))
        threshold = st.session_state.get("saturation_threshold", 80) / 100
        date_count = st.session_state.get("date_count", 6)
        
        engine = OccupancyEngine()
        results = engine.calculate_daily_occupancy(
            valid_orders, clean_capa,
            start_date=s_date, end_date=e_date,
            mode='plan', include_estimated=True,
            granularity='W', aggregation='AVG',
            threshold=threshold
        )
        final_df = results["final_df"]
        
        if not final_df.empty:
            # 피벗 및 필터링
            pivot_df = final_df.pivot(index='plant', columns='date', values='OCC_RATE_WAVG')
            
            # 주차별 데이터 상위 N개 주차만 표시
            if len(pivot_df.columns) > date_count:
                pivot_df = pivot_df.iloc[:, :date_count]
            
            display_dates = pivot_df.columns.tolist()
            # X축 라벨 형식 변경: M/D(NW) -> 예: 3/30(14W)
            new_cols = [f"{d.month}/{d.day}({d.isocalendar()[1]}W)" for d in pivot_df.columns]
            rev_date_map = dict(zip(new_cols, display_dates))
            pivot_df.columns = new_cols
            
            plants_list = [f"{p}동" for p in pivot_df.index]

            # [Selection Logic] 이전 실행의 클릭 데이터를 확인하여 상위 위젯과 동기화
            if "heatmap_test" in st.session_state:
                event_data = st.session_state["heatmap_test"]
                points = []
                # SelectionEvent 객체 또는 딕셔너리 대응
                if hasattr(event_data, "selection"):
                    points = event_data.selection.get("points", [])
                elif isinstance(event_data, dict) and "selection" in event_data:
                    points = event_data["selection"].get("points", [])
                
                if points:
                    point = points[0]
                    # Plotly 반환값(raw_x, raw_y)이 Label(문자열)이거나 Index(숫자)인 경우 모두 대응
                    raw_x = point.get("x")
                    raw_y = point.get("y")
                    
                    # 1. x(날짜) 매칭 로직
                    new_sel_x = None
                    if isinstance(raw_x, (int, float)): # Index로 넘어온 경우
                        idx = int(raw_x)
                        if 0 <= idx < len(new_cols):
                            new_sel_x = new_cols[idx]
                    else: # Label 문자열로 넘어온 경우
                        s_raw_x = str(raw_x).strip()
                        if s_raw_x in new_cols:
                            new_sel_x = s_raw_x
                        else:
                            # 부분 일치 검색 (방어적)
                            for col in new_cols:
                                if s_raw_x in col or col in s_raw_x:
                                    new_sel_x = col
                                    break
                    
                    # 2. y(공장) 매칭 로직
                    new_sel_y = None
                    if isinstance(raw_y, (int, float)): # Index로 넘어온 경우
                        idx = int(raw_y)
                        if 0 <= idx < len(plants_list):
                            new_sel_y = plants_list[idx]
                    else: # Label 문자열로 넘어온 경우
                        s_raw_y = str(raw_y).strip()
                        if s_raw_y in plants_list:
                            new_sel_y = s_raw_y
                        else:
                            for p in plants_list:
                                if s_raw_y in p or p in s_raw_y:
                                    new_sel_y = p
                                    break

                    if new_sel_x and new_sel_y:
                        click_sig = f"{new_sel_x}_{new_sel_y}"
                        # 새로운 클릭 시그니처 발생 시에만 세션 상태 동기화 및 재실행
                        if st.session_state.get("last_heatmap_click") != click_sig:
                            st.session_state["sel_date_widget"] = new_sel_x
                            st.session_state["sel_plant_widget"] = new_sel_y
                            st.session_state["last_heatmap_click"] = click_sig
                            st.toast(f"📍 {new_sel_y}, {new_sel_x} 선택됨", icon="✅")
                            st.rerun()
                else:
                    # 선택이 해제된 경우 시그니처 초기화
                    if st.session_state.get("last_heatmap_click") is not None:
                        st.session_state["last_heatmap_click"] = None
                        st.rerun()

            # --- 보조 필터 UI ---
            st.markdown("#### 🔎 상세 조회 조건 (히트맵 클릭 또는 수동 선택)")
            f_col1, f_col2, f_col3 = st.columns([1, 1, 2])
            
            with f_col1:
                sel_date_label = st.selectbox("📅 날짜 선택", options=new_cols, key="sel_date_widget")
            with f_col2:
                sel_plant_label = st.selectbox("🏢 생산 동 선택", options=plants_list, key="sel_plant_widget")
            
            # --- [CRITICAL FIX] 완전한 클릭 지원을 위한 단일 Scatter 기반 가짜 히트맵 복원 ---
            # Streamlit의 px.imshow(Heatmap)는 브라우저 이벤트에서 click 지점을 전혀 반환하지 않는 고질적 버그가 있습니다.
            # 오버레이 방식조차 무시되므로, 가장 확실하게 클릭이 작동하던 "순수 Scatter 기반의 가짜 히트맵" 방식으로 돌아갑니다.
            # 단, 이전에 지적된 "색상이 안 예쁘다/히트맵 같지 않다"는 문제를 극복하기 위해 px.imshow와 동일한 완벽한 그라데이션 컬러 매핑 기능을 자체 구현했습니다.
            
            fig_test = go.Figure()
            
            x_data = []
            y_data = []
            z_data = []
            color_data = []
            text_data = []
            
            z_max = pivot_df.max().max()
            z_max = max(z_max, 1.0)
            p_thresh = threshold / z_max if z_max > 0 else 0.8
            p_50 = 0.5 / z_max if z_max > 0 else 0.5
            
            color_scale = [
                [0.0, "#e8f5e9"],
                [min(p_50, 0.99), "#fff9c4"],
                [max(0, p_thresh - 0.01), "#ffcc80"],
                [min(p_thresh, 1.0), "#ff8a80"],
                [1.0, "#e53935"]
            ]
            
            # --- 색상 보간(Interpolation) 알고리즘 ---
            def hex_to_rgb(h):
                return tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

            def rgb_to_hex(r, g, b):
                return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

            def get_interpolated_color(val):
                p = val / z_max if z_max > 0 else 0
                p = min(max(p, 0.0), 1.0)
                for i in range(len(color_scale)-1):
                    p1, c1 = color_scale[i]
                    p2, c2 = color_scale[i+1]
                    if p1 <= p <= p2:
                        if p1 == p2:
                            return c2
                        ratio = (p - p1) / (p2 - p1)
                        rgb1, rgb2 = hex_to_rgb(c1), hex_to_rgb(c2)
                        r = rgb1[0] + (rgb2[0] - rgb1[0]) * ratio
                        g = rgb1[1] + (rgb2[1] - rgb1[1]) * ratio
                        b = rgb1[2] + (rgb2[2] - rgb1[2]) * ratio
                        return rgb_to_hex(r, g, b)
                return color_scale[-1][1]

            for yr, p in enumerate(plants_list):
                for xc, c in enumerate(new_cols):
                    val = pivot_df.iloc[yr, xc]
                    
                    x_data.append(c)
                    y_data.append(p)
                    z_data.append(val)
                    color_data.append(get_interpolated_color(val))
                    text_data.append(f"<b>{val:.0%}</b>")
            
            # 셀 사이의 간격(흰 줄)을 최소화하기 위해 size를 아주 크게(95) 할당
            fig_test.add_trace(go.Scatter(
                x=x_data,
                y=y_data,
                mode='markers+text',
                marker=dict(
                    symbol='square',
                    size=95, 
                    color=color_data,
                    line=dict(width=0)
                ),
                text=text_data,
                textfont=dict(size=22, color="black"),
                hovertemplate="시간 축: %{x}<br>동: %{y}<br>평균 점유율: %{customdata[0]:.1%}<extra></extra>",
                customdata=[[z] for z in z_data],
                showlegend=False
            ))

            fig_test.update_layout(
                title="<b>동별 점유율 (%) 현황 (단위: 주별 (Week), 평균 (AVG))</b>",
                xaxis=dict(
                    title="시간 축",
                    tickfont=dict(size=13, color="black"), 
                    showgrid=False
                ),
                yaxis=dict(
                    title="생산 동",
                    tickfont=dict(size=13, color="black"), 
                    showgrid=False, 
                    autorange="reversed" # 위에서부터 1동이 오도록 뒤집기
                ),
                height=450,
                clickmode='event+select',
                plot_bgcolor='white',
                dragmode=False
            )
            
            # 히트맵 차트 렌더링 (on_select 활용)
            st.plotly_chart(fig_test, width="stretch", on_select="rerun", selection_mode="points", key="heatmap_test")

            # --- 최종 드릴다운 필터링 및 출력 ---
            target_date = rev_date_map.get(sel_date_label)
            target_plant = int(sel_plant_label.replace("동", ""))
            
            # 주간 단위 보기이므로, 선택한 날짜(월요일)로부터 7일간의 범위를 산정
            week_start = target_date.date()
            week_end = week_start + timedelta(days=6)
            week_num = week_start.isocalendar()[1]
            
            st.markdown(f"### 📋 상세 계획 내역 ({sel_plant_label}, {week_num}주차 {week_start.strftime('%Y-%m-%d')}~{week_end.strftime('%Y-%m-%d')})")
            
            if not valid_orders.empty:
                # 내부 표준 컬럼명(plant, start_in, end_out)을 사용하여 필터링
                # 클릭한 주 동안 단 하루라도 걸쳐 있는 모든 오더를 필터링
                drill_df = valid_orders[
                    (valid_orders['plant'] == target_plant) &
                    (valid_orders['start_in'].dt.date <= week_end) &
                    (valid_orders['end_out'].dt.date >= week_start)
                ].copy()
                
                if not drill_df.empty:
                    # 표시용 컬럼 정리 (PJT 추가)
                    display_cols = ['order_id', 'customer', 'pjt', 'model', 'qty', 'area_m2_unit', 'start_in', 'end_out']
                    # 존재하는 컬럼만 필터링 (방어적 코드)
                    actual_display_cols = [c for c in display_cols if c in drill_df.columns]
                    drill_df = drill_df[actual_display_cols]
                    
                    # 한글 라벨 매핑
                    label_map = {
                        'order_id': '순번', 'customer': '고객사', 'pjt': 'PJT명', 'model': '모델명', 
                        'qty': '수량', 'area_m2_unit': '면적', 'start_in': '시작(도장)', 'end_out': '종료(포장)'
                    }
                    drill_df.columns = [label_map.get(c, c) for c in drill_df.columns]
                    
                    # 데이터 타입 및 날짜 형식 보정 (PyArrow 에러 방지용 명시적 형변환)
                    for col in ['순번', 'PJT명', '고객사', '모델명']:
                        if col in drill_df.columns:
                            drill_df[col] = drill_df[col].apply(lambda x: str(x) if pd.notna(x) else '')
                    
                    for col in ['시작(도장)', '종료(포장)']:
                        if col in drill_df.columns:
                            drill_df[col] = pd.to_datetime(drill_df[col]).dt.strftime('%Y-%m-%d')
                    
                    if '수량' in drill_df.columns:
                        drill_df['수량'] = pd.to_numeric(drill_df['수량'], errors='coerce').fillna(0).astype("Int64")
                    
                    if '면적' in drill_df.columns:
                        drill_df['면적'] = pd.to_numeric(drill_df['면적'], errors='coerce').fillna(0).astype("Int64")
                    
                    # 가운데 정렬 및 간격 조정을 위해 st.table 사용 (CSS와 연동되어 가운데 정렬 보장)
                    # 인덱스가 혼합 타입일 경우 발생하는 오류를 방지하기 위해 reset_index(drop=True) 적용
                    st.table(drill_df.reset_index(drop=True))
                    st.caption(f"💡 총 {len(drill_df)}건의 오더가 가동 중입니다. (합계 수량: {drill_df['수량'].sum():,})")
                else:
                    st.info("해당 시점에 진행 중인 상세 오더 정보가 없습니다.")
        else:
            st.warning("분석 결과 데이터가 없습니다.")
        
        # [디버그용] 선택 데이터 실시간 확인 (화면 하단으로 이동)
        st.markdown("<hr>", unsafe_allow_html=True)
        if st.checkbox("디버그 모드 (클릭 데이터 확인)", value=True):
            st.write("🔍 DEBUG - 현재 선택 데이터:", st.session_state.get("heatmap_test"))

with tab5:
    if "dev_authenticated" not in st.session_state:
        st.session_state["dev_authenticated"] = False

    if not st.session_state["dev_authenticated"]:
        st.markdown("<div style='margin-top: 50px;'></div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            st.markdown("<h3 style='text-align: center;'>🔐 Developer Access</h3>", unsafe_allow_html=True)
            
            # [Fix] 비밀번호 확인 콜백 함수 (Enter 키 대응)
            def check_dev_password():
                pwd = st.session_state.get("dev_pwd_input", "")
                if pwd == "2305":
                    st.session_state["dev_authenticated"] = True
                    # st.rerun()은 콜백 내에서 불필요하므로 제거 (자동 재실행됨)
                elif pwd != "":
                    st.session_state["dev_pwd_error"] = "❌ 비밀번호가 일치하지 않습니다."
                else:
                    st.session_state.pop("dev_pwd_error", None)

            # [User Request] 자동 포커스 및 Enter 키 연동
            st.text_input("비밀번호를 입력하세요", type="password", key="dev_pwd_input", on_change=check_dev_password)
            
            if "dev_pwd_error" in st.session_state:
                st.error(st.session_state["dev_pwd_error"])

            if st.button("접근 허용", use_container_width=True):
                check_dev_password()
                if st.session_state["dev_authenticated"]:
                    st.rerun() # 버튼 클릭 시에는 명시적 재실행이 필요할 수 있음 (상태 변경 반영)

            # [User Request] JavaScript를 이용한 자동 포커스 (SetFocus) - 지연 및 재시도 로직 추가
            components.html(
                """
                <script>
                    function focusPassword() {
                        const passwordInput = window.parent.document.querySelector('input[type="password"]');
                        if (passwordInput) {
                            passwordInput.focus();
                        } else {
                            // 아직 렌더링되지 않았을 경우 100ms 후 재시도
                            setTimeout(focusPassword, 100);
                        }
                    }
                    // 최초 렌더링 시 약간의 지연 후 실행 (Streamlit 렌더링 타이밍 대응)
                    // [SetFocus] 명확한 포커싱을 위해 지연시간 유지 및 재시도 보강
                    setTimeout(focusPassword, 500); 
                </script>
                """,
                height=0,
            )
    else:
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        st.markdown(f"""
            <div style="display: flex; align-items: baseline; gap: 12px; margin-bottom: 5px;">
                <h3 style="margin: 0; font-size: 1.35rem;">📥 MES 사용자별 사용현황</h3>
                <span style="color: #aaa; font-size: 0.95rem;">MES-내부서비스관리-조회 및 엑셀 다운로드</span>
                <span style="margin-left: auto;">
                    <button onclick="window.location.reload()" style="font-size: 0.7rem; color: #888; background: none; border: 1px solid #ddd; border-radius: 4px; cursor: pointer;">로그아웃(새로고침)</button>
                </span>
            </div>
        """, unsafe_allow_html=True)
        
        # 로그아웃 버튼 (실제 세션 초기화용)
        if st.button("🔒 로그아웃", key="dev_logout_btn", help="개발자 모드를 종료합니다."):
            st.session_state["dev_authenticated"] = False
            st.rerun()

        # 1. 사용자 마스터 정보 우선 로드 (항상 표시)
        user_info_file = "순번 재직여부 아이디 사용자명 부서 전화번호 등록일 260410.txt"
        df_user_master = pd.DataFrame()
        
        if os.path.exists(user_info_file):
            try:
                with open(user_info_file, "r", encoding="utf-8") as f:
                    u_lines = f.readlines()
                
                if u_lines:
                    u_data = []
                    for u_line in u_lines[1:]:
                        u_line = u_line.strip()
                        if not u_line: continue
                        
                        u_parts = u_line.split()
                        if len(u_parts) < 5: continue
                        
                        # Pattern: [순번] [재직여부] [아이디] [사용자명] [REST...] [날짜] [시간]
                        u_reg = f"{u_parts[-2]} {u_parts[-1]}"
                        u_main = u_parts[:-2]
                        
                        order_num = u_main[0]
                        status = u_main[1]
                        user_id = u_main[2]
                        user_name = u_main[3]
                        
                        u_rem = u_main[4:]
                        dept_parts = []
                        phone = ""
                        phone_regex = r'\d{2,3}-\d{3,4}-\d{4}'
                        for ur in u_rem:
                            if re.match(phone_regex, ur):
                                phone = ur
                            else:
                                dept_parts.append(ur)
                        
                        dept = " ".join(dept_parts)
                        
                        u_row = {
                            '순번': order_num,
                            '재직여부': status,
                            '아이디': user_id,
                            '사용자명': user_name,
                            '부서': dept,
                            '전화번호': phone,
                            '등록일': u_reg
                        }
                        u_data.append(u_row)
                    
                    df_user_master = pd.DataFrame(u_data)
                    
                    # [UI Change] Display moved to bottom of analysis
                    pass 
            except Exception as ue:
                st.error(f"사용자 마스터 로드 오류: {ue}")
        else:
            st.warning(f"사용자 마스터 파일을 찾을 수 없습니다: {user_info_file}")

        st.divider()

        # 2. 로그 파일 업로드 및 분석
        dev_file_upload = st.file_uploader('"사용자별_사용현황 " 파일을 드래그하거나 클릭하여 업로드하세요.', 
                                            type=["csv", "xlsx", "xls", "xlsb"], key="dev_file_upload")
        
        if dev_file_upload:
            try:
                # 1. 파일 데이터 로딩 (pandas 활용)
                if dev_file_upload.name.lower().endswith('.csv'):
                    df_usage = pd.read_csv(dev_file_upload)
                else:
                    df_usage = pd.read_excel(dev_file_upload)
                
                if df_usage is not None and not df_usage.empty:
                    # 현재 컬럼명에 '일시', '사용자'가 포함되어 있는지 확인
                    current_cols = [str(c).replace(" ", "") for c in df_usage.columns]
                    has_header = any('일시' in c or '일자' in c for c in current_cols) and any('사용자' in c or 'user' in c for c in current_cols)
                    
                    if not has_header:
                        for i in range(min(15, len(df_usage))):
                            row_vals = [str(x).replace(" ", "") for x in df_usage.iloc[i].values]
                            if any('일시' in v or '일자' in v for v in row_vals) and any('사용자' in v or 'user' in v for v in row_vals):
                                df_usage.columns = df_usage.iloc[i].values
                                df_usage = df_usage.iloc[i+1:].reset_index(drop=True)
                                break
                                
                    # 컬럼명 공백 정리
                    df_usage.columns = [str(c).strip() for c in df_usage.columns]
                    
                    # 컬럼명 자동 탐지 (공백, 개행 문자 등 제거 후 확인)
                    date_col = None
                    user_col = None
                    for c in df_usage.columns:
                        c_clean = str(c).replace(" ", "").replace("\n", "").replace("\r", "").lower()
                        if not date_col and ('일시' in c_clean or '일자' in c_clean or 'date' in c_clean):
                            date_col = c
                        if not user_col and ('사용자' in c_clean or 'user' in c_clean):
                            user_col = c
                    
                    if date_col and user_col:
                        plot_df = df_usage.copy()
                        # 날짜 형식으로 변환 (형식이 맞지 않으면 NaT)
                        plot_df[date_col] = pd.to_datetime(plot_df[date_col], errors='coerce')
                        plot_df = plot_df.dropna(subset=[date_col, user_col])
                        
                        if not plot_df.empty:
                            # [User Request] 업로드된 사용자 명단 저장 (공백 제거 후 비교용)
                            st.session_state["uploaded_users"] = set(plot_df[user_col].astype(str).str.strip().unique())
                            st.success(f"'{dev_file_upload.name}' 데이터 분석 완료! (총 {len(plot_df)}건)")
                            st.markdown("### 📊 사용자별 접속 현황 대시보드")
                            
                            # 일자별 / 주차별 기준 산출
                            plot_df['Date'] = plot_df[date_col].dt.date
                            plot_df['Week'] = plot_df[date_col].dt.to_period('W').dt.start_time.dt.date
    
                            # 그래프 위아래 1개씩 렌더링 (전체 폭 사용)
                            
                            # 사용자별 총 접속 횟수 계산하여 정렬 순서 결정
                            user_rank = plot_df[user_col].value_counts().index.tolist()
                            
                            # 1. 사용자별 접속 현황 (일자별 Stack)
                            daily_counts = plot_df.groupby(['Date', user_col]).size().reset_index(name='Access_Count')
                            daily_counts['Date_Str'] = daily_counts['Date'].apply(lambda x: x.strftime('%#m/%#d'))
                            
                            # 각 사용자별 총합 계산 (텍스트 표시용)
                            daily_totals = daily_counts.groupby(user_col)['Access_Count'].sum().reset_index()
                            
                            # 커스텀 연한 색상 조합 (회색, 파랑, 노랑, 녹색 등)
                            custom_pastels = ["#D3D3D3", "#ADD8E6", "#FFF9C4", "#C8E6C9", "#F8BBD0", "#E1BEE7", "#B3E5FC", "#FFCCBC"]
                            
                            fig_daily = px.bar(daily_counts, x=user_col, y='Access_Count', color='Date_Str',
                                                title='<b>📅 사용자별 메뉴 클릭 횟수 (일자별 구분)</b>', 
                                                labels={'Date_Str': '일자', 'Access_Count': '메뉴 클릭 횟수', user_col: '사용자'},
                                                category_orders={user_col: user_rank},
                                                color_discrete_sequence=custom_pastels,
                                                template='plotly_white')
                            
                            # 상단에 합계 표시 (Scatter trace 이용)
                            fig_daily.add_scatter(x=daily_totals[user_col], y=daily_totals['Access_Count'], 
                                                  text=daily_totals['Access_Count'].apply(lambda x: f"<b>{x}</b>"), mode='text',
                                                  textposition='top center', showlegend=False,
                                                  textfont=dict(size=17, color='black'))
    
                            # 글씨 크기 및 굵기 조정 및 Y축 범위 여유 확보 (숫자 잘림 방지)
                            max_daily = daily_totals['Access_Count'].max() if not daily_totals.empty else 100
                            fig_daily.update_layout(
                                font=dict(size=14, color='black'),
                                title_font=dict(size=20, color='black'),
                                xaxis=dict(tickfont=dict(size=15, family='Arial Black', color='black')),
                                yaxis=dict(title_font=dict(size=16, color='black'), tickfont=dict(size=14, color='black', family='Arial Black'),
                                           range=[0, max_daily * 1.15]),
                                legend=dict(font=dict(size=13))
                            )
                            
                            # 2. 사용자별 접속 현황 (주차별 Stack)
                            weekly_counts = plot_df.groupby(['Week', user_col]).size().reset_index(name='Access_Count')
                            weekly_counts['Week_Str'] = weekly_counts['Week'].apply(lambda x: x.strftime('%#m/%#d'))
                            
                            # 각 사용자별 총합 계산 (텍스트 표시용)
                            weekly_totals = weekly_counts.groupby(user_col)['Access_Count'].sum().reset_index()
    
                            fig_weekly = px.bar(weekly_counts, x=user_col, y='Access_Count', color='Week_Str',
                                                title='<b>🗓️ 사용자별 메뉴 클릭 횟수 (주차별 구분)</b>', 
                                                labels={'Week_Str': '주차(시작일)', 'Access_Count': '메뉴 클릭 횟수', user_col: '사용자'},
                                                category_orders={user_col: user_rank},
                                                color_discrete_sequence=custom_pastels,
                                                template='plotly_white')
                            
                            # 상단에 합계 표시
                            fig_weekly.add_scatter(x=weekly_totals[user_col], y=weekly_totals['Access_Count'], 
                                                   text=weekly_totals['Access_Count'].apply(lambda x: f"<b>{x}</b>"), mode='text',
                                                   textposition='top center', showlegend=False,
                                                   textfont=dict(size=17, color='black'))
    
                            max_weekly = weekly_totals['Access_Count'].max() if not weekly_totals.empty else 100
                            fig_weekly.update_layout(
                                font=dict(size=14, color='black'),
                                title_font=dict(size=20, color='black'),
                                xaxis=dict(tickfont=dict(size=14, family='Arial Black', color='black')),
                                yaxis=dict(title_font=dict(size=16, color='black'), tickfont=dict(size=14, color='black', family='Arial Black'),
                                           range=[0, max_weekly * 1.15]),
                                legend=dict(font=dict(size=14))
                            )
    
                            # 3. 사용자별 로그인 일수 (1일 1회 계산)
                            # daily_counts 자체가 [Date, User] 그룹화 결과이므로 각 행을 1로 취급
                            login_df = daily_counts.copy()
                            login_df['Login_Value'] = 1
                            
                            # 로그인 일수 기준 사용자 정렬 순서
                            user_login_rank = login_df.groupby(user_col)['Login_Value'].sum().sort_values(ascending=False).index.tolist()
                            login_totals = login_df.groupby(user_col)['Login_Value'].sum().reset_index()
    
                            fig_login = px.bar(login_df, x=user_col, y='Login_Value', color='Date_Str',
                                                title='<b>🔑 사용자별 로그인 일수 (1일 1회 기준)</b>', 
                                                labels={'Date_Str': '일자', 'Login_Value': '로그인 일수', user_col: '사용자'},
                                                category_orders={user_col: user_login_rank},
                                                color_discrete_sequence=custom_pastels,
                                                template='plotly_white')
                            
                            fig_login.add_scatter(x=login_totals[user_col], y=login_totals['Login_Value'], 
                                                  text=login_totals['Login_Value'].apply(lambda x: f"<b>{x}일</b>"), mode='text',
                                                  textposition='top center', showlegend=False,
                                                  textfont=dict(size=17, color='black'))
    
                            max_login = login_totals['Login_Value'].max() if not login_totals.empty else 10
                            fig_login.update_layout(
                                font=dict(size=14, color='black'),
                                title_font=dict(size=20, color='black'),
                                xaxis=dict(tickfont=dict(size=14, family='Arial Black', color='black')),
                                yaxis=dict(title_font=dict(size=16, color='black'), tickfont=dict(size=14, color='black', family='Arial Black'),
                                           range=[0, max_login * 1.15]),
                                legend=dict(font=dict(size=14))
                            )
    
                            # 그래프 출력 순서 조정 (일자별 -> 로그인 일수 -> 주차별)
                            st.plotly_chart(fig_daily, use_container_width=True)
                            
                            # 각 그래프 사이에 연한 회색 구분선 추가
                            st.markdown("<hr style='border: 0.5px solid #eee; margin: 30px 0;'>", unsafe_allow_html=True)
                            st.plotly_chart(fig_login, use_container_width=True)
                            

                            # --- [User Request] 사용자 마스터 정보 & 미접속 사용자 비교 분석 (위치 변경) ---
                            # uploaded_users가 세션에 있을 때만 비교 수행
                            if "uploaded_users" in st.session_state and not df_user_master.empty:
                                uploaded_users = st.session_state["uploaded_users"]
                                missing_users_df = df_user_master[~df_user_master['사용자명'].str.strip().isin(uploaded_users)].copy()
                                
                                st.markdown("<hr style='border: 1px dashed #ddd; margin: 40px 0 20px 0;'>", unsafe_allow_html=True)
                                st.markdown(f"### ⚠️ 시스템 미접속 사용자 명단 (총 {len(missing_users_df)}명)")
                                st.caption("※ 사용자 마스터 정보에는 등록되어 있으나, 업로드한 '사용자별_사용현황' 엑셀 상에 접속 기록이 없는 인원입니다.")
                                
                                if not missing_users_df.empty:
                                    names_list = ", ".join(missing_users_df['사용자명'].tolist())
                                    st.markdown(f"""
                                        <div style="background-color: rgba(255, 75, 75, 0.05); padding: 15px; border-radius: 8px; border: 1px solid rgba(255, 75, 75, 0.2); margin: 10px 0 10px 0; line-height: 1.6;">
                                            <strong style="color: #ff4b4b; font-size: 0.9rem;">📝 미접속 사용자 명단:</strong><br>
                                            <span style="font-size: 0.95rem; color: #333;">{names_list}</span>
                                        </div>
                                    """, unsafe_allow_html=True)

                                    dept_groups = missing_users_df.groupby('부서')['사용자명'].apply(lambda x: ", ".join(x)).reset_index()
                                    dept_lines = []
                                    for _, row in dept_groups.iterrows():
                                        d_name = row['부서'] if row['부서'] else "부서 미지정"
                                        dept_lines.append(f"<li style='margin-bottom: 5px;'><strong style='color: #444; font-size: 0.9rem;'>{d_name}</strong> : <span style='font-size: 0.9rem; color: #555;'>{row['사용자명']}</span></li>")
                                    
                                    dept_html = f"""
                                        <div style="background-color: rgba(255, 75, 75, 0.05); padding: 15px; border-radius: 8px; border: 1px solid rgba(255, 75, 75, 0.2); margin: 0 0 20px 0;">
                                            <strong style="color: #ff4b4b; font-size: 0.9rem; display: block; margin-bottom: 10px;">🏢 부서별 미접속 현황:</strong>
                                            <ul style="list-style: none; padding-left: 0; margin: 0;">
                                                {"".join(dept_lines)}
                                            </ul>
                                        </div>
                                    """
                                    st.markdown(dept_html, unsafe_allow_html=True)
                                
                                    with st.expander(f"미접속 사용자 명단 확인 ({len(missing_users_df)}명)", expanded=True):
                                        display_cols = ['사용자명', '부서', '아이디', '등록일']
                                        available_cols = [c for c in display_cols if c in missing_users_df.columns]
                                        
                                        table_header = "".join([f"<th>{col}</th>" for col in available_cols])
                                        table_rows = ""
                                        for _, row in missing_users_df[available_cols].iterrows():
                                            row_cells = "".join([f"<td>{row[col]}</td>" for col in available_cols])
                                            table_rows += f"<tr>{row_cells}</tr>"
                                        
                                        custom_table_html = f"""
                                        <div class="compact-table-container">
                                            <table class="compact-table">
                                                <thead>
                                                    <tr>{table_header}</tr>
                                                </thead>
                                                <tbody>
                                                    {table_rows}
                                                </tbody>
                                            </table>
                                        </div>
                                        """
                                        st.markdown(custom_table_html, unsafe_allow_html=True)
                                        st.caption("💡 위 명단은 '사용자별_사용현황' 데이터에 없는 마스터 사용자들입니다.")
                                else:
                                    st.success("🎉 모든 마스터 사용자가 시스템 접속 기록이 있습니다.")
                                
                                # [User Request] 마스터 정보 전체 보기를 미접속자 명단 아래로 이동
                                st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
                                with st.expander("👤 사용자 마스터 정보 확인 (전체)", expanded=False):
                                    st.dataframe(df_user_master, use_container_width=True, height=400)

                            st.markdown("<hr style='border: 0.5px solid #eee; margin: 30px 0;'>", unsafe_allow_html=True)
                            st.plotly_chart(fig_weekly, use_container_width=True)
                                
                            # (옵션) 원본 데이터 테이블 확인
                            with st.expander("원본 데이터 확인"):
                                st.dataframe(plot_df)
                        else:
                            st.warning("분석 가능한 유효한 날짜/사용자 데이터가 없습니다.")
                    else:
                        st.error(f"❌ 엑셀 파일에서 '일시' 혹은 '사용자' 컬럼을 찾을 수 없습니다.")
                        st.info(f"파싱된 컬럼 목록: {list(df_usage.columns)}")
                        with st.expander("데이터 미리보기 (상위 10행)"):
                            st.dataframe(df_usage.head(10))
            except Exception as e:
                st.error(f"🚨 파일 처리 중 오류가 발생했습니다: {e}")



