import pandas as pd
from datetime import datetime, timedelta

# 1. Orders Sample Data (정상, 오류 케이스 포함)
orders_data = [
    # 정상 주문
    ["ORD-001", "MODEL-A", 1, 1, 50.0, "2026-02-01", "2026-02-10", "actual"],
    ["ORD-002", "MODEL-B", 2, 2, 30.0, "2026-02-05", "2026-02-15", "actual"],
    ["ORD-003", "MODEL-C", 1, 1, 100.0, "2026-02-08", "2026-02-20", "planned"],
    # end_out 공란 (예측 대상)
    ["ORD-004", "MODEL-A", 1, 3, 50.0, "2026-02-10", None, "actual"],
    # 오류 케이스: 날짜 역전
    ["ORD-005", "MODEL-B", 1, 4, 40.0, "2026-02-15", "2026-02-10", "planned"],
    # 오류 케이스: 수량 0
    ["ORD-006", "MODEL-C", 0, 5, 20.0, "2026-02-20", "2026-02-25", "planned"],
    # 오류 케이스: 잘못된 plant
    ["ORD-007", "MODEL-A", 1, 6, 50.0, "2026-02-25", "2026-02-28", "planned"]
]

orders_df = pd.DataFrame(orders_data, columns=[
    'order_id', 'model', 'qty', 'plant', 'area_m2_unit', 'start_in', 'end_out', 'status'
])
orders_df.to_csv(r"d:\Plant_Area\orders_sample.csv", index=False)

# 2. Capacity Sample Data
capacity_data = [
    [1, 1000.0, "2026-01-01", "2026-06-30"],
    [2, 800.0, "2026-01-01", "2026-12-31"],
    [3, 1200.0, "2026-01-01", "2026-12-31"],
    [1, 1500.0, "2026-07-01", "2026-12-31"], # 동 면적 변경 (레이아웃 변경 시뮬레이션)
    [4, 500.0, "2026-01-01", "2026-12-31"],
    [5, 600.0, "2026-01-01", "2026-12-31"]
]

capacity_df = pd.DataFrame(capacity_data, columns=[
    'plant', 'capacity_m2', 'effective_from', 'effective_to'
])
capacity_df.to_csv(r"d:\Plant_Area\capacity_sample.csv", index=False)

print("Sample files created: orders_sample.csv, capacity_sample.csv")
