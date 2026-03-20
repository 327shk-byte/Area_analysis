import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
import yaml
import os

class DataValidator:
    def __init__(self):
        self.required_order_cols = ['order_id', 'model', 'qty', 'plant', 'area_m2_unit', 'start_in']
        self.capacity_cols = ['plant', 'capacity_m2', 'effective_from', 'effective_to']
        
        # 정규식 패턴 정의
        self.patterns = {
            'order_id': r'^[A-Za-z0-9\-_]+$',
            'model': r'^[A-Za-z0-9\-_]+$',
            'plant': r'^[1-5]$',
            'date': r'^\d{4}-\d{2}-\d{2}$'
        }
    def validate_orders(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list]:
        """주문 데이터 검증 및 상태 업데이트"""
        if df.empty:
            cols = self.required_order_cols + ['is_included', 'row_type', 'exclude_reason', 'warning_flags', 'data_mode', 'is_estimated']
            empty_df = pd.DataFrame(columns=cols)
            return empty_df.copy(), empty_df.copy(), []
            
        df = df.copy()
        
        # 1. 메타 컬럼 존재 확인 및 초기화 (NaN 방어)
        for col in ['is_included', 'row_type', 'exclude_reason', 'warning_flags', 'data_mode', 'is_estimated']:
            if col not in df.columns:
                if col == 'is_included':
                    df[col] = True
                elif col == 'is_estimated':
                    df[col] = False
                elif col == 'data_mode':
                    df[col] = 'unknown'
                else:
                    df[col] = ""
            else:
                if col in ['exclude_reason', 'warning_flags']:
                    df[col] = df[col].fillna("").astype(str)
                elif col == 'is_included':
                    df[col] = df[col].fillna(True).astype(bool)
                elif col == 'is_estimated':
                    df[col] = df[col].fillna(False).astype(bool)
        
        # 2. 필수 컬럼 체크
        missing_cols = [col for col in self.required_order_cols if col not in df.columns]
        if missing_cols:
            return pd.DataFrame(), df, [f"Missing required columns: {missing_cols}"]

        # 3. 데이터 정규화 (Plant 등)
        def clean_plant(val):
            try:
                s = str(val).strip()
                digits = "".join(filter(str.isdigit, s))
                return int(digits) if digits else np.nan
            except:
                return np.nan

        # 이미 숫자인 경우 제외하고 클리닝
        mask_plant_str = df['plant'].apply(lambda x: isinstance(x, str))
        df.loc[mask_plant_str, 'plant'] = df.loc[mask_plant_str, 'plant'].apply(clean_plant)
        
        # 4. 유효성 검사 (is_included 가 True인 실제 데이터 행 대상)
        mask_real = df['row_type'].isin(['DATA_PLAN', 'DATA_ACTUAL', 'DATA'])
        
        # 💡 [Senior Logic] 원본 데이터 보존을 위해 검증용 임시 컬럼 사용
        # 원본 컬럼(start_in, end_out)에 "완료" 등의 텍스트가 있을 경우 NaT로 덮어씌워지는 것을 방지
        df['_tmp_qty'] = pd.to_numeric(df['qty'], errors='coerce')
        df['_tmp_area'] = pd.to_numeric(df['area_m2_unit'], errors='coerce')
        df['_tmp_start'] = pd.to_datetime(df['start_in'], errors='coerce')
        df['_tmp_end'] = pd.to_datetime(df['end_out'], errors='coerce')
        
        idx_invalid_qty = mask_real & ((df['_tmp_qty'] <= 0) | df['_tmp_qty'].isna())
        df.loc[idx_invalid_qty, 'warning_flags'] += "Qty_Error; "
        df.loc[idx_invalid_qty, 'is_included'] = False
        df.loc[idx_invalid_qty, 'exclude_reason'] += "수량 오류; "
        
        idx_invalid_plant = mask_real & (~df['plant'].isin([1, 2, 3, 4, 5]))
        df.loc[idx_invalid_plant, 'warning_flags'] += "Plant_Error; "
        df.loc[idx_invalid_plant, 'is_included'] = False
        df.loc[idx_invalid_plant, 'exclude_reason'] += "유효하지 않은 동; "

        # 날짜 누락 및 역전 체크 (임시 컬럼 기반)
        idx_missing_start = mask_real & df['_tmp_start'].isna()
        df.loc[idx_missing_start, 'warning_flags'] += "Missing_Start; "
        df.loc[idx_missing_start, 'is_included'] = False
        df.loc[idx_missing_start, 'exclude_reason'] += "시작일 누락; "

        # end_out 보정 (임시 컬럼 기반)
        mask_need_end_fix = mask_real & df['is_included'] & df['_tmp_end'].isna() & df['_tmp_start'].notna()
        if mask_need_end_fix.any():
            df.loc[mask_need_end_fix, '_tmp_end'] = df.loc[mask_need_end_fix, '_tmp_start'] + timedelta(days=14)
            df.loc[mask_need_end_fix, 'warning_flags'] += "End_Predicted; "
            df.loc[mask_need_end_fix, 'is_estimated'] = True

        idx_invalid_date = mask_real & df['_tmp_start'].notna() & df['_tmp_end'].notna() & (df['_tmp_start'] > df['_tmp_end'])
        df.loc[idx_invalid_date, 'warning_flags'] += "Date_Reversal; "
        df.loc[idx_invalid_date, 'is_included'] = False
        df.loc[idx_invalid_date, 'exclude_reason'] += "날짜 역전; "

        # 5. 결과 분리
        # 분석 엔진용 데이터(valid_df)는 정제된 날짜 데이터를 사용
        valid_df = df[df['is_included'] == True].copy()
        valid_df['qty'] = valid_df['_tmp_qty']
        valid_df['area_m2_unit'] = valid_df['_tmp_area']
        valid_df['start_in'] = valid_df['_tmp_start']
        valid_df['end_out'] = valid_df['_tmp_end']
        
        # UI 출력용 전체 데이터(df)는 원본 텍스트를 유지하고 임시 컬럼만 삭제
        df = df.drop(columns=['_tmp_qty', '_tmp_area', '_tmp_start', '_tmp_end'])
        invalid_df = df[df['is_included'] == False].copy()
        
        errors = []
        if not invalid_df.empty:
            # 실질적 데이터 중 제외된 것만 에러 리스트에 추가 (헤더 제외)
            err_report = invalid_df[invalid_df['row_type'].str.contains('DATA', na=False)]
            if not err_report.empty:
                errors = err_report.apply(lambda r: f"[{r['order_id']}] {r['exclude_reason']}", axis=1).tolist()

        return valid_df, df, errors # 전체 상태 확인을 위해 원본 df(상태 포함)를 index 1로 반환

    def validate_capacity(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
        """공장 Capa 데이터 검증"""
        errors = []
        df = df.copy()

        # 1. 필수 컬럼 체크
        missing_cols = [col for col in self.capacity_cols if col not in df.columns]
        if missing_cols:
            errors.append(f"Missing required columns: {missing_cols}")
            return df, errors

        # 2. 날짜 형식 변환
        for col in ['effective_from', 'effective_to']:
            df[col] = pd.to_datetime(df[col], errors='coerce')

        # 3. 데이터 논리 체크
        invalid_date = df[df['effective_from'] > df['effective_to']]
        if not invalid_date.empty:
            errors.append(f"Capacity date reversal found for plant: {invalid_date['plant'].tolist()}")

        return df, errors

    def load_schema(self, schema_path: str) -> dict:
        """YAML 스키마 파일 로드"""
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"스키마 파일 로드 실패: {e}")
            return {}

    def validate_schema(self, df: pd.DataFrame, schema: dict) -> list:
        """데이터 프레임을 YAML 스키마에 따라 검증"""
        errors = []
        
        if not schema or 'columns' not in schema:
            return ["스키마가 유효하지 않습니다."]
        
        schema_cols = schema['columns']
        
        # 필수 컬럼 체크
        for col_name, col_info in schema_cols.items():
            if col_info.get('required', False) and col_name not in df.columns:
                errors.append(f"필수 컬럼 누락: {col_name}")
                continue
            
            if col_name not in df.columns:
                continue
            
            # 데이터 타입 검증
            if 'type' in col_info:
                expected_type = col_info['type']
                if expected_type == 'integer':
                    # 정수형 검증
                    invalid_rows = df[~df[col_name].apply(lambda x: isinstance(x, (int, np.integer)) or (isinstance(x, float) and x.is_integer()))]
                    if not invalid_rows.empty:
                        errors.append(f"컬럼 '{col_name}'에 정수형이 아닌 값이 포함되어 있습니다.")
                elif expected_type == 'float':
                    # 실수형 검증
                    invalid_rows = df[~df[col_name].apply(lambda x: isinstance(x, (int, float, np.floating, np.integer)))]
                    if not invalid_rows.empty:
                        errors.append(f"컬럼 '{col_name}'에 실수형이 아닌 값이 포함되어 있습니다.")
                elif expected_type == 'string':
                    # 문자열 검증
                    invalid_rows = df[~df[col_name].apply(lambda x: isinstance(x, str))]
                    if not invalid_rows.empty:
                        errors.append(f"컬럼 '{col_name}'에 문자열이 아닌 값이 포함되어 있습니다.")
                elif expected_type == 'date':
                    # 날짜형 검증
                    invalid_rows = df[pd.to_datetime(df[col_name], errors='coerce').isna()]
                    if not invalid_rows.empty:
                        errors.append(f"컬럼 '{col_name}'에 날짜형이 아닌 값이 포함되어 있습니다.")
            
            # 최소값/최대값 검증
            if 'min' in col_info and col_name in df.columns:
                invalid_rows = df[df[col_name] < col_info['min']]
                if not invalid_rows.empty:
                    errors.append(f"컬럼 '{col_name}'에 최소값({col_info['min']}) 미만의 값이 포함되어 있습니다.")
            
            if 'max' in col_info and col_name in df.columns:
                invalid_rows = df[df[col_name] > col_info['max']]
                if not invalid_rows.empty:
                    errors.append(f"컬럼 '{col_name}'에 최대값({col_info['max']}) 초과의 값이 포함되어 있습니다.")
            
            # 열거형 값 검증
            if 'enum' in col_info and col_name in df.columns:
                invalid_rows = df[~df[col_name].isin(col_info['enum'])]
                if not invalid_rows.empty:
                    errors.append(f"컬럼 '{col_name}'에 허용되지 않은 값이 포함되어 있습니다. 허용값: {col_info['enum']}")
            
            # 정규식 패턴 검증
            if 'pattern' in col_info and col_name in df.columns:
                pattern = col_info['pattern']
                invalid_rows = df[~df[col_name].astype(str).str.match(pattern)]
                if not invalid_rows.empty:
                    errors.append(f"컬럼 '{col_name}'에 패턴('{pattern}')에 맞지 않는 값이 포함되어 있습니다.")
        
        return errors
