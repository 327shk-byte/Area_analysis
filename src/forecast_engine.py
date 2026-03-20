import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Literal, Dict, Any
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')

# ARIMA 모델을 위한 추가 import
try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.stattools import adfuller
    ARIMA_AVAILABLE = True
except ImportError:
    ARIMA_AVAILABLE = False
    print("ARIMA 모델을 사용하려면 'pip install statsmodels'를 실행하세요.")

@dataclass
class ForecastParams:
    horizon_periods: int = 12
    threshold: float = 0.8
    model_type: str = "linear"  # "linear", "moving_average", "arima"
    confidence_level: float = 0.95
    period_days: int = 1  # 1: 일간, 7: 주간, 30: 월간

class ForecastEngine:
    def __init__(self):
        self.models = {}
        self.metrics = {}
    
    def prepare_data(self, occupancy_data: pd.DataFrame) -> pd.DataFrame:
        """점유율 데이터를 예측을 위한 시계열 데이터로 변환"""
        if occupancy_data.empty:
            return pd.DataFrame()
        
        # 일별 데이터로 그룹화하여 평균 점유율 계산
        df = occupancy_data.copy()
        df['date'] = pd.to_datetime(df['date'])
        
        # 동별로 분리하여 처리
        forecast_data = []
        for plant in df['plant'].unique():
            plant_data = df[df['plant'] == plant].copy()
            plant_data = plant_data.sort_values('date')
            plant_data['plant'] = plant
            forecast_data.append(plant_data)
        
        return pd.concat(forecast_data) if forecast_data else pd.DataFrame()
    
    def _linear_forecast(self, data: pd.DataFrame, params: ForecastParams) -> Dict[str, Any]:
        """선형 회귀 기반 예측"""
        if len(data) < 2:
            return {"forecast": pd.DataFrame(), "metrics": {}}
        
        # 날짜를 숫자로 변환 (주기 간격 기준)
        data = data.sort_values('date')
        start_date = data['date'].min()
        data['periods_from_start'] = (data['date'] - start_date).dt.days / params.period_days
        
        # 선형 회귀 모델 학습
        X = data['periods_from_start'].values.reshape(-1, 1)
        y = data['occupancy_rate'].values
        
        model = LinearRegression()
        model.fit(X, y)
        
        # 미래 예측
        last_period = data['periods_from_start'].max()
        future_periods = np.arange(last_period + 1, last_period + params.horizon_periods + 1).reshape(-1, 1)
        forecast_values = model.predict(future_periods)
        
        # 예측 결과를 DataFrame으로 변환
        future_dates = [start_date + timedelta(days=int(p[0] * params.period_days)) for p in future_periods]
        forecast_df = pd.DataFrame({
            'date': future_dates,
            'plant': data['plant'].iloc[0],
            'forecast_occupancy_rate': np.clip(forecast_values, 0, 1),  # 0~1 사이로 클리핑
            'model': 'linear'
        })
        
        # 모델 성능 평가 (과거 데이터에 대한 예측 정확도)
        y_pred = model.predict(X)
        mae = mean_absolute_error(y, y_pred)
        rmse = np.sqrt(mean_squared_error(y, y_pred))
        
        metrics = {
            'mae': mae,
            'rmse': rmse,
            'model_type': 'linear'
        }
        
        return {"forecast": forecast_df, "metrics": metrics}
    
    def _moving_average_forecast(self, data: pd.DataFrame, params: ForecastParams) -> Dict[str, Any]:
        """이동 평균 기반 예측"""
        if len(data) < 7:  # 최소 7일 데이터 필요
            return self._linear_forecast(data, params)  # 데이터 부족시 선형 회귀로 대체
        
        data = data.sort_values('date')
        window = min(7, len(data))  # 최대 7일 이동 평균
        avg_rate = data['occupancy_rate'].tail(window).mean()
        
        # 미래 예측 (상수 예측)
        last_date = data['date'].max()
        future_dates = [last_date + timedelta(days=i * params.period_days) for i in range(1, params.horizon_periods + 1)]
        
        forecast_df = pd.DataFrame({
            'date': future_dates,
            'plant': data['plant'].iloc[0],
            'forecast_occupancy_rate': avg_rate,
            'model': 'moving_average'
        })
        
        # 단순 상수 예측이므로 성능 메트릭 계산이 제한적임
        metrics = {
            'mae': np.nan,
            'rmse': np.nan,
            'model_type': 'moving_average'
        }
        
        return {"forecast": forecast_df, "metrics": metrics}
    
    def _arima_forecast(self, data: pd.DataFrame, params: ForecastParams) -> Dict[str, Any]:
        """ARIMA 기반 예측"""
        if not ARIMA_AVAILABLE:
            # ARIMA 라이브러리가 없으면 선형 회귀로 대체
            return self._linear_forecast(data, params)
        
        if len(data) < 10:  # 최소 10일 데이터 필요
            return self._linear_forecast(data, params)  # 데이터 부족시 선형 회귀로 대체
        
        try:
            data = data.sort_values('date')
            data.set_index('date', inplace=True)
            
            # 시계열 데이터 준비
            ts = data['occupancy_rate']
            
            # 정상성 검정 (ADF 테스트)
            result = adfuller(ts)
            p_value = result[1]
            
            # 차분이 필요한 경우 (p-value > 0.05)
            d = 0
            if p_value > 0.05:
                d = 1
                ts_diff = ts.diff().dropna()
                result_diff = adfuller(ts_diff)
                if result_diff[1] > 0.05:
                    d = 2  # 2차 차분
            
            # ARIMA 모델 학습 (자동 파라미터 선택)
            # 간단한 파라미터로 시작 (1, d, 1)
            model = ARIMA(ts, order=(1, d, 1))
            fitted_model = model.fit()
            
            # 미래 예측
            forecast_result = fitted_model.forecast(steps=params.horizon_periods)
            forecast_values = forecast_result.values
            
            # 예측 결과를 DataFrame으로 변환
            last_date = data.index.max()
            future_dates = [last_date + timedelta(days=i * params.period_days) for i in range(1, params.horizon_periods + 1)]
            forecast_df = pd.DataFrame({
                'date': future_dates,
                'plant': data['plant'].iloc[0],
                'forecast_occupancy_rate': np.clip(forecast_values, 0, 1),  # 0~1 사이로 클리핑
                'model': 'arima'
            })
            
            # 모델 성능 평가 (과거 데이터에 대한 예측 정확도)
            # in-sample 예측
            in_sample_pred = fitted_model.fittedvalues
            mae = mean_absolute_error(ts[d:], in_sample_pred[d:])  # 차분된 부분 제외
            rmse = np.sqrt(mean_squared_error(ts[d:], in_sample_pred[d:]))
            
            metrics = {
                'mae': mae,
                'rmse': rmse,
                'model_type': 'arima'
            }
            
            return {"forecast": forecast_df, "metrics": metrics}
            
        except Exception as e:
            # ARIMA 모델 학습 실패시 선형 회귀로 대체
            data.reset_index(inplace=True)
            return self._linear_forecast(data, params)
    
    def forecast_occupancy(self, occupancy_data: pd.DataFrame, params: ForecastParams = None) -> Dict[str, Any]:
        """점유율 예측 수행"""
        if params is None:
            params = ForecastParams()
        
        # 데이터 준비
        prepared_data = self.prepare_data(occupancy_data)
        if prepared_data.empty:
            return {"forecast": pd.DataFrame(), "metrics": {}}
        
        # 동별로 예측 수행
        all_forecasts = []
        all_metrics = {}
        
        for plant in prepared_data['plant'].unique():
            plant_data = prepared_data[prepared_data['plant'] == plant]
            
            if params.model_type == "linear":
                result = self._linear_forecast(plant_data, params)
            elif params.model_type == "moving_average":
                result = self._moving_average_forecast(plant_data, params)
            elif params.model_type == "arima":
                result = self._arima_forecast(plant_data, params)
            else:
                # 기본적으로 선형 회귀 사용
                result = self._linear_forecast(plant_data, params)
            
            if not result["forecast"].empty:
                all_forecasts.append(result["forecast"])
                all_metrics[f"plant_{plant}"] = result["metrics"]
        
        forecast_df = pd.concat(all_forecasts) if all_forecasts else pd.DataFrame()
        
        return {
            "forecast": forecast_df,
            "metrics": all_metrics,
            "params": params
        }
    
    def evaluate_risk_periods(self, forecast_data: pd.DataFrame, threshold: float = 0.8) -> pd.DataFrame:
        """예측된 위험 기간 식별"""
        if forecast_data.empty:
            return pd.DataFrame()
        
        # 임계치를 초과하는 기간 식별
        risk_periods = forecast_data[forecast_data['forecast_occupancy_rate'] >= threshold].copy()
        risk_periods['risk_level'] = risk_periods['forecast_occupancy_rate'].apply(
            lambda x: 'high' if x >= 0.9 else 'medium' if x >= 0.8 else 'low'
        )
        
        return risk_periods.sort_values(['plant', 'date'])
