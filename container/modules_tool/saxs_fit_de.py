from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from rdetoolkit.exceptions import StructuredError
from rdetoolkit.graph.api.csv2graph import plot_from_dataframe
from scipy import stats
from scipy.optimize import differential_evolution

source_lambda = 0.154  # [nm]
SMALL_QR_THRESHOLD = 1e-3


def single_particle_scattering(q: np.ndarray, r: float) -> list[float]:
    """単一粒子の散乱関数.

    Args:
        q: 散乱ベクトルの大きさ
        r: 粒子の半径

    Returns:
        list[float]: ?

    """
    qr = q * r
    # 小さいqrに対するTaylor展開（数値安定性のため）
    small_qr = qr < SMALL_QR_THRESHOLD
    result = np.zeros_like(qr)

    if np.any(~small_qr):
        qr_large = qr[~small_qr]
        result[~small_qr] = (3 * (np.sin(qr_large) - qr_large * np.cos(qr_large)) / (qr_large ** 3)) ** 2

    # 小さいqrの場合のTaylor展開近似
    if np.any(small_qr):
        qr_small = qr[small_qr]
        # F(qr) ≈ 1 - (qr)²/10 + (qr)⁴/280 for small qr
        result[small_qr] = (1 - qr_small ** 2 / 10 + qr_small ** 4 / 280) ** 2

    return result


def scattering_with_size_distribution(q: np.ndarray, r_mean: float, r_sigma: float, h: float) -> np.ndarray:
    """粒径分布を考慮した球形粒子の散乱関数.

    Args:
        q: 散乱ベクトルの大きさ（1D numpy配列）
        r_mean: 粒子の平均半径
        r_sigma: 粒子の半径の分散
        h: 散乱強度

    Returns:
        list[float]: ?

    """
    # ガウス分布に基づく積分（半径は正の値のみ）
    # r_min = max(0.01, r_mean - 3 * r_sigma)  # 最小値を0.01 nmに設定
    r_min = max(0.0, r_mean - 3 * r_sigma)     # 最小値を0.0  nmに設定
    r_max = r_mean + 3 * r_sigma
    r_values = np.linspace(r_min, r_max, 100)
    r_step = np.mean(np.diff(r_values))
    weights = np.exp(-0.5 * ((r_values - r_mean) / r_sigma) ** 2) / (r_sigma * np.sqrt(2 * np.pi))

    integrated_scattering = np.zeros(len(q))
    for w_i, r_i in zip(weights, r_values, strict=False):
        if r_i > 0:
            scattering_per_r = single_particle_scattering(q, r_i)
            integrated_scattering += (w_i * scattering_per_r) * r_step

    return h * integrated_scattering


def cost_function(params: list[float], q: np.ndarray, y: np.ndarray) -> float:
    """コスト関数（残差の二乗平均）.

    Args:
        params: 最適化するパラメータの辞書（球の半径rと対数空間の強度h）
        q: 散乱ベクトルの大きさ（実験データから）
        y: 観測された散乱強度（実験データから）

    Returns:
        float: 平均値

    """
    mean_ln, sigma_ln, h_log = params[0], params[1], params[2]
    mean_linear = np.exp(mean_ln)
    sigma_linear = np.exp(sigma_ln)
    h_linear = 10.0 ** h_log
    y_predicted = scattering_with_size_distribution(q, mean_linear, sigma_linear, h_linear)

    if np.any(y_predicted <= 0) or np.any(np.isnan(y_predicted)) or np.any(np.isinf(y_predicted)):
        return 1e10

    y_int = np.round(y).astype(int)

    try:
        nll = -1 * stats.poisson.logpmf(y_int, y_predicted)
        cost = np.mean(nll)
        if np.isnan(cost) or np.isinf(cost):
            return 1e10
        return cost
    except Exception:
        return 1e10


def load_filtered_data(df_data: pd.DataFrame, path: Path, log_file: Path) -> tuple[list, list]:
    """Load filtere data.

    Args:
        df_data (pd.DataFrame): Loaded dataframe.
        path (Path): Loaded file.
        log_file: ログファイルのパス

    Returns:
        q: 散乱ベクトルの大きさ（実験データから）
        y: 観測された散乱強度（実験データから）

    """
    log_to_file("Loading data...", filename=log_file)
    log_to_file(f"Load data from {path}", filename=log_file)

    data = df_data.to_numpy().astype(float)
    x = data[:, 0]
    y = data[:, 2]
    q = 4 * np.pi * np.sin(np.deg2rad(x / 2.0)) / source_lambda
    mask = (q > 1)
    q = q[mask]
    y = y[mask]

    log_to_file(f"Data loaded: {len(q)} points", filename=log_file)
    log_to_file(f"Q range: {q.min():.3f} - {q.max():.3f}", filename=log_file)
    log_to_file(f"Intensity range: {y.min():.3f} - {y.max():.3f}", filename=log_file)
    log_to_file(f"Any NaN in q: {np.any(np.isnan(q))}", filename=log_file)
    log_to_file(f"Any NaN in y: {np.any(np.isnan(y))}", filename=log_file)

    return q, y


def fit(
    q: np.ndarray,
    y: np.ndarray,
    config: dict,
    log_file: Path | str,
    seed: int = 123,
) -> tuple[float | None, np.ndarray | None]:
    """Exec scipy differential evolution.

    Args:
        q: 散乱ベクトルの大きさ（実験データから）
        y: 観測された散乱強度（実験データから）
        config: config.
        log_file: save name for log file.
        seed (int, optional): 0-9.

    Returns:
        ?: ?
        ?: ?

    """
    log_to_file(f"  Trying optimization with seed {seed}...", filename=log_file)

    bounds_key_to_check = ['mean_min', 'mean_max', 'sigma_min', 'sigma_max', 'h_log_min', 'h_log_max']

    if all(key in config['saxs'] for key in bounds_key_to_check):
        bounds = [
            (np.log(config['saxs']['mean_min']), np.log(config['saxs']['mean_max'])),
            (np.log(config['saxs']['sigma_min']), np.log(config['saxs']['sigma_max'])),
            (config['saxs']['h_log_min'], config['saxs']['h_log_max']),
        ]
    else:
        bounds = [
            (np.log(0.1), np.log(50.0)),
            (np.log(0.05), np.log(10.0)),
            (2.0, 6.0),
        ]

    result = differential_evolution(
        cost_function,
        bounds=bounds,
        args=(q, y),
        seed=seed,
        mutation=(0.5, 1.5),
        popsize=50,
        maxiter=1000,
        atol=1e-8,
        tol=1e-8,
    )
    if (result.success):
        return result.fun, result.x

    log_to_file(f"Optimization failed with seed {seed}: {result.message}", filename=log_file)
    return None, None


def set_fitted_result(
    q: np.ndarray,
    y: np.ndarray,
    sample_id: str,
    opt_param: list[float],
    log_file: Path | str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Set fitted result.

    Args:
        q: 散乱ベクトルの大きさ
        y: 観測された散乱強度
        sample_id (str): sample id.
        opt_param (list | None): fitting parameter.
        log_file: ログファイルのパス

    Returns:
        pd.DataFrame: fitting data.
        dict: fitting result.

    """
    mean_ln, sigma_ln, h_log = opt_param[0], opt_param[1], opt_param[2]
    mean_hat = np.exp(mean_ln)
    sigma_hat = np.exp(sigma_ln)
    h_hat = 10.0 ** h_log
    cost = cost_function(opt_param, q, y)

    log_to_file("===" * 8, filename=log_file)
    log_to_file(f"強度 = {h_hat:.2f}", filename=log_file)
    log_to_file(f"半径：平均 = {mean_hat:.2f} [nm], 標準偏差 = {sigma_hat:.2f} [nm]", filename=log_file)
    log_to_file(f"Cost = {cost:.2}", filename=log_file)
    log_to_file("===" * 8, filename=log_file)

    f_hat = scattering_with_size_distribution(q, mean_hat, sigma_hat, h_hat)

    data = pd.DataFrame({
        'q (nm^-1)': q,
        'Experimental Intensity (counts)': y,
        'Fitted Intensity (counts)': f_hat,
    })
    result_dict: dict = {
        "sample_id": sample_id,
        "mean": mean_hat,
        "sigma": sigma_hat,
        "intensity": h_hat,
        "cost": cost,
    }
    return data, result_dict


def plot_size_distribution(result_dict: dict) -> pd.DataFrame:
    """Create Gaussian size distribution DataFrame from fitting results.

    Args:
        result_dict (dict): Dictionary containing fitting results with 'mean' and 'sigma' keys.

    Returns:
        pd.DataFrame: DataFrame with 'Particle Radius (nm)' and 'Probability Density (nm^-1)' columns.

    """
    mean_radius = result_dict["mean"]
    std_radius = result_dict["sigma"]

    r_min_calc = mean_radius - 4 * std_radius
    r_max = mean_radius + 4 * std_radius
    r_values = np.linspace(r_min_calc, r_max, 1000)

    gaussian_pdf = (1 / (std_radius * np.sqrt(2 * np.pi))) * \
        np.exp(-0.5 * ((r_values - mean_radius) / std_radius) ** 2)

    return pd.DataFrame({
        'Particle Radius (nm)': r_values,
        'Probability Density (nm^-1)': gaussian_pdf,
    })


def log_to_file(
    message: str,
    level: str = "INFO",
    filename: Path | str = "app.log",
) -> None:
    """Write log message to file.

    Args:
        message: ログメッセージ
        level: ログレベル (INFO, DEBUG, ERRORなど)
        filename: 出力ファイルパス

    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"{timestamp} - {level} - {message}\n"

    with open(filename, 'a') as file:
        file.write(log_message)


def main_fitting(
    srcpath_data: Path,
    data: dict[str, pd.DataFrame],
    config: dict,
    resource_paths: Path,
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    """Run SAXS fitting.

    Args:
        srcpath_data: Input file path.
        data: Measurement data for each region.
        config: Configuration.
        resource_paths: Output resource paths.

    Returns:
        tuple containing fitting_data and fitting_result.

    """
    save_name = os.path.splitext(os.path.basename(srcpath_data))[0]

    log_file = resource_paths.struct.joinpath(f"{save_name}_fitting.log")
    log_to_file(save_name, filename=log_file)

    fitting_data: dict[str, pd.DataFrame] = {}
    fitting_result: dict[str, pd.DataFrame] = {}
    for region_key, df in data.items():
        q, y = load_filtered_data(df, srcpath_data, log_file)

        opt_cost = 1e5
        opt_param = None
        successful_fits = 0
        # Use all available CPU cores for parallel fitting (n_jobs=-1).
        # Execution time and CPU load depend on the machine resources and
        # the load from other processes.
        results = Parallel(n_jobs=-1)(
            delayed(fit)(q, y, config, log_file, i)
            for i in range(10)
        )

        costs, params = zip(*results, strict=False)

        for cost, param in zip(costs, params, strict=False):
            if cost is not None and cost < opt_cost:
                opt_cost = cost
                opt_param = param
                successful_fits += 1
                log_to_file(
                    f"  Success! Cost: {cost:.3f}",
                    filename=log_file,
                )
            else:
                log_to_file(
                    "  Failed",
                    filename=log_file,
                )

        log_to_file(
            f"Total successful fits: {successful_fits}/10",
            filename=log_file,
        )

        if opt_param is None:
            msg = f"Optimization failed for region '{region_key}'."
            raise StructuredError(
                msg,
            )

        fitted_df, result_dict = set_fitted_result(
            q,
            y,
            save_name,
            opt_param,
            log_file,
        )

        fitting_data[region_key] = fitted_df
        fitting_result[region_key] = pd.DataFrame(
            result_dict,
            index=[0],
        )

        df_gaussian = plot_size_distribution(result_dict)

        plot_from_dataframe(
            df=df_gaussian,
            logy=False,
            html=False,
            output_dir=str(resource_paths.other_image),
            name=f"gaussian_distribution_{region_key}",
            no_individual=True,
            xlim=(0, df_gaussian.iloc[:, 0].max() * 1.05),
            ylim=(0, df_gaussian.iloc[:, 1].max() * 1.05),
            title="Gaussian Size Distribution",
        )

    return fitting_data, fitting_result
