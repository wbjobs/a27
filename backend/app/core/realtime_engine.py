import pandas as pd
import numpy as np
import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict

from app.core.duckdb_engine import duckdb_engine
from app.core.factor_engine import factor_executor
from app.models.schemas import FactorWorkflow

logger = logging.getLogger(__name__)


class RealtimeMarketSimulator:
    def __init__(self):
        self._sessions: Dict[str, "RealtimeSession"] = {}
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        dataset_name: str,
        workflow: FactorWorkflow,
        push_interval: float = 1.0
    ) -> "RealtimeSession":
        async with self._lock:
            session_id = f"session_{int(time.time())}_{np.random.randint(100000)}"
            session = RealtimeSession(
                session_id, dataset_name, workflow, push_interval
            )
            await session.start()
            self._sessions[session_id] = session
            return session

    async def close_session(self, session_id: str):
        async with self._lock:
            if session_id in self._sessions:
                await self._sessions[session_id].stop()
                del self._sessions[session_id]


class RealtimeSession:
    def __init__(
        self,
        session_id: str,
        dataset_name: str,
        workflow: FactorWorkflow,
        push_interval: float = 1.0
    ):
        self.session_id = session_id
        self.dataset_name = dataset_name
        self.workflow = workflow
        self.push_interval = push_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._callbacks: List[callable] = []
        self._current_index = 0
        self._dates: List[Any] = []
        self._market_data: Optional[pd.DataFrame] = None
        self._factor_history: Dict[str, pd.Series] = {}
        self._last_factor_values: Dict[str, float] = {}
        self._initialized = False

    def add_callback(self, callback: callable):
        self._callbacks.append(callback)

    def remove_callback(self, callback: callable):
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def start(self):
        df = duckdb_engine.load_table(self.dataset_name)
        if df.empty:
            raise ValueError(f"Dataset {self.dataset_name} not found or empty")

        date_col = duckdb_engine._find_date_column(self.dataset_name)
        code_col = duckdb_engine._find_column(self.dataset_name, ["ts_code", "code", "symbol", "stock_code"])

        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        self._market_data = df.sort_values(date_col)
        self._dates = sorted(self._market_data[date_col].unique())
        self._current_index = 0
        self._initialized = True
        self._running = True
        self._task = asyncio.create_task(self._push_loop())
        logger.info(f"Realtime session {self.session_id} started, {len(self._dates)} dates")

    async def stop(self):
        self._running = False
        if self._task:
            try:
                self._task.cancel()
                await self._task
            except Exception:
                pass
        logger.info(f"Realtime session {self.session_id} stopped")

    async def _push_loop(self):
        try:
            while self._running and self._current_index < len(self._dates):
                try:
                    as_of_date = self._dates[self._current_index]
                    result = self._process_single_date(as_of_date)

                    if result:
                        for callback in self._callbacks:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(result)
                                else:
                                    callback(result)
                            except Exception as e:
                                logger.error(f"Callback error: {e}")

                    self._current_index += 1
                    await asyncio.sleep(self.push_interval)
                except Exception as e:
                    logger.error(f"Push loop error: {e}")
                    await asyncio.sleep(self.push_interval)

            if self._current_index >= len(self._dates):
                end_msg = {
                    "type": "realtime_end",
                    "data": {
                        "session_id": self.session_id,
                        "message": "行情推送完成，已回放所有历史数据",
                        "total_dates": len(self._dates),
                        "processed_dates": self._current_index
                    },
                    "timestamp": time.time()
                }
                for callback in self._callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(end_msg)
                        else:
                            callback(end_msg)
                    except Exception:
                        pass

        except asyncio.CancelledError:
            pass

    def _process_single_date(self, as_of_date) -> Optional[Dict[str, Any]]:
        df = self._market_data
        date_col = duckdb_engine._find_date_column(self.dataset_name)
        code_col = duckdb_engine._find_column(self.dataset_name, ["ts_code", "code", "symbol", "stock_code"])

        df_slice = df[df[date_col] <= as_of_date].copy()
        if df_slice.empty:
            return None

        current_bar_df = df[df[date_col] == as_of_date]

        bars = []
        for _, row in current_bar_df.iterrows():
            bars.append({
                "ts_code": row[code_col],
                "trade_date": str(as_of_date)[:10],
                "open": float(row.get("open", np.nan)),
                "high": float(row.get("high", np.nan)),
                "low": float(row.get("low", np.nan)),
                "close": float(row.get("close", np.nan)),
                "volume": float(row.get("volume", np.nan)),
                "timestamp": time.time()
            })

        from app.core.factor_engine import FactorWorkflowExecutor
        executor = FactorWorkflowExecutor()

        try:
            factor_records, _ = executor.execute_workflow(
                self.workflow,
                self.dataset_name,
                end_date=pd.Timestamp(as_of_date).date()
            )
        except Exception as e:
            logger.error(f"Factor compute error at {as_of_date}: {e}")
            return None

        factor_updates = []
        for rec in factor_records:
            ts_code = rec.get("ts_code")
            fv = rec.get("factor_value")
            if pd.notna(fv):
                prev = self._last_factor_values.get(ts_code, fv)
                change_pct = ((fv - prev) / abs(prev)) * 100 if abs(prev) > 1e-9 else 0.0
                factor_updates.append({
                    "ts_code": ts_code,
                    "trade_date": str(as_of_date)[:10],
                    "factor_value": float(fv),
                    "previous_value": float(prev),
                    "change_pct": round(float(change_pct), 4)
                })
                self._last_factor_values[ts_code] = float(fv)

        stats = {
            "date": str(as_of_date)[:10],
            "n_stocks": len(bars),
            "n_factor_updates": len(factor_updates),
            "factor_mean": float(np.nanmean([f["factor_value"] for f in factor_updates])) if factor_updates else 0,
            "factor_std": float(np.nanstd([f["factor_value"] for f in factor_updates])) if factor_updates else 0
        }

        return {
            "type": "realtime_update",
            "data": {
                "session_id": self.session_id,
                "date": str(as_of_date)[:10],
                "bars": bars,
                "factor_updates": factor_updates,
                "stats": stats,
                "progress": self._current_index / len(self._dates)
            },
            "timestamp": time.time()
        }


realtime_simulator = RealtimeMarketSimulator()
