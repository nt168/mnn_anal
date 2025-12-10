#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回归分析算法模块

实现线性和非线性回归分析
"""

import numpy as np
from typing import Dict, Any, Tuple, Optional, List
from scipy import stats
from scipy.optimize import curve_fit
import warnings
from utils.logger import LoggerManager
from .utils import transform_variable_name

warnings.filterwarnings('ignore', category=RuntimeWarning)


class RegressionAnalyzer:
    """回归分析器"""

    def __init__(self):
        """初始化回归分析器"""
        self.logger = LoggerManager.get_logger("RegressionAnalyzer")

    def analyze_regression(self, x_data: np.ndarray, y_data: np.ndarray,
                         x_name: str = "X", y_name: str = "Y") -> Dict[str, Any]:
        """
        执行回归分析

        Args:
            x_data: X轴数据
            y_data: Y轴数据
            x_name: X轴名称
            y_name: Y轴名称

        Returns:
            回归分析结果
        """
        try:
            # 数据预处理
            x_clean, y_clean = self._clean_data(x_data, y_data)
            if len(x_clean) < 3:
                raise ValueError("有效数据点太少，无法进行回归分析")

            # 尝试线性回归
            linear_result = self._linear_regression(x_clean, y_clean)

            # 评估线性回归质量
            linear_quality = self._evaluate_regression_quality(linear_result, len(x_clean))

            # 如果线性回归质量不佳，尝试非线性回归
            nonlinear_result = None
            if linear_quality['score'] < 0.7:  # R² < 0.7 认为质量不佳
                nonlinear_result = self._try_nonlinear_regression(x_clean, y_clean)

                # 选择最佳回归
                if nonlinear_result and nonlinear_result['r2'] > linear_result['r2']:
                    best_result = nonlinear_result
                    best_result['type'] = 'nonlinear'
                else:
                    best_result = linear_result
                    best_result['type'] = 'linear'
            else:
                best_result = linear_result
                best_result['type'] = 'linear'

            # 计算预测值和残差
            y_pred = self._predict_values(best_result, x_clean)
            residuals = y_clean - y_pred

            # 构造完整结果
            result = {
                'x_name': x_name,
                'y_name': y_name,
                'data_points': len(x_clean),
                'x_data': x_clean.tolist(),
                'y_data': y_clean.tolist(),
                'y_predicted': y_pred.tolist(),
                'residuals': residuals.tolist(),
                'regression': best_result,
                'quality': self._evaluate_regression_quality(best_result, len(x_clean)),
                'equation': self._format_equation(best_result, x_name, y_name),
                'summary': self._generate_summary(best_result, linear_quality, x_name, y_name)
            }

            return result

        except Exception as e:
            self.logger.error(f"回归分析失败: {e}")
            raise

    def _clean_data(self, x_data: np.ndarray, y_data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        清理数据，移除无效值

        Args:
            x_data: X轴数据
            y_data: Y轴数据

        Returns:
            清理后的X, Y数据
        """
        # 移除NaN和无穷值
        mask = np.isfinite(x_data) & np.isfinite(y_data)
        x_clean = x_data[mask]
        y_clean = y_data[mask]

        # 如果还有重复的X值，保留Y最大的
        unique_x, indices = np.unique(x_clean, return_inverse=True)
        max_y_for_x = np.zeros(len(unique_x))
        for i, idx in enumerate(indices):
            if y_clean[i] > max_y_for_x[idx]:
                max_y_for_x[idx] = y_clean[i]

        return unique_x, max_y_for_x

    def _linear_regression(self, x_data: np.ndarray, y_data: np.ndarray) -> Dict[str, Any]:
        """
        线性回归分析

        Args:
            x_data: X轴数据
            y_data: Y轴数据

        Returns:
            线性回归结果
        """
        slope, intercept, r_value, p_value, std_err = stats.linregress(x_data, y_data)

        return {
            'method': 'linear',
            'slope': slope,
            'intercept': intercept,
            'r2': r_value ** 2,
            'p_value': p_value,
            'std_error': std_err,
            'slope_ci': self._calculate_confidence_interval(slope, std_err, len(x_data))
        }

    def _try_nonlinear_regression(self, x_data: np.ndarray, y_data: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        尝试非线性回归

        Args:
            x_data: X轴数据
            y_data: Y轴数据

        Returns:
            最佳非线性回归结果或None
        """
        models_to_try = [
            ('quadratic', self._quadratic_func, [1, 0.1, 0]),
            ('exponential', self._exponential_func, [max(y_data), 0.1]),
            ('logarithmic', self._logarithmic_func, [1, 0]),
            ('power', self._power_func, [1, 1])
        ]

        best_model = None
        best_r2 = -1

        for name, func, p0 in models_to_try:
            try:
                popt, pcov = curve_fit(func, x_data, y_data, p0=p0, maxfev=10000)

                # 计算R²
                y_pred = func(x_data, *popt)
                ss_res = np.sum((y_data - y_pred) ** 2)
                ss_tot = np.sum((y_data - np.mean(y_data)) ** 2)
                r2 = 1 - (ss_res / ss_tot)

                if r2 > best_r2:
                    best_r2 = r2
                    best_model = {
                        'method': name,
                        'function': func,
                        'parameters': popt.tolist(),
                        'covariance': pcov.tolist(),
                        'r2': r2
                    }

            except Exception:
                continue  # 跳过拟合失败的模型

        return best_model

    def _quadratic_func(self, x, a, b, c):
        """二次函数 y = ax² + bx + c"""
        return a * x**2 + b * x + c

    def _exponential_func(self, x, a, b):
        """指数函数 y = a * exp(bx)"""
        return a * np.exp(b * x)

    def _logarithmic_func(self, x, a, b):
        """对数函数 y = a * ln(x) + b"""
        return a * np.log(x + 1) + b  # +1 避免ln(0)

    def _power_func(self, x, a, b):
        """幂函数 y = a * x^b"""
        return a * np.power(x, b)

    def _predict_values(self, regression_result: Dict[str, Any], x_data: np.ndarray) -> np.ndarray:
        """
        使用回归结果预测Y值

        Args:
            regression_result: 回归结果
            x_data: X轴数据

        Returns:
            预测的Y值
        """
        if regression_result['method'] == 'linear':
            slope = regression_result['slope']
            intercept = regression_result['intercept']
            return slope * x_data + intercept
        else:
            func = regression_result['function']
            params = regression_result['parameters']
            return func(x_data, *params)

    def _evaluate_regression_quality(self, regression_result: Dict[str, Any], n_points: int) -> Dict[str, Any]:
        """
        评估回归质量

        Args:
            regression_result: 回归结果
            n_points: 数据点数量

        Returns:
            质量评估结果
        """
        r2 = regression_result['r2']

        # 质量等级
        if r2 >= 0.9:
            quality = 'excellent'
            score = r2
        elif r2 >= 0.7:
            quality = 'good'
            score = r2
        elif r2 >= 0.5:
            quality = 'fair'
            score = r2 * 0.8
        else:
            quality = 'poor'
            score = r2 * 0.6

        # 样本充足性
        if n_points >= 10:
            sample_adequacy = 'excellent'
        elif n_points >= 7:
            sample_adequacy = 'good'
        elif n_points >= 5:
            sample_adequacy = 'fair'
        else:
            sample_adequacy = 'poor'

        return {
            'quality': quality,
            'score': score,
            'r2': r2,
            'n_points': n_points,
            'sample_adequacy': sample_adequacy,
            'recommendation': self._get_recommendation(quality, sample_adequacy)
        }

    def _get_recommendation(self, quality: str, sample_adequacy: str) -> str:
        """获取建议"""
        if quality == 'excellent' and sample_adequacy != 'poor':
            return "回归质量极佳，结果可信度高"
        elif quality == 'good' and sample_adequacy != 'poor':
            return "回归质量良好，结果具有参考价值"
        elif quality == 'fair':
            return "回归质量一般，建议结合其他分析方法"
        else:
            return "回归质量较差，建议增加数据点或尝试其他分析方法"

    def _format_equation(self, regression_result: Dict[str, Any], x_name: str, y_name: str) -> str:
        """
        格式化回归方程

        Args:
            regression_result: 回归结果
            x_name: X轴名称
            y_name: Y轴名称

        Returns:
            格式化的方程字符串
        """
        if regression_result['method'] == 'linear':
            slope = regression_result['slope']
            intercept = regression_result['intercept']

            if abs(intercept) < 0.001:
                return f"{y_name} = {slope:.4f} × {x_name}"
            elif intercept > 0:
                return f"{y_name} = {slope:.4f} × {x_name} + {intercept:.4f}"
            else:
                return f"{y_name} = {slope:.4f} × {x_name} - {abs(intercept):.4f}"

        elif regression_result['method'] == 'quadratic':
            a, b, c = regression_result['parameters']
            return f"{y_name} = {a:.4f} × {x_name}² + {b:.4f} × {x_name} + {c:.4f}"

        elif regression_result['method'] == 'exponential':
            a, b = regression_result['parameters']
            return f"{y_name} = {a:.4f} × e^({b:.4f} × {x_name})"

        elif regression_result['method'] == 'logarithmic':
            a, b = regression_result['parameters']
            return f"{y_name} = {a:.4f} × ln({x_name}) + {b:.4f}"

        elif regression_result['method'] == 'power':
            a, b = regression_result['parameters']
            return f"{y_name} = {a:.4f} × {x_name}^{b:.4f}"

        else:
            return "复杂回归方程"

    def _generate_summary(self, regression_result: Dict[str, Any],
                         linear_quality: Dict[str, Any], x_name: str, y_name: str) -> str:
        """
        生成分析摘要

        Args:
            regression_result: 回归结果
            linear_quality: 线性回归质量
            x_name: X轴名称
            y_name: Y轴名称

        Returns:
            分析摘要
        """
        r2 = regression_result['r2']
        method = regression_result['method']

        if method == 'linear':
            method_desc = "线性回归"
        elif method == 'quadratic':
            method_desc = "二次回归"
        elif method == 'exponential':
            method_desc = "指数回归"
        elif method == 'logarithmic':
            method_desc = "对数回归"
        elif method == 'power':
            method_desc = "幂函数回归"
        else:
            method_desc = "非线性回归"

        summary = f"采用{method_desc}方法分析{y_name}与{transform_variable_name(x_name)}的关系。"
        summary += f"回归决定系数R² = {r2:.4f}，"

        if r2 >= 0.9:
            summary += "表明拟合效果极佳。"
        elif r2 >= 0.7:
            summary += "表明拟合效果良好。"
        elif r2 >= 0.5:
            summary += "表明拟合效果一般。"
        else:
            summary += "表明拟合效果较差。"

        # 如果尝试了非线性搜索，添加说明
        if linear_quality['score'] < 0.7:
            summary += f"由于线性回归质量不佳(R²={linear_quality['r2']:.3f})，"
            summary += f"自动选择了{method_desc}以获得更好的拟合效果。"

        return summary

    def _calculate_confidence_interval(self, slope: float, std_err: float, n: int) -> List[float]:
        """
        计算斜率的95%置信区间

        Args:
            slope: 斜率
            std_err: 标准误差
            n: 样本量

        Returns:
            置信区间 [lower, upper]
        """
        from scipy import stats
        t_value = stats.t.ppf(0.975, n - 2)  # 95%置信度
        lower = slope - t_value * std_err
        upper = slope + t_value * std_err
        return [lower, upper]


