import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import hashlib
import json

class OccupancyEngine:
    def __init__(self):
        self._cache = {}
    
    def _generate_cache_key(self, orders_df, capacity_df, start_date, end_date, mode, include_estimated, granularity, aggregation, threshold):
        """계산 조건에 따라 캐시 키 생성"""
        orders_hash = hashlib.md5(pd.util.hash_pandas_object(orders_df, index=False).values.tobytes()).hexdigest()
        capacity_hash = hashlib.md5(pd.util.hash_pandas_object(capacity_df, index=False).values.tobytes()).hexdigest()
        conditions = {
            "orders_hash": orders_hash, "capacity_hash": capacity_hash,
            "start_date": str(start_date), "end_date": str(end_date),
            "mode": mode, "include_estimated": include_estimated,
            "granularity": granularity, "aggregation": aggregation, "threshold": threshold
        }
        return hashlib.md5(json.dumps(conditions, sort_keys=True).encode()).hexdigest()
    
    def _get_from_cache(self, cache_key):
        return self._cache.get(cache_key)
    
    def _save_to_cache(self, cache_key, result):
        if len(self._cache) >= 10:
            del self._cache[next(iter(self._cache))]
        self._cache[cache_key] = result

    def _to_excel_datetime(self, s: pd.Series) -> pd.Series:
        s2 = s.copy()
        num = pd.to_numeric(s2, errors="coerce")
        is_excel_serial = num.between(20000, 60000)
        out = pd.Series(pd.NaT, index=s2.index, dtype="datetime64[ns]")
        if is_excel_serial.any():
            out.loc[is_excel_serial] = pd.to_datetime(num.loc[is_excel_serial], unit="D", origin="1899-12-30", errors="coerce")
        rest = ~is_excel_serial
        if rest.any():
            out.loc[rest] = pd.to_datetime(s2.loc[rest], errors="coerce")
        return out

    def _empty_result(self) -> dict:
        return {
            "daily_occupancy": pd.DataFrame(), "final_df": pd.DataFrame(),
            "risk_summary": pd.DataFrame(), "threshold_history": pd.DataFrame()
        }

    def _calculate_plant_occupancy(self, plant, delta_df, full_dates, calc_start, calc_end, capacity_df):
        plant_delta = delta_df[delta_df['plant'] == plant].groupby('date')['delta'].sum().reindex(full_dates, fill_value=0)
        plant_occ = plant_delta.cumsum()
        mask = (full_dates >= calc_start) & (full_dates <= calc_end)
        dates_sliced = full_dates[mask]
        occ_sliced = plant_occ[mask]
        plant_cap_info = capacity_df[capacity_df['plant'] == plant]
        caps = []
        for d in dates_sliced:
            cap_row = plant_cap_info[(plant_cap_info['effective_from'] <= d) & (plant_cap_info['effective_to'] >= d)]
            caps.append(cap_row.iloc[0]['capacity_m2'] if not cap_row.empty else np.nan)
        p_df = pd.DataFrame({'date': dates_sliced, 'plant': plant, 'occupied_area': occ_sliced.values, 'capacity': caps})
        p_df['occupied_area'] = p_df['occupied_area'].clip(lower=0)
        p_df['occupancy_rate'] = (p_df['occupied_area'] / p_df['capacity']).fillna(0).clip(lower=0)
        return p_df

    def calculate_daily_occupancy(self, orders_df: pd.DataFrame, capacity_df: pd.DataFrame, 
                                 start_date=None, end_date=None, 
                                 mode='plan', include_estimated=True,
                                 granularity='D', aggregation='MAX',
                                 threshold=0.8) -> dict:
        cache_key = self._generate_cache_key(orders_df, capacity_df, start_date, end_date, mode, include_estimated, granularity, aggregation, threshold)
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None: return cached_result

        if orders_df.empty: return self._empty_result()
        df = orders_df.copy()
        if 'data_mode' in df.columns and mode in ['plan', 'actual']:
            df = df[df['data_mode'] == mode]
        if not include_estimated and 'is_estimated' in df.columns:
            df = df[df['is_estimated'] == False]
        if df.empty: return self._empty_result()

        for col in ["start_in", "end_out"]:
            if col not in df.columns: df[col] = pd.NaT
            df[col] = self._to_excel_datetime(df[col])

        df["occ_start"], df["occ_end"] = df["start_in"], df["end_out"]
        df = df.dropna(subset=["occ_start", "occ_end"])
        if df.empty: return self._empty_result()

        min_date, max_date = df["occ_start"].min().normalize(), df["occ_end"].max().normalize()
        calc_start = pd.to_datetime(start_date) if start_date else min_date
        calc_end = pd.to_datetime(end_date) if end_date else max_date
        
        deltas = []
        for _, row in df.iterrows():
            area_total = row['qty'] * row['area_m2_unit']
            deltas.append({'date': row['occ_start'], 'plant': row['plant'], 'delta': area_total})
            deltas.append({'date': row['occ_end'] + timedelta(days=1), 'plant': row['plant'], 'delta': -area_total})
        delta_df = pd.DataFrame(deltas)
        full_dates = pd.date_range(start=min_date, end=max_date + timedelta(days=1), freq='D')
        
        daily_results = [self._calculate_plant_occupancy(p, delta_df, full_dates, calc_start, calc_end, capacity_df) for p in [1, 2, 3, 4, 5]]
        daily_df = pd.concat(daily_results, ignore_index=True)

        # Risk Metrics
        max_date_actual = daily_df['date'].max()
        if pd.isna(max_date_actual): return self._empty_result()
        recent_start, thresh_start = max_date_actual - timedelta(days=90), max_date_actual - timedelta(days=180)
        daily_df = daily_df.sort_values(['plant', 'date'])

        # 1. Risk Summary
        recent_df = daily_df[daily_df['date'] >= recent_start].copy()
        if not recent_df.empty:
            agg_df = recent_df.groupby('plant')['occupancy_rate'].agg(['max', 'mean']).round(4).reset_index()
            agg_df.columns = ['plant', 'recent_max_rate', 'recent_avg_rate']
            max_rows = recent_df.loc[recent_df.groupby('plant')['occupancy_rate'].idxmax()]
            peak_df = max_rows[['plant', 'date']].copy()
            peak_df['peak_month'] = peak_df['date'].dt.strftime('%Y-%m')
            risk_summary = pd.DataFrame({'plant': [1,2,3,4,5]}).merge(agg_df, on='plant', how='left').fillna(0).merge(peak_df[['plant', 'peak_month']], on='plant', how='left').fillna('No Data')
        else:
            risk_summary = pd.DataFrame({'plant': [1,2,3,4,5]}).assign(recent_max_rate=0.0, recent_avg_rate=0.0, peak_month='No Data')

        # 2. Threshold History
        thresh_df = daily_df[daily_df['date'] >= thresh_start].copy()
        over_days = thresh_df[thresh_df['occupancy_rate'] >= threshold].groupby('plant').size().reindex([1,2,3,4,5], fill_value=0).reset_index(name='over_threshold_days')
        highs = thresh_df.groupby('plant')['occupancy_rate'].max().reindex([1,2,3,4,5], fill_value=0).reset_index(name='highest_rate')
        streaks = []
        for p in [1,2,3,4,5]:
            p_daily = thresh_df[thresh_df['plant'] == p].sort_values('date')['occupancy_rate'] >= threshold
            streak, max_streak = 0, 0
            for over in p_daily:
                if over: streak += 1; max_streak = max(max_streak, streak)
                else: streak = 0
            streaks.append({'plant': p, 'max_streak': max_streak})
        threshold_history = over_days.merge(pd.DataFrame(streaks), on='plant').merge(highs, on='plant')
        threshold_history['status'] = threshold_history['highest_rate'].apply(lambda r: '🔴 위험' if r >= threshold else ('🟡 주의' if r >= threshold*0.75 else '🟢 안전'))
        threshold_history['highest_rate'] = threshold_history['highest_rate'].round(4)

        # 3. Final DF Aggregation
        if granularity in ['W', 'M']:
            freq_map, agg_key = {'W': 'W-MON', 'M': 'M'}, ('MAX' if aggregation == 'MAX' else 'AVG')
            resampled_list = []
            for p in [1,2,3,4,5]:
                p_data = daily_df[daily_df['plant'] == p].set_index('date')
                res = p_data.resample(freq_map[granularity]).max() if aggregation == 'MAX' else p_data.resample(freq_map[granularity]).mean()
                res['plant'] = p
                res = res.reset_index().rename(columns={'occupancy_rate': f'OCC_RATE_{granularity}{agg_key}', 'occupied_area': f'OCC_AREA_{granularity}{agg_key}'})
                resampled_list.append(res)
            final_df = pd.concat(resampled_list)
        else: final_df = daily_df.copy().rename(columns={'occupancy_rate': 'OCC_RATE_D', 'occupied_area': 'OCC_AREA_D'})

        result = {"daily_occupancy": daily_df, "final_df": final_df, "risk_summary": risk_summary, "threshold_history": threshold_history}
        self._save_to_cache(cache_key, result)
        return result
