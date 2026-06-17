import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import logging

from app.core.duckdb_engine import duckdb_engine
from app.core.operators import OperatorRegistry
from app.models.schemas import FactorWorkflow, FactorNode

logger = logging.getLogger(__name__)


class FactorWorkflowExecutor:
    def __init__(self):
        self._node_outputs: Dict[str, pd.Series] = {}
        self._raw_data: Optional[pd.DataFrame] = None
        self._code_col: Optional[str] = None
        self._date_col: Optional[str] = None
        self._all_dates: List[Any] = []
        self._chain_lookback: Dict[str, int] = {}

    def _compute_chain_lookback(self, nodes: List[FactorNode], node_map: Dict[str, FactorNode]) -> Dict[str, int]:
        lookbacks = {}
        for node_id in self._topological_sort(nodes):
            node = node_map[node_id]
            op = OperatorRegistry.get(node.operator_id)
            own_lb = op.get_lookback(node.params) if op else 0
            
            max_upstream_lb = 0
            for _, source in node.inputs.items():
                upstream_id = self._extract_node_deps(source)
                if upstream_id and upstream_id in lookbacks:
                    max_upstream_lb = max(max_upstream_lb, lookbacks[upstream_id])
            
            lookbacks[node_id] = own_lb + max_upstream_lb
        
        return lookbacks
    
    def _load_market_data(
        self,
        dataset_name: str,
        stock_codes: Optional[List[str]] = None,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None
    ) -> pd.DataFrame:
        info = duckdb_engine.get_table_info(dataset_name)
        if not info:
            raise ValueError(f"Dataset {dataset_name} not found")
        
        cols = info["columns"]
        required = {"open", "high", "low", "close"}
        cols_lower = {c.lower(): c for c in cols}
        price_cols = [cols_lower[c] for c in ["open", "high", "low", "close"] if c in cols_lower]
        code_candidates = ["ts_code", "code", "symbol", "stock_code"]
        self._code_col = next((cols_lower[c] for c in code_candidates if c in cols_lower), None)
        self._date_col = next((c for c in cols if 'date' in c.lower() or 'time' in c.lower()), None)
        
        vol_col = None
        for vc in ["volume", "vol", "成交量"]:
            if vc in cols_lower:
                vol_col = cols_lower[vc]
                break
        
        query_cols = price_cols + ([] if not self._code_col else [self._code_col]) + ([] if not self._date_col else [self._date_col]) + ([] if not vol_col else [vol_col])
        df = duckdb_engine.query_data(
            dataset_name,
            columns=query_cols,
            stock_codes=stock_codes,
            start_date=start_date,
            end_date=end_date
        )
        self._raw_data = df
        return df
    
    def _extract_price_series(self, df: pd.DataFrame, price_type: str = "close") -> Dict[str, pd.Series]:
        if self._code_col is None or self._date_col is None:
            raise ValueError("Missing code or date column")
        
        price_col_lower = {c.lower(): c for c in df.columns}
        price_col = price_col_lower.get(price_type.lower())
        if price_col is None:
            raise ValueError(f"Price column {price_type} not found")
        
        result = {}
        for code, group in df.groupby(self._code_col):
            sorted_group = group.sort_values(self._date_col)
            series = pd.Series(
                sorted_group[price_col].values,
                index=sorted_group[self._date_col].values,
                name=str(code)
            )
            result[str(code)] = series
        return result
    
    def _extract_volume_series(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        if self._code_col is None or self._date_col is None:
            return {}
        
        vol_col = None
        for vc in ["volume", "vol", "成交量"]:
            for c in df.columns:
                if c.lower() == vc.lower():
                    vol_col = c
                    break
            if vol_col:
                break
        
        if not vol_col:
            return {}
        
        result = {}
        for code, group in df.groupby(self._code_col):
            sorted_group = group.sort_values(self._date_col)
            series = pd.Series(
                sorted_group[vol_col].values,
                index=sorted_group[self._date_col].values,
                name=str(code)
            )
            result[str(code)] = series
        return result
    
    def _extract_node_deps(self, source) -> Optional[str]:
        if isinstance(source, dict):
            if source.get('type') == 'node_output':
                return source.get('node_id')
            return None
        elif isinstance(source, str):
            if source.startswith("market:") or source in ['close', 'open', 'high', 'low', 'volume']:
                return None
            if ":" in source:
                return source.split(":")[0]
            if source.startswith("node_") or source.startswith("n_") or len(source) <= 10:
                return source
            return None
        return None

    def _build_dependency_graph(self, nodes: List[FactorNode]) -> Tuple[Dict[str, List[str]], Dict[str, FactorNode]]:
        adj = defaultdict(list)
        node_map = {}
        in_degree = defaultdict(int)
        
        valid_ids = {n.id for n in nodes}
        
        for node in nodes:
            node_map[node.id] = node
            if node.id not in in_degree:
                in_degree[node.id] = 0
        
        for node in nodes:
            for _, source in node.inputs.items():
                source_node_id = self._extract_node_deps(source)
                if source_node_id and source_node_id in valid_ids:
                    adj[source_node_id].append(node.id)
                    in_degree[node.id] = in_degree.get(node.id, 0) + 1
        
        return adj, node_map
    
    def _topological_sort(self, nodes: List[FactorNode]) -> List[str]:
        adj, node_map = self._build_dependency_graph(nodes)
        in_degree = defaultdict(int)
        valid_ids = {n.id for n in nodes}
        for n in nodes:
            in_degree[n.id] = 0
        for n in nodes:
            for _, source in n.inputs.items():
                sid = self._extract_node_deps(source)
                if sid and sid in valid_ids:
                    in_degree[n.id] += 1
        
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result = []
        while queue:
            nid = queue.pop(0)
            result.append(nid)
            for neighbor in adj.get(nid, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(result) != len(nodes):
            remaining = set(n.id for n in nodes) - set(result)
            raise ValueError(f"Workflow has circular dependencies involving: {remaining}")
        return result
    
    def _resolve_inputs(
        self,
        node: FactorNode,
        close_series: Dict[str, pd.Series],
        open_series: Dict[str, pd.Series],
        high_series: Dict[str, pd.Series],
        low_series: Dict[str, pd.Series],
        volume_series: Dict[str, pd.Series],
        stock_codes: List[str]
    ) -> Dict[str, pd.Series]:
        inputs = {}
        
        price_series_map = {
            'close': close_series,
            'open': open_series,
            'high': high_series,
            'low': low_series,
            'volume': volume_series
        }
        
        for input_id, source in node.inputs.items():
            if isinstance(source, dict):
                src_type = source.get('type')
                if src_type == 'market_data':
                    field = source.get('field', 'close')
                    inputs[input_id] = price_series_map.get(field, close_series)
                elif src_type == 'node_output':
                    node_id = source.get('node_id')
                    if node_id and node_id in self._node_outputs:
                        inputs[input_id] = self._node_outputs[node_id]
            elif isinstance(source, str):
                if source.startswith("market:"):
                    market_type = source.split(":")[1]
                    inputs[input_id] = price_series_map.get(market_type, close_series)
                elif ":" in source:
                    source_node_id, output_id = source.split(":")
                    if source_node_id in self._node_outputs:
                        inputs[input_id] = self._node_outputs[source_node_id]
                elif source in self._node_outputs:
                    inputs[input_id] = self._node_outputs[source]
                elif source in price_series_map:
                    inputs[input_id] = price_series_map[source]
        
        if not inputs:
            operator = OperatorRegistry.get(node.operator_id)
            if operator and operator.inputs:
                first_input = operator.inputs[0]
                if first_input["id"] == "price":
                    inputs[first_input["id"]] = close_series
                elif first_input["id"] == "volume":
                    inputs[first_input["id"]] = volume_series
                elif first_input["id"] == "factor":
                    inputs[first_input["id"]] = close_series
                elif first_input["id"] in ["left", "right"]:
                    inputs[first_input["id"]] = close_series
        
        return inputs
    
    def _apply_operator_per_stock(
        self,
        operator_id: str,
        inputs: Dict[str, Dict[str, pd.Series]],
        params: Dict[str, Any]
    ) -> Dict[str, pd.Series]:
        operator = OperatorRegistry.get(operator_id)
        if not operator:
            raise ValueError(f"Unknown operator: {operator_id}")
        
        result = {}
        all_codes = set()
        for inp_series_dict in inputs.values():
            all_codes.update(inp_series_dict.keys())
        
        for code in all_codes:
            stock_inputs = {}
            valid = True
            for input_id, series_dict in inputs.items():
                if code not in series_dict:
                    valid = False
                    break
                stock_inputs[input_id] = series_dict[code]
            if not valid:
                continue
            try:
                result[code] = operator.compute(stock_inputs, params)
            except Exception as e:
                logger.warning(f"Failed to compute operator {operator_id} for stock {code}: {e}")
                continue
        
        return result
    
    def execute_workflow(
        self,
        workflow: FactorWorkflow,
        dataset_name: str,
        stock_codes: Optional[List[str]] = None,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        forward_validation: bool = False
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        self._node_outputs = {}
        df = self._load_market_data(dataset_name, stock_codes, start_date, end_date)
        
        close_series = self._extract_price_series(df, "close")
        open_series = self._extract_price_series(df, "open")
        high_series = self._extract_price_series(df, "high")
        low_series = self._extract_price_series(df, "low")
        volume_series = self._extract_volume_series(df)
        
        all_stock_codes = list(close_series.keys())
        
        execution_order = self._topological_sort(workflow.nodes)
        adj, node_map = self._build_dependency_graph(workflow.nodes)
        
        self._chain_lookback = self._compute_chain_lookback(workflow.nodes, node_map)
        
        if forward_validation:
            output_data, fv_info = self._execute_forward_validation(
                workflow, node_map, execution_order,
                close_series, open_series, high_series, low_series, volume_series,
                all_stock_codes, df
            )
            factor_records = self._format_factor_output(output_data, df)
            stats = self._compute_factor_statistics(factor_records)
            stats["forward_validation"] = fv_info
            return factor_records, stats
        
        for node_id in execution_order:
            node = node_map[node_id]
            inputs = self._resolve_inputs(
                node,
                close_series,
                open_series,
                high_series,
                low_series,
                volume_series,
                all_stock_codes
            )
            result = self._apply_operator_per_stock(node.operator_id, inputs, node.params)
            self._node_outputs[node_id] = result
        
        output_data = self._node_outputs.get(workflow.output_node, {})
        factor_records = self._format_factor_output(output_data, df)
        stats = self._compute_factor_statistics(factor_records)
        
        return factor_records, stats

    def _execute_forward_validation(
        self,
        workflow: FactorWorkflow,
        node_map: Dict[str, FactorNode],
        execution_order: List[str],
        close_series: Dict[str, pd.Series],
        open_series: Dict[str, pd.Series],
        high_series: Dict[str, pd.Series],
        low_series: Dict[str, pd.Series],
        volume_series: Dict[str, pd.Series],
        stock_codes: List[str],
        df: pd.DataFrame
    ) -> Tuple[Dict[str, pd.Series], Dict[str, Any]]:
        all_dates = sorted(set().union(*(s.index for s in close_series.values())))
        output_lookback = self._chain_lookback.get(workflow.output_node, 0)
        warmup_dates = all_dates[:output_lookback] if output_lookback < len(all_dates) else []
        eval_dates = all_dates[output_lookback:]
        
        output_node_data: Dict[str, pd.Series] = {}
        for code in stock_codes:
            output_node_data[code] = pd.Series(dtype=float, name=code)
        
        total = len(eval_dates)
        for i, as_of_date in enumerate(eval_dates):
            if i % 50 == 0:
                logger.info(f"Forward validation: {i}/{total} as_of_date={as_of_date}")
            
            truncated_inputs = self._truncate_series_at_date(
                close_series, open_series, high_series, low_series, volume_series,
                as_of_date, stock_codes
            )
            
            self._node_outputs = {}
            for node_id in execution_order:
                node = node_map[node_id]
                inputs = self._resolve_inputs(
                    node,
                    truncated_inputs["close"],
                    truncated_inputs["open"],
                    truncated_inputs["high"],
                    truncated_inputs["low"],
                    truncated_inputs["volume"],
                    stock_codes
                )
                result = self._apply_operator_per_stock(node.operator_id, inputs, node.params)
                self._node_outputs[node_id] = result
            
            output_data = self._node_outputs.get(workflow.output_node, {})
            for code, series in output_data.items():
                if code in output_node_data and len(series) > 0:
                    last_val = series.iloc[-1]
                    if pd.notna(last_val):
                        output_node_data[code].at[as_of_date] = last_val
        
        fv_info = {
            "enabled": True,
            "total_dates": len(all_dates),
            "warmup_dates": len(warmup_dates),
            "eval_dates": len(eval_dates),
            "output_chain_lookback": output_lookback,
            "warmup_period_end": str(warmup_dates[-1])[:10] if warmup_dates else None,
            "message": f"前向验证完成: 跳过{len(warmup_dates)}天预热期, 在{len(eval_dates)}个时点验证"
        }
        
        return output_node_data, fv_info

    def _truncate_series_at_date(
        self,
        close_series: Dict[str, pd.Series],
        open_series: Dict[str, pd.Series],
        high_series: Dict[str, pd.Series],
        low_series: Dict[str, pd.Series],
        volume_series: Dict[str, pd.Series],
        as_of_date: Any,
        stock_codes: List[str]
    ) -> Dict[str, Dict[str, pd.Series]]:
        result = {}
        for name, series_dict in [
            ("close", close_series), ("open", open_series),
            ("high", high_series), ("low", low_series),
            ("volume", volume_series)
        ]:
            truncated = {}
            for code in stock_codes:
                if code in series_dict:
                    s = series_dict[code]
                    truncated[code] = s[s.index <= as_of_date]
            result[name] = truncated
        return result
    
    def _format_factor_output(
        self,
        output_data: Dict[str, pd.Series],
        df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        records = []
        for code, series in output_data.items():
            for dt, val in series.items():
                if pd.notna(val):
                    records.append({
                        "ts_code": code,
                        "trade_date": str(dt)[:10] if hasattr(dt, 'strftime') else str(dt),
                        "factor_value": float(val)
                    })
        
        if self._date_col and self._code_col:
            factor_df = pd.DataFrame(records)
            if not factor_df.empty and 'trade_date' in factor_df.columns:
                factor_df['trade_date'] = pd.to_datetime(factor_df['trade_date'])
                factor_df = factor_df.sort_values(['trade_date', 'ts_code'])
                records = factor_df.to_dict('records')
        
        return records
    
    def _compute_factor_statistics(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not records:
            return {"count": 0}
        
        df = pd.DataFrame(records)
        vals = df['factor_value']
        return {
            "count": len(df),
            "mean": float(vals.mean()) if len(vals) > 0 else 0,
            "std": float(vals.std()) if len(vals) > 1 else 0,
            "min": float(vals.min()) if len(vals) > 0 else 0,
            "max": float(vals.max()) if len(vals) > 0 else 0,
            "median": float(vals.median()) if len(vals) > 0 else 0,
            "n_stocks": df['ts_code'].nunique() if 'ts_code' in df.columns else 0,
            "n_dates": df['trade_date'].nunique() if 'trade_date' in df.columns else 0
        }


factor_executor = FactorWorkflowExecutor()
