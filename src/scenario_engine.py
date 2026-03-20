import pandas as pd
import numpy as np
from datetime import datetime, date
from src.occupancy_engine import OccupancyEngine

class ScenarioEngine:
    def __init__(self, base_orders: pd.DataFrame, base_capacity: pd.DataFrame):
        self.base_orders = base_orders.copy()
        self.base_capacity = base_capacity.copy()
        self.engine = OccupancyEngine()
        self.virtual_orders = []

    def load_virtual_orders(self, v_list: list):
        """Set virtual orders from an external list (e.g., from session_state)"""
        self.virtual_orders = v_list

    def add_virtual_order(self, order_dict: dict):
        """Add a single virtual order"""
        if not order_dict:
            return
        self.virtual_orders.append(order_dict)

    def get_combined_orders(self) -> pd.DataFrame:
        """Combine base orders with virtual orders"""
        if not self.virtual_orders:
            return self.base_orders
        
        # Convert list of dicts to DataFrame
        v_df = pd.DataFrame(self.virtual_orders)
        
        # Ensure compatibility with base_orders schema
        # Required columns for calculation: 'start_in', 'end_out', 'plant', 'area_m2_unit', 'qty'
        # Additional columns for filtering/display: 'data_mode', 'is_estimated', 'row_type'
        
        # Default values for virtual orders
        if 'data_mode' not in v_df.columns:
            v_df['data_mode'] = 'plan'  # Virtual orders are always plan
        if 'is_estimated' not in v_df.columns:
            v_df['is_estimated'] = False
        if 'row_type' not in v_df.columns:
            v_df['row_type'] = 'SCENARIO' # Identify virtual orders
        if 'is_included' not in v_df.columns:
            v_df['is_included'] = True

        # Ensure types (date conversion handled by OccupancyEngine._to_excel_datetime but let's pre-process if needed)
        # Assuming input is already datetime or string 'YYYY-MM-DD'
        
        combined = pd.concat([self.base_orders, v_df], ignore_index=True)
        return combined

    def simulate(self, start_date, end_date, mode='plan', granularity='D', aggregation='MAX'):
        """Run occupancy calculation for the combined scenario"""
        combined_orders = self.get_combined_orders()
        
        # 1. Base Result (Baseline)
        base_res = self.engine.calculate_daily_occupancy(
            self.base_orders, self.base_capacity,
            start_date=start_date, end_date=end_date,
            mode=mode, granularity=granularity, aggregation=aggregation
        )

        # 2. Simulation Result (Combined)
        sim_res = self.engine.calculate_daily_occupancy(
            combined_orders, self.base_capacity,
            start_date=start_date, end_date=end_date,
            mode=mode, granularity=granularity, aggregation=aggregation
        )
        
        return {
            "base": base_res,
            "simulation": sim_res,
            "delta": self._calculate_delta(base_res, sim_res, granularity, aggregation)
        }

    def _calculate_delta(self, base_res, sim_res, granularity, aggregation):
        """Calculate the difference between base and simulation results"""
        base_df = base_res['final_df']
        sim_df = sim_res['final_df']

        if base_df.empty or sim_df.empty:
            return pd.DataFrame() # No comparison possible

        # Pivot DataFrames to align by (plant, date)
        # Using the metric columns (OCC_RATE_..., OCC_AREA_...)
        # We need to compute delta for BOTH rate and area if possible, or just the main one.
        # Let's compute delta for 'OCC_RATE_{gran}{agg}' and 'OCC_AREA_{gran}{agg}'
        
        suffix = ""
        if granularity == 'D':
            suffix_rate = "_D"
            suffix_area = "_D"
        else:
            suffix_rate = f"_{granularity}{aggregation}"
            suffix_area = f"_{granularity}{aggregation}"
            
        rate_col = f"OCC_RATE{suffix_rate}"
        area_col = f"OCC_AREA{suffix_area}"
        
        # Pivot both
        base_pivot = base_df.pivot(index='plant', columns='date', values=rate_col)
        sim_pivot = sim_df.pivot(index='plant', columns='date', values=rate_col)
        
        # Align indexes and columns (union) to handle new dates in simulation
        aligned_base, aligned_sim = base_pivot.align(sim_pivot, join='outer', fill_value=0)
        
        delta_df = aligned_sim - aligned_base
        
        return delta_df
