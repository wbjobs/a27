import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple
import warnings
warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)


class PortfolioOptimizer:
    def __init__(self):
        self.factor_names: List[str] = []
        self.factor_returns: Optional[pd.DataFrame] = None
        self.cov_matrix: Optional[pd.DataFrame] = None
        self.expected_returns: Optional[pd.Series] = None

    def _prepare_data(
        self,
        factors: List[Dict[str, Any]],
        dataset_name: str
    ) -> bool:
        if len(factors) < 2:
            raise ValueError("组合优化至少需要2个因子")

        self.factor_names = []
        factor_dfs = {}

        for item in factors:
            name = item.get("name", f"factor_{len(factor_dfs)}")
            values = item.get("factor_values", item.get("values", []))
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
            raise ValueError(f"有效因子仅{len(factor_dfs)}个，需要至少2个")

        self.factor_names = list(factor_dfs.keys())
        combined = pd.DataFrame(factor_dfs)
        combined = combined.ffill().dropna()

        if combined.empty or len(combined) < 20:
            raise ValueError(f"对齐后数据不足({len(combined)}行)，无法进行优化")

        self.factor_returns = combined
        self.expected_returns = combined.mean() * 252
        self.cov_matrix = combined.cov() * 252

        return True

    def optimize_mean_variance(
        self,
        target_return: Optional[float] = None,
        risk_free_rate: float = 0.03,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
        objective: str = "max_sharpe"
    ) -> Tuple[Dict[str, float], float, float, float]:
        try:
            import cvxpy as cp
        except ImportError:
            return self._optimize_numpy(risk_free_rate, min_weight, max_weight, objective)

        n = len(self.factor_names)
        w = cp.Variable(n)
        ret = self.expected_returns.values @ w
        risk = cp.quad_form(w, self.cov_matrix.values)

        constraints = [
            cp.sum(w) == 1.0,
            w >= min_weight,
            w <= max_weight
        ]

        if target_return is not None:
            constraints.append(ret >= target_return)
            prob = cp.Problem(cp.Minimize(risk), constraints)
        else:
            if objective == "min_variance":
                prob = cp.Problem(cp.Minimize(risk), constraints)
            elif objective == "max_sharpe":
                sharpe = (ret - risk_free_rate) / cp.sqrt(risk)
                prob = cp.Problem(cp.Maximize(sharpe), constraints)
            else:
                prob = cp.Problem(cp.Maximize(ret), constraints)

        try:
            prob.solve(solver=cp.SCS, eps=1e-6, max_iters=10000)
        except Exception as e:
            logger.warning(f"CVXPY solve failed ({e}), falling back to numpy")
            return self._optimize_numpy(risk_free_rate, min_weight, max_weight, objective)

        if prob.status not in ["optimal", "optimal_inaccurate"]:
            logger.warning(f"Optimization status: {prob.status}, falling back to equal weights")
            return self._optimize_equal_weight()

        weights = np.maximum(w.value, min_weight)
        weights = weights / weights.sum()
        weights_dict = dict(zip(self.factor_names, [round(float(x), 6) for x in weights]))

        exp_ret = float(np.dot(self.expected_returns.values, weights))
        exp_vol = float(np.sqrt(weights @ self.cov_matrix.values @ weights.T))
        sharpe = (exp_ret - risk_free_rate) / exp_vol if exp_vol > 0 else 0

        return weights_dict, exp_ret, exp_vol, sharpe

    def _optimize_numpy(
        self,
        risk_free_rate: float,
        min_weight: float,
        max_weight: float,
        objective: str
    ) -> Tuple[Dict[str, float], float, float, float]:
        n = len(self.factor_names)

        if objective == "equal_weight":
            return self._optimize_equal_weight()

        if objective == "min_variance":
            inv_diag = 1.0 / np.diag(self.cov_matrix.values)
            weights = inv_diag / inv_diag.sum()
        elif objective == "inverse_vol":
            vols = np.sqrt(np.diag(self.cov_matrix.values))
            weights = (1.0 / vols) / (1.0 / vols).sum()
        else:
            er = self.expected_returns.values
            weights = er / er.sum() if er.sum() > 0 else np.ones(n) / n

        weights = np.clip(weights, min_weight, max_weight)
        weights = weights / weights.sum()

        weights_dict = dict(zip(self.factor_names, [round(float(x), 6) for x in weights]))
        exp_ret = float(np.dot(self.expected_returns.values, weights))
        exp_vol = float(np.sqrt(weights @ self.cov_matrix.values @ weights.T))
        sharpe = (exp_ret - risk_free_rate) / exp_vol if exp_vol > 0 else 0

        return weights_dict, exp_ret, exp_vol, sharpe

    def _optimize_equal_weight(self) -> Tuple[Dict[str, float], float, float, float]:
        n = len(self.factor_names)
        weights = np.ones(n) / n
        weights_dict = dict(zip(self.factor_names, [round(float(x), 6) for x in weights]))
        exp_ret = float(np.dot(self.expected_returns.values, weights))
        exp_vol = float(np.sqrt(weights @ self.cov_matrix.values @ weights.T))
        sharpe = (exp_ret - 0.03) / exp_vol if exp_vol > 0 else 0
        return weights_dict, exp_ret, exp_vol, sharpe

    def optimize_risk_parity(
        self,
        risk_free_rate: float = 0.03,
        min_weight: float = 0.0,
        max_weight: float = 1.0
    ) -> Tuple[Dict[str, float], float, float, float, Dict[str, float]]:
        try:
            import cvxpy as cp
            n = len(self.factor_names)
            w = cp.Variable(n, nonneg=True)
            cov = self.cov_matrix.values
            sigma = cp.sqrt(cp.quad_form(w, cov))
            risk_contrib = cp.multiply(w, (cov @ w)) / sigma
            target = sigma / n
            constraints = [cp.sum(w) == 1.0, w >= min_weight, w <= max_weight]
            obj = cp.sum_squares(risk_contrib - target)
            prob = cp.Problem(cp.Minimize(obj), constraints)
            prob.solve(solver=cp.SCS, eps=1e-6)

            if prob.status not in ["optimal", "optimal_inaccurate"]:
                raise Exception(f"Status: {prob.status}")

            weights = np.maximum(w.value, 0)
            weights = weights / weights.sum()
        except Exception as e:
            logger.warning(f"Risk parity optimization failed ({e}), using inverse volatility")
            vols = np.sqrt(np.diag(self.cov_matrix.values))
            weights = (1.0 / vols) / (1.0 / vols).sum()

        weights = np.clip(weights, min_weight, max_weight)
        weights = weights / weights.sum()
        weights_dict = dict(zip(self.factor_names, [round(float(x), 6) for x in weights]))

        exp_ret = float(np.dot(self.expected_returns.values, weights))
        exp_vol = float(np.sqrt(weights @ self.cov_matrix.values @ weights.T))
        sharpe = (exp_ret - risk_free_rate) / exp_vol if exp_vol > 0 else 0

        marginal_risk = self.cov_matrix.values @ weights
        total_risk = exp_vol
        risk_contrib = (weights * marginal_risk) / total_risk if total_risk > 0 else weights * 0
        risk_contrib_dict = dict(zip(self.factor_names, [round(float(x), 6) for x in risk_contrib]))

        return weights_dict, exp_ret, exp_vol, sharpe, risk_contrib_dict

    def compute_efficient_frontier(
        self,
        risk_free_rate: float = 0.03,
        n_points: int = 30,
        min_weight: float = 0.0,
        max_weight: float = 1.0
    ) -> List[Dict[str, Any]]:
        try:
            import cvxpy as cp
        except ImportError:
            return self._compute_efficient_frontier_numpy(risk_free_rate, n_points, min_weight, max_weight)

        n = len(self.factor_names)
        min_ret = float(self.expected_returns.min())
        max_ret = float(self.expected_returns.max())
        points = []

        for target in np.linspace(min_ret, max_ret, n_points):
            try:
                w = cp.Variable(n)
                ret = self.expected_returns.values @ w
                risk = cp.quad_form(w, self.cov_matrix.values)
                constraints = [cp.sum(w) == 1.0, w >= min_weight, w <= max_weight, ret >= target]
                prob = cp.Problem(cp.Minimize(risk), constraints)
                prob.solve(solver=cp.SCS, eps=1e-5, max_iters=5000)

                if prob.status in ["optimal", "optimal_inaccurate"]:
                    weights = np.maximum(w.value, 0)
                    weights = weights / weights.sum()
                    w_dict = dict(zip(self.factor_names, [round(float(x), 4) for x in weights]))
                    er = float(np.dot(self.expected_returns.values, weights))
                    ev = float(np.sqrt(weights @ self.cov_matrix.values @ weights.T))
                    points.append({
                        "expected_return": round(er, 6),
                        "expected_volatility": round(ev, 6),
                        "sharpe_ratio": round((er - risk_free_rate) / ev if ev > 0 else 0, 4),
                        "weights": w_dict
                    })
            except Exception:
                continue

        return points if points else self._compute_efficient_frontier_numpy(risk_free_rate, n_points, min_weight, max_weight)

    def _compute_efficient_frontier_numpy(
        self,
        risk_free_rate: float,
        n_points: int,
        min_weight: float,
        max_weight: float
    ) -> List[Dict[str, Any]]:
        n = len(self.factor_names)
        points = []
        for i in range(n_points):
            alpha = i / max(n_points - 1, 1)
            weights = np.array([alpha + (1 - alpha) / n] + [(1 - alpha) / n] * (n - 1))
            weights = np.clip(weights, min_weight, max_weight)
            weights = weights / weights.sum()
            er = float(np.dot(self.expected_returns.values, weights))
            ev = float(np.sqrt(weights @ self.cov_matrix.values @ weights.T))
            w_dict = dict(zip(self.factor_names, [round(float(x), 4) for x in weights]))
            points.append({
                "expected_return": round(er, 6),
                "expected_volatility": round(ev, 6),
                "sharpe_ratio": round((er - risk_free_rate) / ev if ev > 0 else 0, 4),
                "weights": w_dict
            })
        return points

    def monte_carlo_simulation(
        self,
        n_simulations: int = 2000,
        risk_free_rate: float = 0.03,
        min_weight: float = 0.0,
        max_weight: float = 1.0
    ) -> List[Dict[str, Any]]:
        n = len(self.factor_names)
        results = []

        for _ in range(n_simulations):
            weights = np.random.rand(n)
            weights = np.clip(weights, min_weight, max_weight)
            weights = weights / weights.sum()
            er = float(np.dot(self.expected_returns.values, weights))
            ev = float(np.sqrt(weights @ self.cov_matrix.values @ weights.T))
            w_dict = dict(zip(self.factor_names, [round(float(x), 4) for x in weights]))
            results.append({
                "expected_return": round(er, 6),
                "expected_volatility": round(ev, 6),
                "sharpe_ratio": round((er - risk_free_rate) / ev if ev > 0 else 0, 4),
                "weights": w_dict
            })

        return results

    def optimize(
        self,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        self._prepare_data(request["factors"], request["dataset_name"])

        model = request.get("model", "mean_variance")
        rf = request.get("risk_free_rate", 0.03)
        min_w = request.get("min_weight", 0.0)
        max_w = request.get("max_weight", 1.0)
        target_ret = request.get("target_return")

        risk_contributions = None

        if model == "mean_variance":
            weights, exp_ret, exp_vol, sharpe = self.optimize_mean_variance(
                target_ret, rf, min_w, max_w, "max_sharpe"
            )
        elif model == "min_variance":
            weights, exp_ret, exp_vol, sharpe = self.optimize_mean_variance(
                target_ret, rf, min_w, max_w, "min_variance"
            )
        elif model == "max_sharpe":
            weights, exp_ret, exp_vol, sharpe = self.optimize_mean_variance(
                target_ret, rf, min_w, max_w, "max_sharpe"
            )
        elif model == "equal_weight":
            weights, exp_ret, exp_vol, sharpe = self._optimize_equal_weight()
        elif model == "risk_parity":
            weights, exp_ret, exp_vol, sharpe, risk_contributions = self.optimize_risk_parity(
                rf, min_w, max_w
            )
        else:
            weights, exp_ret, exp_vol, sharpe = self._optimize_equal_weight()

        efficient_frontier = self.compute_efficient_frontier(rf, 30, min_w, max_w)
        monte_carlo = self.monte_carlo_simulation(2000, rf, min_w, max_w)

        result = {
            "success": True,
            "message": f"组合优化完成，模型: {model}",
            "weights": weights,
            "expected_return": round(float(exp_ret), 6),
            "expected_volatility": round(float(exp_vol), 6),
            "sharpe_ratio": round(float(sharpe), 4),
            "efficient_frontier": efficient_frontier,
            "monte_carlo_points": monte_carlo
        }

        if risk_contributions:
            result["risk_contributions"] = risk_contributions

        return result


portfolio_optimizer = PortfolioOptimizer()
