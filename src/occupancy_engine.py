import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
from functools import lru_cache
import hashlib
import json

class OccupancyEngine:
    def __init__(self):
        self._cache = {}
    
    def _generate_cache_key(self, orders_df, capacity_df, start_date, end_date, mode, include_estimated, granularity, aggregation):
        """계산 조건에 따라 캐시 키 생성"""
        # DataFrame의 주요 특성으로 해시 생성
        orders_hash = hashlib.md5(
            pd.util.hash_pandas_object(orders_df, index=False).values.tobytes()
        ).hexdigest()
        
        capacity_hash = hashlib.md5(
            pd.util.hash_pandas_object(capacity_df, index=False).values.tobytes()
        ).hexdigest()
        
        # 모든 조건을 딕셔너리로 정리
        conditions = {
            "orders_hash": orders_hash,
            "capacity_hash": capacity_hash,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "mode": mode,
            "include_estimated": include_estimated,
            "granularity": granularity,
            "aggregation": aggregation
        }
        
        # JSON 문자열로 변환하여 해시 생성
        conditions_str = json.dumps(conditions, sort_keys=True)
        return hashlib.md5(conditions_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key):
        """캐시에서 결과 조회"""
        if cache_key in self._cache:
            return self._cache[cache_key]
        return None
    
    def _save_to_cache(self, cache_key, result):
        """결과를 캐시에 저장"""
        # 캐시 크기 제한 (최대 10개)
        if len(self._cache) >= 10:
            # 가장 오래된 항목 제거
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        self._cache[cache_key] = result

    def _to_excel_datetime(self, s: pd.Series) -> pd.Series:
        """
        s에 문자열/엑셀serial(숫자)/datetime이 섞여 있어도
        최종적으로 datetime64로 통일한다.
        """
        s2 = s.copy()

        # 1) 숫자(엑셀 serial) 처리: 20000~60000 사이를 엑셀 날짜로 간주(대략 1954~2064)
        num = pd.to_numeric(s2, errors="coerce")
        is_excel_serial = num.between(20000, 60000)

        out = pd.Series(pd.NaT, index=s2.index, dtype="datetime64[ns]")

        if is_excel_serial.any():
            out.loc[is_excel_serial] = pd.to_datetime(
                num.loc[is_excel_serial],
                unit="D",
                origin="1899-12-30",
                errors="coerce",
            )

        # 2) 나머지(문자열/이미 datetime) 처리
        rest = ~is_excel_serial
        if rest.any():
            out.loc[rest] = pd.to_datetime(s2.loc[rest], errors="coerce")

        return out

    def _empty_result(self) -> dict:
        """기본 빈 결과 구조 반환"""
        return {
            "daily_occupancy": pd.DataFrame(),
            "final_df": pd.DataFrame(),
            "monthly_summary": pd.DataFrame(),
            "over_threshold_days": pd.DataFrame()
        }

    def _calculate_plant_occupancy(self, plant, delta_df, full_dates, calc_start, calc_end, capacity_df, min_date, max_date):
        """단일 공장에 대한 점유율 계산"""
        plant_delta = delta_df[delta_df['plant'] == plant].groupby('date')['delta'].sum().reindex(full_dates, fill_value=0)
        plant_occ = plant_delta.cumsum()
        
        # 조회 범위 슬라이싱
        mask = (full_dates >= calc_start) & (full_dates <= calc_end)
        dates_sliced = full_dates[mask]
        occ_sliced = plant_occ[mask]
        
        # Capacity 매핑
        plant_cap_info = capacity_df[capacity_df['plant'] == plant]
        caps = []
        for d in dates_sliced:
            cap_row = plant_cap_info[(plant_cap_info['effective_from'] <= d) & (plant_cap_info['effective_to'] >= d)]
            caps.append(cap_row.iloc[0]['capacity_m2'] if not cap_row.empty else np.nan)
        
        p_df = pd.DataFrame({
            'date': dates_sliced,
            'plant': plant,
            'occupied_area': occ_sliced.values,
            'capacity': caps
        })
        # 0 이하 방지 및 점유율 계산
        p_df['occupied_area'] = p_df['occupied_area'].clip(lower=0)
        p_df['occupancy_rate'] = (p_df['occupied_area'] / p_df['capacity']).fillna(0).clip(lower=0)
        
        return p_df

    def calculate_daily_occupancy(self, orders_df: pd.DataFrame, capacity_df: pd.DataFrame, 
                                 start_date=None, end_date=None, 
                                 mode='plan', include_estimated=True,
                                 granularity='D', aggregation='MAX') -> dict:
        """
        [Phase 4] 고도화된 점유 계산 엔진
        - mode: 'plan'(일자), 'actual'(실행) 필터링
        - include_estimated: end_out 추정 데이터 포함여부
        - granularity: 'D'(일), 'W'(주), 'M'(월) 집계
        - aggregation: 'MAX'(피크치), 'AVG'(평균)
        """
        # 캐시 키 생성
        cache_key = self._generate_cache_key(
            orders_df, capacity_df, start_date, end_date, 
            mode, include_estimated, granularity, aggregation
        )
        
        # 캐시에서 결과 조회
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result

        if orders_df.empty:
            return self._empty_result()

        df = orders_df.copy()

        # 1. 시나리오 필터링 (Guardrail #2 반영)
        if 'data_mode' in df.columns and mode in ['plan', 'actual']:
            df = df[df['data_mode'] == mode]
        
        if not include_estimated and 'is_estimated' in df.columns:
            df = df[df['is_estimated'] == False]

        if df.empty:
            return self._empty_result()

        # ✅ 필수 컬럼 보장
        required_cols = ["start_in", "end_out"]
        for col in required_cols:
            if col not in df.columns:
                df[col] = pd.NaT

        # ✅ 날짜 타입 통일
        for col in required_cols:
            df[col] = self._to_excel_datetime(df[col])

        # 점유 구간 설정
        df["occ_start"] = df["start_in"]
        df["occ_end"] = df["end_out"] # 포장일 포함

        # NaT 제거
        df = df.dropna(subset=["occ_start", "occ_end"])
        if df.empty:
            return self._empty_result()

        # 날짜 범위 산출
        min_date = df["occ_start"].min().normalize()
        max_date = df["occ_end"].max().normalize()
        
        calc_start = pd.to_datetime(start_date) if start_date else min_date
        calc_end = pd.to_datetime(end_date) if end_date else max_date
        
        # 1. Delta 산출
        deltas = []
        for _, row in df.iterrows():
            area_total = row['qty'] * row['area_m2_unit']
            deltas.append({'date': row['occ_start'], 'plant': row['plant'], 'delta': area_total})
            # 포장일 다음 날 아침에 비워짐
            deltas.append({'date': row['occ_end'] + timedelta(days=1), 'plant': row['plant'], 'delta': -area_total})
            
        delta_df = pd.DataFrame(deltas)
        
        # 2. 날짜 축 생성 및 누적 합계 (Daily Baseline)
        full_dates = pd.date_range(start=min_date, end=max_date + timedelta(days=1), freq='D')
        plants = [1, 2, 3, 4, 5]
        
        # 병렬 처리 대신 순차 처리로 변경 (안정성 향상)
        daily_results = []
        for plant in plants:
            try:
                result = self._calculate_plant_occupancy(plant, delta_df, full_dates, calc_start, calc_end, capacity_df, min_date, max_date)
                daily_results.append(result)
            except Exception as e:
                print(f"공장 {plant} 처리 중 오류 발생: {e}")
            
        # daily_results가 비어있는 경우 빈 DataFrame 생성
        if not daily_results:
            daily_df = pd.DataFrame(columns=['date', 'plant', 'occupied_area', 'capacity', 'occupancy_rate'])
        else:
            daily_df = pd.concat(daily_results, ignore_index=True)

        # New Risk Metrics (Plant-centric summaries)
        threshold = 0.8
        max_date = daily_df['date'].max()
        # max_date가 NaT인 경우 처리
        if pd.isna(max_date):
            # 빈 데이터프레임일 경우 기본값 설정
            risk_summary = pd.DataFrame({
                'plant': [1, 2, 3, 4, 5],
                'recent_max_rate': [0.0, 0.0, 0.0, 0.0, 0.0],
                'recent_avg_rate': [0.0, 0.0, 0.0, 0.0, 0.0],
                'peak_month': ['No Data', 'No Data', 'No Data', 'No Data', 'No Data']
            })
            threshold_history = pd.DataFrame({
                'plant': [1, 2, 3, 4, 5],
                'over80_days': [0, 0, 0, 0, 0],
                'max_streak': [0, 0, 0, 0, 0],
                'highest_rate': [0.0, 0.0, 0.0, 0.0, 0.0],
                'status': ['🟢 안전', '🟢 안전', '🟢 안전', '🟢 안전', '🟢 안전']
            })
            # 3. [Phase 4] 리샘플링 집계 (Guardrail #3 반영)
            if granularity in ['W', 'M']:
                freq_map = {'W': 'W-MON', 'M': 'M'}
                agg_key = 'MAX' if aggregation == 'MAX' else 'AVG'
                resampled_list = []
                for plant in [1, 2, 3, 4, 5]:
                    empty_df = pd.DataFrame(columns=['date', f'OCC_RATE_{granularity}{agg_key}', f'OCC_AREA_{granularity}{agg_key}', 'plant'])
                    resampled_list.append(empty_df)
                final_df = pd.concat(resampled_list)
            else:
                final_df = daily_df.copy()
                final_df = final_df.rename(columns={
                    'occupancy_rate': 'OCC_RATE_D',
                    'occupied_area': 'OCC_AREA_D'
                })
            # 월간 요약 카드용 (기존 호환성 유지)
            monthly_summary = pd.DataFrame(columns=['plant', 'month', 'avg_area', 'max_area', 'avg_rate'])
            over_threshold = pd.DataFrame(columns=['plant', 'month', 'over_80_days'])
            result = {
                "daily_occupancy": daily_df,  # 원본 일별 데이터
                "final_df": final_df,        # 집계된 최종 데이터 (Heatmap용)
                "monthly_summary": monthly_summary,
                "over_threshold_days": over_threshold,
                "risk_summary": risk_summary,
                "threshold_history": threshold_history
            }
            # 결과를 캐시에 저장
            self._save_to_cache(cache_key, result)
            return result
            
        recent_start = max_date - timedelta(days=90)  # ~3 months
        thresh_start = max_date - timedelta(days=180)  # ~6 months

        # Ensure date sorted
        daily_df = daily_df.sort_values(['plant', 'date'])

        plants = [1, 2, 3, 4, 5]

        # 1. Risk Summary: Recent 3M per plant (Safe Merge)
        risk_base = pd.DataFrame({'plant': plants})
        recent_df = daily_df[daily_df['date'] >= recent_start].copy()
        if not recent_df.empty:
            # Agg
            agg_df = recent_df.groupby('plant')['occupancy_rate'].agg(['max', 'mean']).round(4)
            agg_df.columns = ['recent_max_rate', 'recent_avg_rate']
            agg_df = agg_df.reset_index()

            # Peak
            max_rows = recent_df.loc[recent_df.groupby('plant')['occupancy_rate'].idxmax()]
            peak_df = max_rows[['plant', 'date']].copy()
            peak_df['peak_month'] = peak_df['date'].dt.strftime('%Y-%m')
            peak_df = peak_df[['plant', 'peak_month']]

            # Merge
            risk_summary = risk_base.merge(agg_df, on='plant', how='left').fillna(0)
            risk_summary = risk_summary.merge(peak_df, on='plant', how='left')
            risk_summary['peak_month'] = risk_summary['peak_month'].fillna('No Data')
        else:
            risk_summary = risk_base.assign(recent_max_rate=0.0, recent_avg_rate=0.0, peak_month='No Data')

        # 2. Threshold History: 6M over80, streak, high
        thresh_df = daily_df[daily_df['date'] >= thresh_start].copy()
        over_df = thresh_df[thresh_df['occupancy_rate'] >= threshold]

        over_days = over_df.groupby('plant').size().reindex(plants, fill_value=0).reset_index(name='over80_days')
        highs = thresh_df.groupby('plant')['occupancy_rate'].max().reindex(plants, fill_value=0).reset_index(name='highest_rate')

        # Max streak per plant (6M)
        streaks = []
        for p in plants:
            p_daily = thresh_df[thresh_df['plant'] == p].sort_values('date')['occupancy_rate'] >= threshold
            streak = 0
            max_streak = 0
            for over in p_daily:
                if over:
                    streak += 1
                    max_streak = max(max_streak, streak)
                else:
                    streak = 0
            streaks.append({'plant': p, 'max_streak': max_streak})
        streaks_df = pd.DataFrame(streaks)

        threshold_history = over_days.merge(streaks_df, on='plant').merge(highs, on='plant')

        # Status
        def get_status(row):
            if row['highest_rate'] >= threshold:
                return '🔴 위험'
            elif row['highest_rate'] >= 0.6:
                return '🟡 주의'
            else:
                return '🟢 안전'
        threshold_history['status'] = threshold_history.apply(get_status, axis=1)

        threshold_history['highest_rate'] = threshold_history['highest_rate'].round(4)

        # 3. [Phase 4] 리샘플링 집계 (Guardrail #3 반영)
        if granularity in ['W', 'M']:
            freq_map = {'W': 'W-MON', 'M': 'M'}
            agg_key = 'MAX' if aggregation == 'MAX' else 'AVG'
            
            resampled_list = []
            for plant in plants:
                plant_data = daily_df[daily_df['plant'] == plant].set_index('date')
                if aggregation == 'MAX':
                    res = plant_data.resample(freq_map[granularity]).max()
                else:
                    res = plant_data.resample(freq_map[granularity]).mean()
                
                res['plant'] = plant
                res = res.reset_index()
                
                # 컬럼 네이밍 명시화 (Guardrail #1 관련)
                suffix = f"_{granularity}{agg_key}" # ex: _WMAX, _MAVG
                res = res.rename(columns={
                    'occupancy_rate': f'OCC_RATE_{granularity}{agg_key}',
                    'occupied_area': f'OCC_AREA_{granularity}{agg_key}'
                })
                resampled_list.append(res)
            
            final_df = pd.concat(resampled_list)
        else:
            final_df = daily_df.copy()
            final_df = final_df.rename(columns={
                'occupancy_rate': 'OCC_RATE_D',
                'occupied_area': 'OCC_AREA_D'
            })

        # 월간 요약 카드용 (기존 호환성 유지)
        monthly_summary = daily_df.set_index('date').groupby(['plant', pd.Grouper(freq='M')]).agg({
            'occupied_area': ['mean', 'max'],
            'occupancy_rate': 'mean'
        }).reset_index()
        monthly_summary.columns = ['plant', 'month', 'avg_area', 'max_area', 'avg_rate']
        
        over_threshold = daily_df[daily_df['occupancy_rate'] >= 0.8].groupby(['plant', pd.Grouper(key='date', freq='M')]).size().reset_index(name='over_80_days')
        
        result = {
            "daily_occupancy": daily_df,  # 원본 일별 데이터
            "final_df": final_df,        # 집계된 최종 데이터 (Heatmap용)
            "monthly_summary": monthly_summary,
            "over_threshold_days": over_threshold,
            "risk_summary": risk_summary,
            "threshold_history": threshold_history
        }
        
        # 결과를 캐시에 저장
        self._save_to_cache(cache_key, result)
        
        return result
