import pandas as pd
from datetime import datetime, date
import sys

from src.scenario_engine import ScenarioEngine
from src.occupancy_engine import OccupancyEngine

try:
    # 1. Create dummy base orders
    base_orders = pd.DataFrame({
        'order_id': ['B1', 'B2'],
        'customer': ['C1', 'C2'],
        'model': ['M1', 'M2'],
        'qty': [10, 20],
        'plant': [1, 2],
        'area_m2_unit': [2.0, 3.0],
        'start_in': [date(2025, 1, 1), date(2025, 1, 10)],
        'end_out': [date(2025, 1, 5), date(2025, 1, 15)],
        'data_mode': ['plan', 'plan'],
        'is_estimated': [False, False],
        'row_type': ['DATA', 'DATA']
    })

    base_capa = pd.DataFrame({
        'plant': [1, 2, 3, 4, 5],
        'capacity_m2': [1000.0, 1000.0, 1000.0, 1000.0, 1000.0],
        'effective_from': [pd.to_datetime('2000-01-01')] * 5,
        'effective_to': [pd.to_datetime('2099-12-31')] * 5
    })

    engine = ScenarioEngine(base_orders, base_capa)
    
    # 2. Virtual orders
    engine.load_virtual_orders([{
        "order_id": "VIRTUAL-1",
        "customer": "V-Cust",
        "model": "V-Model",
        "qty": 50,
        "plant": 1,
        "area_m2_unit": 5.0,
        "start_in": date(2025, 1, 3),
        "end_out": date(2025, 1, 8),
        "data_mode": "plan",
        "is_estimated": False,
        "row_type": "SCENARIO"
    }])

    print("Running simulate...")
    # 3. Simulate
    res = engine.simulate(start_date=date(2025, 1, 1), end_date=date(2025, 1, 20), mode='plan', granularity='D', aggregation='MAX')

    print("Simulation completed.")
    print("Keys:", res.keys())
    print("Delta shape:", res['delta'].shape)
    print(res['delta'].head())
except Exception as e:
    import traceback
    traceback.print_exc()
