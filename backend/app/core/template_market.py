import pandas as pd
import numpy as np
import time
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple

from app.core.duckdb_engine import duckdb_engine

logger = logging.getLogger(__name__)


class TemplateMarket:
    def __init__(self):
        self._ensure_table()

    def _ensure_table(self):
        try:
            duckdb_engine.conn.execute("""
                CREATE TABLE IF NOT EXISTS factor_templates (
                    template_id VARCHAR PRIMARY KEY,
                    name VARCHAR,
                    description VARCHAR,
                    category VARCHAR,
                    tags VARCHAR,
                    author_name VARCHAR,
                    author_avatar VARCHAR,
                    author_profile VARCHAR,
                    workflow_json VARCHAR,
                    factor_stats_json VARCHAR,
                    backtest_result_json VARCHAR,
                    likes INTEGER DEFAULT 0,
                    forks INTEGER DEFAULT 0,
                    views INTEGER DEFAULT 0,
                    is_public BOOLEAN DEFAULT TRUE,
                    created_at DOUBLE,
                    updated_at DOUBLE
                )
            """)
            logger.info("Template table ensured")
        except Exception as e:
            logger.warning(f"Failed to create template table: {e}")

    def publish_template(
        self,
        name: str,
        description: str,
        category: str,
        tags: List[str],
        author_name: str,
        workflow: Dict[str, Any],
        factor_stats: Optional[Dict[str, Any]] = None,
        backtest_result: Optional[Dict[str, Any]] = None,
        is_public: bool = True,
        author_avatar: Optional[str] = None,
        author_profile: Optional[str] = None
    ) -> str:
        template_id = f"tpl_{uuid.uuid4().hex[:12]}"
        now = time.time()

        import json
        workflow_json = json.dumps(workflow, ensure_ascii=False, default=str)
        factor_stats_json = json.dumps(factor_stats, ensure_ascii=False, default=str) if factor_stats else None
        backtest_json = json.dumps(backtest_result, ensure_ascii=False, default=str) if backtest_result else None
        tags_json = json.dumps(tags, ensure_ascii=False)

        duckdb_engine.conn.execute("""
            INSERT INTO factor_templates (
                template_id, name, description, category, tags,
                author_name, author_avatar, author_profile,
                workflow_json, factor_stats_json, backtest_result_json,
                likes, forks, views, is_public, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?, ?)
        """, [
            template_id, name, description, category, tags_json,
            author_name, author_avatar, author_profile,
            workflow_json, factor_stats_json, backtest_json,
            is_public, now, now
        ])

        logger.info(f"Template published: {template_id}")
        return template_id

    def list_templates(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        offset: int = 0,
        limit: int = 50,
        only_public: bool = True
    ) -> Tuple[List[Dict[str, Any]], int]:
        import json
        query = "SELECT * FROM factor_templates WHERE 1=1"
        params = []

        if only_public:
            query += " AND is_public = TRUE"
        if category:
            query += " AND category = ?"
            params.append(category)
        if search:
            query += " AND (name LIKE ? OR description LIKE ? OR tags LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

        if sort_by in ["created_at", "updated_at", "likes", "forks", "views"]:
            order = "DESC" if sort_order.lower() == "desc" else "ASC"
            query += f" ORDER BY {sort_by} {order}"

        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        total = duckdb_engine.conn.execute(count_query, params).fetchone()[0]

        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        try:
            df = duckdb_engine.conn.execute(query, params).fetchdf()
        except Exception as e:
            logger.warning(f"Query failed ({e}), trying simpler approach")
            all_df = duckdb_engine.conn.execute("SELECT * FROM factor_templates", params).fetchdf()
            if search:
                mask = (all_df['name'].str.contains(search, na=False) |
                        all_df['description'].str.contains(search, na=False) |
                        all_df['tags'].str.contains(search, na=False))
                all_df = all_df[mask]
            if only_public:
                all_df = all_df[all_df['is_public'] == True]
            total = len(all_df)
            all_df = all_df.sort_values(sort_by, ascending=(sort_order.lower() == "asc"))
            df = all_df.iloc[offset:offset+limit]

        templates = []
        for _, row in df.iterrows():
            try:
                wf = json.loads(row['workflow_json'])
            except Exception:
                wf = {}

            try:
                tags = json.loads(row['tags']) if row['tags'] else []
            except Exception:
                tags = []

            try:
                stats = json.loads(row['factor_stats_json']) if row['factor_stats_json'] else None
            except Exception:
                stats = None

            try:
                bt = json.loads(row['backtest_result_json']) if row['backtest_result_json'] else None
            except Exception:
                bt = None

            templates.append({
                "template_id": row['template_id'],
                "name": row['name'],
                "description": row['description'],
                "category": row['category'],
                "tags": tags,
                "author": {
                    "name": row['author_name'],
                    "avatar": row['author_avatar'],
                    "profile": row['author_profile']
                },
                "workflow": wf,
                "factor_stats": stats,
                "backtest_result": bt,
                "likes": int(row['likes']),
                "forks": int(row['forks']),
                "views": int(row['views']),
                "is_public": bool(row['is_public']),
                "created_at": float(row['created_at']),
                "updated_at": float(row['updated_at'])
            })

        return templates, total

    def get_template(self, template_id: str, increment_views: bool = True) -> Optional[Dict[str, Any]]:
        import json
        try:
            row = duckdb_engine.conn.execute(
                "SELECT * FROM factor_templates WHERE template_id = ?",
                [template_id]
            ).fetchone()
        except Exception as e:
            logger.error(f"Get template error: {e}")
            return None

        if not row:
            return None

        if increment_views:
            try:
                duckdb_engine.conn.execute(
                    "UPDATE factor_templates SET views = views + 1, updated_at = ? WHERE template_id = ?",
                    [time.time(), template_id]
                )
            except Exception:
                pass

        try:
            wf = json.loads(row['workflow_json'])
        except Exception:
            wf = {}

        try:
            tags = json.loads(row['tags']) if row['tags'] else []
        except Exception:
            tags = []

        try:
            stats = json.loads(row['factor_stats_json']) if row['factor_stats_json'] else None
        except Exception:
            stats = None

        try:
            bt = json.loads(row['backtest_result_json']) if row['backtest_result_json'] else None
        except Exception:
            bt = None

        return {
            "template_id": row['template_id'],
            "name": row['name'],
            "description": row['description'],
            "category": row['category'],
            "tags": tags,
            "author": {
                "name": row['author_name'],
                "avatar": row['author_avatar'],
                "profile": row['author_profile']
            },
            "workflow": wf,
            "factor_stats": stats,
            "backtest_result": bt,
            "likes": int(row['likes']),
            "forks": int(row['forks']),
            "views": int(row['views']) + (1 if increment_views else 0),
            "is_public": bool(row['is_public']),
            "created_at": float(row['created_at']),
            "updated_at": float(row['updated_at'])
        }

    def fork_template(self, template_id: str, new_author_name: str, new_name: Optional[str] = None) -> Optional[Tuple[str, Dict[str, Any]]]:
        tpl = self.get_template(template_id, increment_views=False)
        if not tpl:
            return None

        try:
            duckdb_engine.conn.execute(
                "UPDATE factor_templates SET forks = forks + 1, updated_at = ? WHERE template_id = ?",
                [time.time(), template_id]
            )
        except Exception:
            pass

        new_tpl_id = self.publish_template(
            name=new_name or f"{tpl['name']} (Fork)",
            description=f"Forked from {tpl['name']} by {tpl['author']['name']}. {tpl['description']}",
            category=tpl['category'],
            tags=tpl['tags'] + ["forked"],
            author_name=new_author_name,
            workflow=tpl['workflow'],
            factor_stats=tpl.get('factor_stats'),
            backtest_result=tpl.get('backtest_result'),
            is_public=tpl['is_public']
        )

        new_tpl = self.get_template(new_tpl_id, increment_views=False)
        return new_tpl_id, new_tpl['workflow'] if new_tpl else tpl['workflow']

    def like_template(self, template_id: str) -> bool:
        try:
            duckdb_engine.conn.execute(
                "UPDATE factor_templates SET likes = likes + 1, updated_at = ? WHERE template_id = ?",
                [time.time(), template_id]
            )
            return True
        except Exception as e:
            logger.error(f"Like template error: {e}")
            return False

    def delete_template(self, template_id: str) -> bool:
        try:
            duckdb_engine.conn.execute(
                "DELETE FROM factor_templates WHERE template_id = ?",
                [template_id]
            )
            return True
        except Exception as e:
            logger.error(f"Delete template error: {e}")
            return False

    def get_categories(self) -> List[str]:
        try:
            rows = duckdb_engine.conn.execute(
                "SELECT DISTINCT category FROM factor_templates WHERE is_public = TRUE"
            ).fetchall()
            return [r[0] for r in rows if r[0]]
        except Exception:
            return []


template_market = TemplateMarket()
