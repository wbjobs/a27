import duckdb
import pandas as pd
import numpy as np
import os
import tempfile
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import date, datetime
from contextlib import contextmanager

from app.config import settings


class DuckDBEngine:
    _instance = None
    _conn = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        os.makedirs(settings.data_dir, exist_ok=True)
        db_path = os.path.join(settings.data_dir, "factor_workbench.duckdb")
        self._conn = duckdb.connect(db_path)
        self._init_extensions()
    
    def _init_extensions(self):
        try:
            self._conn.execute("INSTALL pandas")
            self._conn.execute("LOAD pandas")
        except Exception:
            pass
    
    @contextmanager
    def connection(self):
        yield self._conn
    
    def close(self):
        if self._conn:
            self._conn.close()
    
    def import_file(
        self,
        file_content: bytes,
        file_type: str,
        table_name: Optional[str] = None,
        frequency: str = "daily"
    ) -> Dict[str, Any]:
        suffix = ".csv" if file_type.lower() == "csv" else ".parquet"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name
        
        try:
            if table_name is None:
                file_hash = hashlib.md5(file_content).hexdigest()[:8]
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                table_name = f"market_data_{frequency}_{timestamp}_{file_hash}"
            
            if file_type.lower() == "csv":
                query = f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto('{tmp_path}')"
            else:
                query = f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet('{tmp_path}')"
            
            self._conn.execute(query)
            row_count = self._conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            columns = self._conn.execute(f"DESCRIBE {table_name}").fetchall()
            column_names = [col[0] for col in columns]
            
            return {
                "table_name": table_name,
                "row_count": row_count,
                "columns": column_names
            }
        finally:
            os.unlink(tmp_path)
    
    def list_tables(self) -> List[Dict[str, Any]]:
        tables = self._conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
        result = []
        for (table_name,) in tables:
            try:
                row_count = self._conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                columns_desc = self._conn.execute(f"DESCRIBE {table_name}").fetchall()
                columns = [col[0] for col in columns_desc]
                result.append({
                    "name": table_name,
                    "row_count": row_count,
                    "columns": columns
                })
            except Exception:
                continue
        return result
    
    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        try:
            row_count = self._conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            columns_desc = self._conn.execute(f"DESCRIBE {table_name}").fetchall()
            columns = [col[0] for col in columns_desc]
            date_cols = [c for c in columns if 'date' in c.lower() or 'time' in c.lower()]
            
            date_range = None
            if date_cols:
                date_col = date_cols[0]
                try:
                    q = f"SELECT MIN({date_col}), MAX({date_col}) FROM {table_name}"
                    min_date, max_date = self._conn.execute(q).fetchone()
                    if min_date and max_date:
                        date_range = {"start": min_date, "end": max_date}
                except Exception:
                    pass
            
            return {
                "name": table_name,
                "row_count": row_count,
                "columns": columns,
                "date_range": date_range
            }
        except Exception:
            return None
    
    def query_data(
        self,
        table_name: str,
        columns: Optional[List[str]] = None,
        stock_codes: Optional[List[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        select_cols = ", ".join(columns) if columns else "*"
        query = f"SELECT {select_cols} FROM {table_name} WHERE 1=1"
        params = []
        
        code_cols = ["ts_code", "code", "symbol", "stock_code"]
        if stock_codes:
            code_col = self._find_column(table_name, code_cols)
            if code_col:
                placeholders = ",".join(["?"] * len(stock_codes))
                query += f" AND {code_col} IN ({placeholders})"
                params.extend(stock_codes)
        
        date_col = self._find_date_column(table_name)
        if start_date or end_date:
            if date_col:
                if start_date:
                    query += f" AND {date_col} >= ?"
                    params.append(start_date)
                if end_date:
                    query += f" AND {date_col} <= ?"
                    params.append(end_date)
        
        query += f" ORDER BY {date_col or '1'} ASC"
        if limit:
            query += f" LIMIT {limit}"
        
        return self._conn.execute(query, params).fetchdf()
    
    def _find_column(self, table_name: str, candidates: List[str]) -> Optional[str]:
        cols = [c[0] for c in self._conn.execute(f"DESCRIBE {table_name}").fetchall()]
        cols_lower = {c.lower(): c for c in cols}
        for cand in candidates:
            if cand.lower() in cols_lower:
                return cols_lower[cand.lower()]
        return None
    
    def _find_date_column(self, table_name: str) -> Optional[str]:
        cols = [c[0] for c in self._conn.execute(f"DESCRIBE {table_name}").fetchall()]
        for c in cols:
            cl = c.lower()
            if 'date' in cl or 'trade_date' in cl or 'time' in cl:
                return c
        return None
    
    def get_stock_codes(self, table_name: str, limit: int = 100) -> List[str]:
        code_col = self._find_column(table_name, ["ts_code", "code", "symbol", "stock_code"])
        if not code_col:
            return []
        query = f"SELECT DISTINCT {code_col} FROM {table_name} LIMIT {limit}"
        result = self._conn.execute(query).fetchall()
        return [row[0] for row in result]
    
    def create_or_replace_view(self, view_name: str, query: str, params: List = None) -> None:
        if params:
            self._conn.execute(f"CREATE OR REPLACE VIEW {view_name} AS {query}", params)
        else:
            self._conn.execute(f"CREATE OR REPLACE VIEW {view_name} AS {query}")
    
    def execute_query(self, query: str, params: List = None) -> pd.DataFrame:
        if params:
            return self._conn.execute(query, params).fetchdf()
        return self._conn.execute(query).fetchdf()
    
    def delete_table(self, table_name: str) -> bool:
        try:
            self._conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            return True
        except Exception:
            return False


duckdb_engine = DuckDBEngine()
