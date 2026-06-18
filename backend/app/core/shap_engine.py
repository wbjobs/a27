import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Any, Tuple, Optional
from io import BytesIO
import warnings
warnings.filterwarnings("ignore")

from app.core.duckdb_engine import duckdb_engine
from app.core.backtest_engine import BacktestEngine

logger = logging.getLogger(__name__)


class ShapAnalyzer:
    def __init__(self):
        pass

    def _prepare_training_data(
        self,
        factor_values: List[Dict[str, Any]],
        dataset_name: str,
        target_period: int = 5
    ) -> Tuple[pd.DataFrame, pd.Series]:
        df = pd.DataFrame(factor_values)
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

        if 'ts_code' not in df.columns or 'trade_date' not in df.columns:
            raise ValueError("因子值缺少ts_code或trade_date字段")

        df['trade_date'] = pd.to_datetime(df['trade_date'])

        mkt = duckdb_engine._conn.execute(f"SELECT * FROM {dataset_name}").fetchdf()
        date_col = duckdb_engine._find_date_column(dataset_name)
        code_col = duckdb_engine._find_column(dataset_name, ["ts_code", "code", "symbol", "stock_code"])
        mkt = mkt.copy()
        mkt[date_col] = pd.to_datetime(mkt[date_col])

        merged = df.merge(
            mkt[[code_col, date_col, 'close']],
            left_on=['ts_code', 'trade_date'],
            right_on=[code_col, date_col],
            how='inner'
        )

        if merged.empty:
            raise ValueError("因子值与行情数据无交集")

        merged = merged.sort_values(['ts_code', 'trade_date'])
        merged['future_return'] = merged.groupby('ts_code')['close'].pct_change(target_period).shift(-target_period)
        merged = merged.dropna(subset=['future_return', 'factor_value'])

        if merged.empty:
            raise ValueError("没有可用的未来收益样本")

        pivot = merged.pivot(index='trade_date', columns='ts_code', values='factor_value').ffill()
        returns_pivot = merged.pivot(index='trade_date', columns='ts_code', values='future_return')

        aligned_dates = pivot.index.intersection(returns_pivot.index)
        X = pivot.loc[aligned_dates].values
        y = returns_pivot.loc[aligned_dates].mean(axis=1).values

        column_names = [f"factor_lag_{i}" for i in range(X.shape[1])]
        if X.shape[1] < 100:
            column_names = list(pivot.columns[:X.shape[1]])

        X_df = pd.DataFrame(X, columns=column_names, index=aligned_dates)
        y_series = pd.Series(y, index=aligned_dates, name='future_return')

        return X_df, y_series

    def compute_shap(
        self,
        factor_name: str,
        factor_values: List[Dict[str, Any]],
        dataset_name: str,
        n_samples: int = 100,
        target_period: int = 5
    ) -> Dict[str, Any]:
        try:
            import shap
            from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
        except ImportError as e:
            return {
                "success": False,
                "message": f"缺少shap或sklearn依赖: {e}",
                "feature_contributions": [],
                "shap_values": [],
                "base_value": 0.0,
                "summary_plot_data": [],
                "force_plot_data": None
            }

        try:
            X, y = self._prepare_training_data(factor_values, dataset_name, target_period)

            if len(X) < 50:
                return {
                    "success": False,
                    "message": f"样本不足({len(X)})，需要至少50个有效样本",
                    "feature_contributions": [],
                    "shap_values": [],
                    "base_value": 0.0,
                    "summary_plot_data": [],
                    "force_plot_data": None
                }

            n_estimators = min(100, max(20, len(X) // 5))
            model = RandomForestRegressor(
                n_estimators=n_estimators,
                max_depth=5,
                random_state=42,
                n_jobs=-1
            )
            model.fit(X, y)

            bg_size = min(50, max(10, len(X) // 10))
            background = shap.sample(X, bg_size, random_state=42)
            explainer = shap.TreeExplainer(model, background)

            n_eval = min(n_samples, len(X))
            eval_data = X.sample(n_eval, random_state=42) if len(X) > n_eval else X
            shap_values_obj = explainer.shap_values(eval_data)

            if isinstance(shap_values_obj, list):
                shap_values_arr = shap_values_obj[0]
            else:
                shap_values_arr = shap_values_obj

            base_value = float(explainer.expected_value)
            if isinstance(base_value, (list, np.ndarray)):
                base_value = float(base_value[0]) if len(base_value) > 0 else 0.0

            feature_names = list(X.columns)
            mean_shap = np.mean(shap_values_arr, axis=0)
            mean_abs_shap = np.mean(np.abs(shap_values_arr), axis=0)
            ranked_indices = np.argsort(-mean_abs_shap)

            contributions = []
            for rank, idx in enumerate(ranked_indices):
                contributions.append({
                    "feature": feature_names[idx],
                    "mean_shap_value": round(float(mean_shap[idx]), 8),
                    "mean_abs_shap_value": round(float(mean_abs_shap[idx]), 8),
                    "importance_rank": rank + 1
                })

            shap_records = []
            for i, (idx, row) in enumerate(eval_data.iterrows()):
                shap_records.append({
                    "date": str(idx)[:10] if hasattr(idx, 'strftime') else str(idx),
                    "feature_values": {feat: round(float(row[feat]), 6) for feat in feature_names},
                    "shap_values": {feat: round(float(shap_values_arr[i, j]), 8) for j, feat in enumerate(feature_names)},
                    "predicted_return": round(float(base_value + np.sum(shap_values_arr[i])), 6),
                    "actual_return": round(float(y.loc[idx]), 6) if idx in y.index else None
                })

            summary_data = []
            for j, feat in enumerate(feature_names):
                for i in range(len(eval_data)):
                    summary_data.append({
                        "feature": feat,
                        "feature_value": round(float(eval_data.iloc[i, j]), 6),
                        "shap_value": round(float(shap_values_arr[i, j]), 8),
                        "rank": int(np.where(ranked_indices == j)[0][0]) + 1
                    })

            mean_idx = len(eval_data) // 2
            force_data = {
                "base_value": round(float(base_value), 6),
                "date": str(eval_data.index[mean_idx])[:10],
                "features": [
                    {
                        "name": feat,
                        "value": round(float(eval_data.iloc[mean_idx, j]), 6),
                        "shap_value": round(float(shap_values_arr[mean_idx, j]), 8),
                        "contribution": round(float(shap_values_arr[mean_idx, j]), 6)
                    }
                    for j, feat in enumerate(feature_names)
                ],
                "predicted": round(float(base_value + np.sum(shap_values_arr[mean_idx])), 6),
                "actual": round(float(y.loc[eval_data.index[mean_idx]]), 6) if eval_data.index[mean_idx] in y.index else None
            }

            return {
                "success": True,
                "message": f"SHAP分析完成，{len(eval_data)}个样本，{len(feature_names)}个特征",
                "feature_contributions": contributions,
                "shap_values": shap_records,
                "base_value": round(float(base_value), 6),
                "summary_plot_data": summary_data,
                "force_plot_data": force_data
            }

        except Exception as e:
            import traceback
            logger.error(f"SHAP computation error: {e}\n{traceback.format_exc()}")
            return {
                "success": False,
                "message": f"SHAP分析失败: {str(e)}",
                "feature_contributions": [],
                "shap_values": [],
                "base_value": 0.0,
                "summary_plot_data": [],
                "force_plot_data": None
            }

    def generate_pdf_report(
        self,
        shap_result: Dict[str, Any],
        factor_name: str,
        backtest_result: Optional[Dict[str, Any]] = None
    ) -> bytes:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
            from reportlab.lib.units import cm
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from matplotlib import font_manager
        except ImportError as e:
            raise RuntimeError(f"PDF生成依赖未安装: {e}")

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=18, spaceAfter=12, textColor=colors.HexColor('#1e3a8a'))
        h2_style = ParagraphStyle('CustomH2', parent=styles['Heading2'], fontSize=14, spaceAfter=10, textColor=colors.HexColor('#3b82f6'))
        normal_style = styles['Normal']

        story = []

        story.append(Paragraph(f"因子解释性分析报告 - {factor_name}", title_style))
        story.append(Paragraph(f"生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
        story.append(Spacer(1, 0.5*cm))

        if shap_result.get("success"):
            story.append(Paragraph("一、特征重要性排名", h2_style))
            contribs = shap_result.get("feature_contributions", [])[:15]
            table_data = [["排名", "特征", "平均SHAP值", "平均|SHAP|值"]]
            for c in contribs:
                table_data.append([
                    str(c["importance_rank"]),
                    str(c["feature"]),
                    f"{c['mean_shap_value']:.6f}",
                    f"{c['mean_abs_shap_value']:.6f}"
                ])
            table = Table(table_data, colWidths=[1.5*cm, 7*cm, 3.5*cm, 3.5*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(table)
            story.append(Spacer(1, 0.5*cm))

            story.append(Paragraph("二、分析摘要", h2_style))
            base_value = shap_result.get("base_value", 0)
            n_features = len(shap_result.get("feature_contributions", []))
            n_samples = len(shap_result.get("shap_values", []))
            summary = [
                ["基础预测值 (Base Value)", f"{base_value:.6f}"],
                ["特征数量", str(n_features)],
                ["分析样本数", str(n_samples)],
            ]
            sum_table = Table(summary, colWidths=[5*cm, 11*cm])
            sum_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#eff6ff')),
            ]))
            story.append(sum_table)
            story.append(Spacer(1, 0.3*cm))

            if contribs:
                top_feature = contribs[0]["feature"]
                top_importance = contribs[0]["mean_abs_shap_value"]
                story.append(Paragraph(
                    f"最重要的特征是 <b>{top_feature}</b>，其平均|SHAP|值为 <b>{top_importance:.6f}</b>，"
                    f"对模型预测的贡献最大。",
                    normal_style
                ))

            if backtest_result:
                story.append(PageBreak())
                story.append(Paragraph("三、回测绩效摘要", h2_style))
                ic = backtest_result.get("ic_stats", {})
                bt_data = [
                    ["IC均值", f"{ic.get('mean_ic', 'N/A')}"],
                    ["ICIR", f"{ic.get('icir', 'N/A')}"],
                    ["P值", f"{ic.get('p_value', 'N/A')}"],
                ]
                ls = backtest_result.get("long_short_return", {})
                bt_data.extend([
                    ["多空组合年化收益", f"{ls.get('annualized_return', 'N/A')}"],
                    ["多空组合夏普比率", f"{ls.get('sharpe_ratio', 'N/A')}"],
                ])
                bt_table = Table(bt_data, colWidths=[5*cm, 11*cm])
                bt_table.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecfdf5')),
                ]))
                story.append(bt_table)

            story.append(Spacer(1, 1*cm))
            story.append(Paragraph("— 报告由 Stock Factor Workbench 自动生成 —", ParagraphStyle(
                'Footer', parent=normal_style, alignment=1, textColor=colors.grey, fontSize=9
            )))

        else:
            story.append(Paragraph(f"分析失败: {shap_result.get('message', '未知错误')}", normal_style))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes


shap_analyzer = ShapAnalyzer()
