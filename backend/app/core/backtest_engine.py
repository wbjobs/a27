import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from scipy import stats as scipy_stats
from datetime import datetime
import logging

from app.core.duckdb_engine import duckdb_engine
from app.models.schemas import (
    BacktestRequest, ICStats, GroupReturns, TurnoverStats, BacktestResult
)

logger = logging.getLogger(__name__)


class BacktestEngine:
    def __init__(self):
        self._code_col = None
        self._date_col = None
        self._close_col = None
    
    def _resolve_columns(self, dataset_name: str):
        info = duckdb_engine.get_table_info(dataset_name)
        if not info:
            raise ValueError(f"Dataset {dataset_name} not found")
        
        cols = info["columns"]
        cols_lower = {c.lower(): c for c in cols}
        
        code_candidates = ["ts_code", "code", "symbol", "stock_code"]
        self._code_col = next((cols_lower[c] for c in code_candidates if c in cols_lower), None)
        self._date_col = next((c for c in cols if 'date' in c.lower() or 'time' in c.lower()), None)
        self._close_col = cols_lower.get("close", cols_lower.get("收盘", cols[0]))
    
    def _get_future_returns(
        self,
        dataset_name: str,
        holding_period: int = 1,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        stock_codes: Optional[List[str]] = None
    ) -> pd.DataFrame:
        self._resolve_columns(dataset_name)
        
        if not self._code_col or not self._date_col:
            raise ValueError("Missing required columns (code/date)")
        
        query_cols = [self._code_col, self._date_col, self._close_col]
        df = duckdb_engine.query_data(
            dataset_name,
            columns=query_cols,
            stock_codes=stock_codes,
            start_date=start_date,
            end_date=end_date
        )
        
        df[self._date_col] = pd.to_datetime(df[self._date_col])
        df = df.sort_values([self._code_col, self._date_col])
        
        returns_list = []
        for code, group in df.groupby(self._code_col):
            group = group.sort_values(self._date_col).copy()
            group['future_return'] = group[self._close_col].pct_change(holding_period).shift(-holding_period)
            returns_list.append(group[[self._code_col, self._date_col, 'future_return']])
        
        returns_df = pd.concat(returns_list, ignore_index=True)
        returns_df.columns = ['ts_code', 'trade_date', 'future_return']
        return returns_df
    
    def _align_data(
        self,
        factor_df: pd.DataFrame,
        returns_df: pd.DataFrame
    ) -> pd.DataFrame:
        factor_df['trade_date'] = pd.to_datetime(factor_df['trade_date'])
        returns_df['trade_date'] = pd.to_datetime(returns_df['trade_date'])
        
        merged = pd.merge(
            factor_df, returns_df,
            on=['ts_code', 'trade_date'],
            how='inner'
        )
        merged = merged.dropna(subset=['factor_value', 'future_return'])
        merged = merged.sort_values(['trade_date', 'ts_code'])
        return merged
    
    def _calculate_ic(self, aligned_df: pd.DataFrame) -> ICStats:
        ic_values = []
        
        for date, group in aligned_df.groupby('trade_date'):
            if len(group) < 5:
                continue
            ic, p_val = scipy_stats.spearmanr(group['factor_value'], group['future_return'])
            if not np.isnan(ic):
                ic_values.append({
                    "trade_date": date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                    "ic": float(ic),
                    "p_value": float(p_val) if not np.isnan(p_val) else 1.0
                })
        
        if not ic_values:
            return ICStats(
                mean_ic=0, ic_std=0, icir=0, t_stat=0, p_value=1,
                ic_values=[]
            )
        
        ic_series = pd.Series([x["ic"] for x in ic_values])
        mean_ic = float(ic_series.mean())
        ic_std = float(ic_series.std()) if len(ic_series) > 1 else 0
        icir = mean_ic / ic_std if ic_std != 0 else 0
        t_stat, p_value = scipy_stats.ttest_1samp(ic_series, 0) if len(ic_series) > 1 else (0, 1)
        
        return ICStats(
            mean_ic=mean_ic,
            ic_std=ic_std,
            icir=float(icir),
            t_stat=float(t_stat) if not np.isnan(t_stat) else 0,
            p_value=float(p_value) if not np.isnan(p_value) else 1,
            ic_values=ic_values
        )
    
    def _calculate_group_returns(
        self,
        aligned_df: pd.DataFrame,
        n_groups: int = 5,
        commission_rate: float = 0.0003
    ) -> Tuple[List[GroupReturns], Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
        all_dates = sorted(aligned_df['trade_date'].unique())
        group_returns_data = {g: [] for g in range(1, n_groups + 1)}
        group_cumulative = {g: 1.0 for g in range(1, n_groups + 1)}
        cumulative_records = {g: [] for g in range(1, n_groups + 1)}
        prev_groups = {}
        turnover_by_period = []
        heatmap_records = []
        
        for date in all_dates:
            date_group = aligned_df[aligned_df['trade_date'] == date].copy()
            if len(date_group) < n_groups * 2:
                continue
            
            date_group['group'] = pd.qcut(
                date_group['factor_value'].rank(method='first'),
                q=n_groups,
                labels=range(1, n_groups + 1),
                duplicates='drop'
            )
            date_group = date_group.dropna(subset=['group'])
            
            period_turnover = 0.0
            for g in range(1, n_groups + 1):
                g_data = date_group[date_group['group'] == g]
                if len(g_data) == 0:
                    continue
                
                avg_ret = float(g_data['future_return'].mean())
                current_codes = set(g_data['ts_code'].values)
                
                if prev_groups and g in prev_groups:
                    prev_codes = prev_groups[g]
                    if len(prev_codes) > 0 and len(current_codes) > 0:
                        changed = len(current_codes - prev_codes)
                        total = max(len(current_codes), len(prev_codes))
                        turnover = changed / total
                        period_turnover += turnover / n_groups
                        avg_ret -= turnover * commission_rate * 2
                
                group_cumulative[g] *= (1 + avg_ret)
                group_returns_data[g].append({
                    "trade_date": date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                    "return": avg_ret
                })
                cumulative_records[g].append({
                    "trade_date": date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                    "cumulative_return": group_cumulative[g] - 1
                })
                heatmap_records.append({
                    "trade_date": date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                    "group": int(g),
                    "return": avg_ret
                })
            
            turnover_by_period.append({
                "trade_date": date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                "turnover": period_turnover
            })
            
            prev_groups = {}
            for g in range(1, n_groups + 1):
                g_data = date_group[date_group['group'] == g]
                prev_groups[g] = set(g_data['ts_code'].values)
        
        group_results = []
        for g in range(1, n_groups + 1):
            if not group_returns_data[g]:
                continue
            
            returns_series = pd.Series([r["return"] for r in group_returns_data[g]])
            cum_ret = group_cumulative[g] - 1
            
            n_periods = len(returns_series)
            annual_factor = 252 / max(holding_period_est(n_periods), 1)
            annual_ret = (1 + cum_ret) ** (annual_factor / max(n_periods, 1)) - 1 if n_periods > 0 else 0
            
            sharpe = 0
            if returns_series.std() > 0:
                sharpe = (returns_series.mean() / returns_series.std()) * np.sqrt(annual_factor)
            
            cum_series = pd.Series([1.0] + list((1 + returns_series).cumprod()))
            running_max = cum_series.cummax()
            drawdown = (cum_series - running_max) / running_max
            max_dd = float(drawdown.min())
            
            group_results.append(GroupReturns(
                group=g,
                cumulative_return=float(cum_ret),
                annual_return=float(annual_ret),
                sharpe_ratio=float(sharpe),
                max_drawdown=float(max_dd),
                returns=group_returns_data[g],
                cumulative_returns=cumulative_records[g]
            ))
        
        if len(group_results) >= 2:
            top = group_results[-1]
            bottom = group_results[0]
            
            ls_returns = []
            ls_cum = 1.0
            ls_cumulative = []
            for i in range(min(len(top.returns), len(bottom.returns))):
                ls_ret = top.returns[i]["return"] - bottom.returns[i]["return"]
                ls_cum *= (1 + ls_ret)
                ls_returns.append({"trade_date": top.returns[i]["trade_date"], "return": ls_ret})
                ls_cumulative.append({"trade_date": top.returns[i]["trade_date"], "cumulative_return": ls_cum - 1})
            
            long_short = {
                "group": "L-S",
                "cumulative_return": ls_cum - 1,
                "annual_return": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "returns": ls_returns,
                "cumulative_returns": ls_cumulative
            }
        else:
            long_short = {}
        
        return group_results, long_short, heatmap_records, turnover_by_period
    
    def run_backtest(self, request: BacktestRequest) -> BacktestResult:
        try:
            factor_df = pd.DataFrame(request.factor_values)
            if factor_df.empty:
                return BacktestResult(success=False, message="因子值为空")
            
            factor_df.columns = factor_df.columns.str.lower()
            col_map = {c: c for c in factor_df.columns}
            for c in factor_df.columns:
                if 'ts_code' in c.lower() or 'code' in c.lower():
                    col_map[c] = 'ts_code'
                elif 'date' in c.lower() or 'time' in c.lower():
                    col_map[c] = 'trade_date'
                elif 'factor' in c.lower() or 'value' in c.lower():
                    col_map[c] = 'factor_value'
            factor_df = factor_df.rename(columns=col_map)
            
            required = {'ts_code', 'trade_date', 'factor_value'}
            if not required.issubset(set(factor_df.columns)):
                return BacktestResult(
                    success=False,
                    message=f"缺少必要列: {required - set(factor_df.columns)}"
                )
            
            unique_codes = factor_df['ts_code'].unique().tolist() if 'ts_code' in factor_df.columns else None
            
            returns_df = self._get_future_returns(
                request.dataset_name,
                holding_period=request.holding_period,
                start_date=request.start_date,
                end_date=request.end_date,
                stock_codes=unique_codes
            )
            
            aligned_df = self._align_data(factor_df, returns_df)
            if aligned_df.empty:
                return BacktestResult(success=False, message="对齐后数据为空，请检查日期和股票代码是否匹配")
            
            ic_stats = self._calculate_ic(aligned_df)
            group_results, long_short, heatmap_data, turnover_periods = self._calculate_group_returns(
                aligned_df,
                n_groups=request.n_groups,
                commission_rate=request.commission_rate
            )
            
            if turnover_periods:
                t_series = pd.Series([t["turnover"] for t in turnover_periods])
                turnover_stats = TurnoverStats(
                    mean_turnover=float(t_series.mean()),
                    turnover_std=float(t_series.std()) if len(t_series) > 1 else 0,
                    turnover_by_period=turnover_periods
                )
            else:
                turnover_stats = TurnoverStats(mean_turnover=0, turnover_std=0, turnover_by_period=[])
            
            return BacktestResult(
                success=True,
                message="回测完成",
                ic_stats=ic_stats,
                group_returns=group_results,
                long_short_return=long_short,
                turnover_stats=turnover_stats,
                heatmap_data=heatmap_data
            )
            
        except Exception as e:
            logger.exception(f"Backtest failed: {e}")
            return BacktestResult(success=False, message=f"回测失败: {str(e)}")


def holding_period_est(n_periods: int) -> int:
    return max(1, n_periods // 252) if n_periods > 252 else 1


backtest_engine = BacktestEngine()
