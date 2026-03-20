import pandas as pd
import numpy as np
import logging

# 로깅 설정
from datetime import datetime
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataTransformer:
    def __init__(self):
        # 표준 컬럼명 매핑 정의 (사용자 파일 헤더 -> 내부 표준)
        # 키값은 정규화된 형태(공백 제거, 대문자)로 정의
        self.column_map = {
            'SEQ.': 'order_id', 'SEQ': 'order_id', '순번': 'order_id', 'P/O': 'order_id', 'ORDER': 'order_id', 'ID': 'order_id',
            '고객명': 'customer', '고객': 'customer', 'CUSTOMER': 'customer',
            'MODEL': 'model', '모델': 'model', 'MODEL1': 'model', 'NAME': 'model', '품명': 'model', '제품명': 'model',
            'QTY': 'qty', '수량': 'qty', 'QUANTITY': 'qty', 'AMOUNT': 'qty', '제작수량': 'qty',
            '납기일': 'due_date', '납기': 'due_date', 'DUE': 'due_date',
            '진행동': 'plant', 'PLANT': 'plant', 'FACILITY': 'plant', '동': 'plant', 'LINE': 'plant',
            'AREA': 'area_m2_unit', '면적': 'area_m2_unit', 'UNITAREA': 'area_m2_unit', '평수': 'area_m2_unit', 'M2': 'area_m2_unit',
            '도장': 'start_in', 
            '제작_1': 'manufacture_1', '자재입고': 'material_in', '원자재입고': 'material_in', 'START': 'material_in',
            '제작일': 'production', '제작일자': 'production', '제작(P)': 'production',
            '제작': 'production_status', '현황': 'production_status', '실행': 'production_status', '상태': 'production_status',
            '포장일': 'end_out', '포장': 'end_out', '반출일': 'end_out', '출하': 'end_out', 'END': 'end_out', 'FINISH': 'end_out', 'OUT': 'end_out', '준공': 'end_out'
        }
    
    def normalize_col(self, col_name: str) -> str:
        """컬럼명을 정규화: 줄바꿈 제거, 모든 공백 제거, 대문자 변환"""
        if pd.isna(col_name): return ""
        return str(col_name).replace('\n', '').replace('\r', '').replace(' ', '').replace('\t', '').strip().upper()

    def find_data_header(self, df_raw: pd.DataFrame) -> tuple[int, dict]:
        """
        다수 키워드 매칭을 통해 최적의 헤더 행을 탐색
        """
        best_row = -1
        best_mapping = {}
        max_matches = 0
        
        for i, row in df_raw.head(40).iterrows():
            row_norm = [self.normalize_col(x) for x in row.values]
            current_mapping = {}
            used_standards = set()
            matches = 0
            
            # [Senior Logic] 2-Pass 매핑 알고리즘
            # Pass 1: 완전 일치 매칭 (Exact Match)
            for idx, cell in enumerate(row_norm):
                if not cell: continue
                for key, standard in self.column_map.items():
                    norm_key = self.normalize_col(key)
                    if cell == norm_key: # 완전 일치만
                        if standard not in used_standards:
                            current_mapping[idx] = standard
                            used_standards.add(standard)
                            matches += 1
                            break
            
            # Pass 2: 부분 일치 매칭 (Partial Match) - 남은 컬럼들 대상
            for idx, cell in enumerate(row_norm):
                if not cell or idx in current_mapping: continue
                for key, standard in self.column_map.items():
                    norm_key = self.normalize_col(key)
                    if norm_key in cell: # 부분 일치 허용
                        if standard not in used_standards:
                            current_mapping[idx] = standard
                            used_standards.add(standard)
                            matches += 1
                            break
            
            # 최소 2개 이상의 핵심 컬럼이 발견되면 유효한 헤더 후보로 간주
            if matches > max_matches and matches >= 2:
                max_matches = matches
                best_row = i
                best_mapping = current_mapping
        
        return best_row, best_mapping

    def parse_date_serial_first(self, val):
        """날짜 변환: 숫자(Excel Serial)를 최우선으로 처리하여 1970년 에러 방지"""
        if pd.isna(val) or str(val).strip().lower() in ['nan', 'none', '']:
            return pd.NaT
        try:
            # 1. 숫자형(float/int)인 경우 Excel Serial 날짜로 강제 처리
            # Excel Serial 40000은 2009년경, 45000은 2023년경임
            s_val = str(val).replace(',', '').strip()
            if s_val.replace('.', '', 1).isdigit():
                f_val = float(s_val)
                # [Fix] 1902년(serial 1000) 등 오인 방지: 최소 1982년(30000) ~ 2064년(60000) 범위만 허용
                if 30000 < f_val < 60000: 
                    return pd.to_datetime(f_val, unit='D', origin='1899-12-30')
            
            # 2. 이미 datetime 객체인 경우
            if isinstance(val, (datetime, pd.Timestamp)):
                return pd.to_datetime(val)
                
            # 3. 일반 문자열 날짜 시도
            dt = pd.to_datetime(val, errors='coerce')
            if pd.isna(dt):
                return val # 날짜가 아니면 원본(실행, 취부 등) 반환
            return dt
        except:
            return val

    def transform_orders(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        원본 데이터를 표준 형식으로 변환 및 전처리 상태 추적 컬럼 추가
        """
        if df_raw.empty:
            return df_raw

        # 1. 헤더 정보를 미리 탐색 (원본 상태에서 탐색)
        header_idx, mapping = self.find_data_header(df_raw)
        
        # 2. 초기 상태 컬럼 정의 (헤더 탐색 후 추가)
        df_proc = df_raw.copy()
        df_proc['is_included'] = True
        df_proc['row_type'] = 'DATA'
        df_proc['exclude_reason'] = ""
        df_proc['warning_flags'] = ""

        # 3. 첫 번째 열(index 0)을 기준으로 인덱스 선정 및 분류
        # Note: df_proc의 0번 열은 원본의 첫 번째 열임
        first_col = df_proc.iloc[:, 0]
        target_indices = []

        def is_numeric(val):
            try:
                if pd.isna(val): return False
                v = str(val).replace(',', '').replace(' ', '').strip()
                if not v: return False
                float(v)
                return True
            except:
                return False

        def is_header_like(val):
            v = self.normalize_col(val)
            return 'SEQ' in v or '순번' in v

        # 분류 및 병합 로직 (N행 + N+1행을 하나로 합침)
        # 사용자 요청: SEQ 가 있는 행(11) + 다음행(12)을 가져와서 합치는 수식 (중복 방지)
        merged_rows = []
        skip_next = False
        
        for idx in range(len(df_proc)):
            if skip_next:
                skip_next = False
                continue
            val = df_proc.iloc[idx, 0]
            if is_header_like(val):
                row = df_proc.iloc[idx].copy()
                row['row_type'] = 'HEADER'
                row['is_included'] = False
                row['exclude_reason'] = "구조적 헤더"
                merged_rows.append(row)
            elif is_numeric(val):
                # SEQ 가 있는 행 (N행)
                current_row = df_proc.iloc[idx].copy()
                current_row['row_type'] = 'DATA_PLAN'
                current_row['is_included'] = True # Phase 4: 엔진의 mode 필터에서 걸러지므로 포함 허용
                merged_rows.append(current_row)
                
                # 다음 행(N+1행) 확인
                if idx + 1 < len(df_proc):
                    next_val = df_proc.iloc[idx + 1, 0]
                    # 다음 행이 숫자가 아니고 헤더도 아니면 데이터 행(ACTUAL)으로 간주하여 가져옴
                    if not is_numeric(next_val) and not is_header_like(next_val):
                        next_row = df_proc.iloc[idx + 1].copy()
                        next_row['row_type'] = 'DATA_ACTUAL'
                        next_row['is_included'] = True # 실제 시뮬레이션에 사용
                        merged_rows.append(next_row)
                        skip_next = True # 다음 행은 이미 처리(포함)했으므로 루프에서 건너뜀
            else:
                row = df_proc.iloc[idx].copy()
                row['row_type'] = 'STRUCTURAL'
                row['is_included'] = False
                row['exclude_reason'] = "비데이터 행"
                merged_rows.append(row)

        df = pd.DataFrame(merged_rows)

        # 4. 컬럼명 설정 및 표준화
        meta_cols = ['is_included', 'row_type', 'exclude_reason', 'warning_flags']
        if header_idx != -1:
            raw_header_row = list(df_raw.iloc[header_idx].values)
            unique_cols = []
            counts = {}
            for col in raw_header_row:
                c = self.normalize_col(col)
                if not c: c = "NAN"
                if c in counts:
                    counts[c] += 1
                    unique_cols.append(f"{c}_{counts[c]}")
                else:
                    counts[c] = 0
                    unique_cols.append(c)
            
            df.columns = unique_cols + meta_cols
            
            # 인덱스 기반 매핑 적용
            rename_dict = {}
            for col_idx, standard in mapping.items():
                if col_idx < len(unique_cols):
                    rename_dict[unique_cols[col_idx]] = standard
            
            df = df.rename(columns=rename_dict)
        else:
            # 헤더를 못 찾은 경우 기본 이름이라도 붙여줌
            basic_cols = [f"COL_{i}" for i in range(len(df.columns) - 4)]
            df.columns = basic_cols + meta_cols

        # 5. 필수 표준 컬럼이 누락된 경우 빈 컬럼이라도 생성 (UI 크래시 방지)
        standard_cols = ['order_id', 'customer', 'model', 'qty', 'due_date', 'plant', 'area_m2_unit', 'production', 'production_status', 'start_in', 'end_out']
        for col in standard_cols:
            if col not in df.columns:
                df[col] = np.nan

        # 5. 날짜 변환 (Serial 우선)
        # production_status도 '일자/실행' 혼합이므로 시리얼 변환 시도
        date_cols = ['due_date', 'start_in', 'production', 'production_status', 'end_out']
        for col in date_cols:
            if col in df.columns:
                df[col] = df[col].apply(self.parse_date_serial_first)
                
                # [Date Guardrail] 연도 기반 2차 필터링 (1902년 등 이상치 제거)
                # 2000년 이전 데이터는 쓰레기값/오인으로 간주하여 NaT 처리
                def enforce_year_range(val):
                    if pd.isna(val) or not isinstance(val, (datetime, pd.Timestamp)):
                        return val
                    if val.year < 2000 or val.year > 2099:
                        return pd.NaT
                    return val
                
                df[col] = df[col].apply(enforce_year_range)

        # 5-2. [Phase 4] data_mode 분류 (plan/actual)
        df['data_mode'] = 'unknown'
        
        # 💡 [Senior Logic] row_type을 기반으로 먼저 분류하고, 제작(production_status) 텍스트로 보정
        if 'row_type' in df.columns:
            df.loc[df['row_type'] == 'DATA_PLAN', 'data_mode'] = 'plan'
            df.loc[df['row_type'] == 'DATA_ACTUAL', 'data_mode'] = 'actual'

        if 'production_status' in df.columns:
            # "일자"가 포함되면 계획(plan), "실행"이 포함되면 실적(actual)
            mask_plan = df['production_status'].astype(str).str.contains('일자', na=False)
            mask_actual = df['production_status'].astype(str).str.contains('실행', na=False)
            df.loc[mask_plan, 'data_mode'] = 'plan'
            df.loc[mask_actual, 'data_mode'] = 'actual'
        
        # 6. 데이터 보정: ffill
        if 'order_id' in df.columns:
            # 💡 [Senior Sync] 주문 식별/속성 정보만 ffill 적용
            # '제작/제작_1/포장' 등 실행 데이터(production, production_status, start_in, end_out)는 
            # 각 행(N/N+1)의 독립적인 데이터 보존을 위해 ffill 대상에서 제외
            cols_to_fill = ['order_id', 'customer', 'model', 'qty', 'due_date', 'plant', 'area_m2_unit']
            available_fill_cols = [c for c in df.columns if c in cols_to_fill]
            
            for col in available_fill_cols:
                df[col] = df[col].replace(['', 'nan', 'None', 'NaN', 'NAN'], np.nan)
            
            # DATA_PLAN/ACTUAL 영역에서 주문 정보 상속 수행
            df[available_fill_cols] = df[available_fill_cols].ffill()
        
        return df.reset_index(drop=True)

    def get_preview_rows(self, df: pd.DataFrame, n=2) -> pd.DataFrame:
        """
        미리보기용 데이터 (is_included=True 인 것 중심)
        """
        if 'is_included' in df.columns:
            return df[df['is_included']].head(n)
        return df.head(n)
