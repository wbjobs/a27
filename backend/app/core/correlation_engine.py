import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sklearn.linear_model import LinearRegression
import logging

logger = logging.getLogger(__name__)


class FactorCorrelationAnalyzer:
    def analyze(
        self,
        factor_values_list: List[Dict[str, Any]],
        vif_threshold: float = 10.0,
        corr_threshold: float = 0.7
    ) -> Dict[str, Any]:
        if len(factor_values_list) < 2:
            return {
                "success": False,
                "message": "至少需要2个因子才能进行相关性分析",
                "correlation_matrix": None,
                "vif_values": None,
                "collinear_pairs": None,
                "removed_factors": None,
                "kept_factors": None
            }

        factor_dfs = {}
        for item in factor_values_list:
            name = item.get("name", "unnamed")
            values = item.get("values", [])
            if not values:
                continue
            df = pd.DataFrame(values)
            if 'ts_code' not in df.columns or 'trade_date' not in df.columns:
                col_map = {}
                for c in df.columns:
                    cl = c.lower()
                    if 'code' in cl:
                        col_map[c] = 'ts_code'
                    elif 'date' in cl or 'time' in cl:
                        col_map[c] = 'trade_date'
                    elif 'factor' in cl or 'value' in cl:
                        col_map[c] = 'factor_value'
                df = df.rename(columns=col_map)
            
            if 'ts_code' in df.columns and 'trade_date' in df.columns and 'factor_value' in df.columns:
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                df = df.set_index(['ts_code', 'trade_date'])['factor_value']
                factor_dfs[name] = df

        if len(factor_dfs) < 2:
            return {
                "success": False,
                "message": f"有效因子仅{len(factor_dfs)}个，需要至少2个",
                "correlation_matrix": None,
                "vif_values": None,
                "collinear_pairs": None,
                "removed_factors": None,
                "kept_factors": None
            }

        combined = pd.DataFrame(factor_dfs)
        combined = combined.dropna()
        
        if combined.empty or len(combined) < 10:
            return {
                "success": False,
                "message": f"对齐后数据不足({len(combined)}行)，无法进行相关性分析",
                "correlation_matrix": None,
                "vif_values": None,
                "collinear_pairs": None,
                "removed_factors": None,
                "kept_factors": None
            }

        corr_matrix = combined.corr()
        corr_records = []
        names = list(corr_matrix.columns)
        for i, name_i in enumerate(names):
            for j, name_j in enumerate(names):
                corr_records.append({
                    "row": name_i,
                    "col": name_j,
                    "value": round(float(corr_matrix.iloc[i, j]), 4)
                })

        vif_values = self._calculate_vif(combined)

        collinear_pairs = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                corr_val = abs(corr_matrix.iloc[i, j])
                if corr_val >= corr_threshold:
                    collinear_pairs.append({
                        "factor_a": names[i],
                        "factor_b": names[j],
                        "correlation": round(float(corr_matrix.iloc[i, j]), 4),
                        "abs_correlation": round(float(corr_val), 4)
                    })

        removed, kept = self._remove_collinear(combined, vif_values, vif_threshold, corr_threshold)

        return {
            "success": True,
            "message": f"分析了{len(names)}个因子, 发现{len(collinear_pairs)}对高度相关",
            "correlation_matrix": corr_records,
            "vif_values": vif_values,
            "collinear_pairs": collinear_pairs,
            "removed_factors": removed,
            "kept_factors": kept
        }

    def _calculate_vif(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        names = list(df.columns)
        vif_results = []
        
        for i, name in enumerate(names):
            y = df[name].values
            X_cols = [names[j] for j in range(len(names)) if j != i]
            X = df[X_cols].values
            
            if X.shape[1] == 0:
                vif_results.append({"name": name, "vif": float('inf')})
                continue
            
            try:
                lr = LinearRegression()
                lr.fit(X, y)
                r_squared = lr.score(X, y)
                if r_squared >= 1.0:
                    vif = float('inf')
                elif r_squared < 0.01:
                    vif = 1.0
                else:
                    vif = 1.0 / (1.0 - r_squared)
                vif_results.append({"name": name, "vif": round(float(vif), 4)})
            except Exception:
                vif_results.append({"name": name, "vif": float('inf')})
        
        return vif_results

    def _remove_collinear(
        self,
        df: pd.DataFrame,
        vif_values: List[Dict[str, Any]],
        vif_threshold: float,
        corr_threshold: float
    ) -> Tuple[List[str], List[str]]:
        remaining = [v["name"] for v in vif_values]
        
        for iteration in range(len(vif_values)):
            current_vifs = [v for v in vif_values if v["name"] in remaining]
            high_vif = [v for v in current_vifs if v["vif"] > vif_threshold]
            
            if not high_vif:
                break
            
            worst = max(high_vif, key=lambda x: x["vif"])
            
            sub_df = df[remaining]
            corr = sub_df.corr()
            worst_idx = remaining.index(worst["name"])
            max_corr_with_others = 0
            for j, other in enumerate(remaining):
                if j != worst_idx:
                    max_corr_with_others = max(max_corr_with_others, abs(corr.loc[worst["name"], other]))
            
            if max_corr_with_others >= corr_threshold:
                remaining.remove(worst["name"])
            else:
                break
        
        removed = [v["name"] for v in vif_values if v["name"] not in remaining]
        return removed, remaining


factor_correlation_analyzer = FactorCorrelationAnalyzer()
