# ----------------------------------------------------------------------
# Copyright (c) 2024 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

from datetime import datetime
from math import log10
import statistics
from collections import Counter

# ---------------------------
# Third-party library imports
# ----------------------------

import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
from lica.asyncio.photometer import Role

# --------------
# local imports
# -------------

from ..constants import ZP_ABS, FreqSequence, TimeSequence

def stats(
    series: list[float, ...], use_median: bool = False
) -> tuple[float, float, list[float, ...]]:
    """Compute mean(/median and std dev around central tendency"""
    central = statistics.median_low(series) if use_median else statistics.fmean(series)
    std_dev = statistics.stdev(series, xbar=central)
    modes = statistics.multimode(series)
    return central, std_dev, modes


def samples(
    session: datetime,
    roles: list[Role, ...],
    freqs: list[FreqSequence, ...],
    tstamps: list[TimeSequence, ...],
    names: list[str, ...],
    use_median: bool = False,
    zp_abs: float = ZP_ABS,
) -> None:
    """Grafica Frecuencia vs Tiempo en N rondas"""
    session_id = session.strftime("%Y-%m-%dT%H:%M:%S")
    fig, axes = plt.subplots(1, figsize=(15, 5))
    central = "median" if use_median else "mean"
    n = len(roles)
    axes = [
        axes,
    ] * n
    colors = ("tab:red", "tab:blue") if n == 2 else ("tab:red",)
    roles_dict = dict()
    for i, ax, role, freq, tstamp, name, color, role in zip(
        range(1, n + 1), axes, roles, freqs, tstamps, names, colors, roles
    ):
        cen, std, modes = stats(freq, use_median=use_median)
        roles_dict[role] = (cen, std, modes)
        ax.set_title(f"Session {session_id}")
        ax.set_ylabel("Frecuency (Hz)")
        # Medidas
        ax.plot(tstamp, freq, color=color, marker=".", linestyle="none", label=f"{name}")
        # Tendencias centrales
        ax.axhline(y=cen, linestyle=":", color=color, label=f"{central} = {cen:.3f}")
        # Barra horizontal semitransparente para la cota de error estimada (2 sigma)
        ax.axhspan(
            cen - 2 * std,
            cen + 2 * std,
            alpha=0.1,
            color=color,
            label=rf"$2\sigma$ ref = {std:.3f}",
        )
        ax.legend()
    if n == 2:
        # caja central de calibración de ronda
        delta_mag = -2.5 * log10(roles_dict[Role.REF][0] / roles_dict[Role.TEST][0])
        zp = zp_abs + delta_mag
        texto = rf"$ \Delta m = {delta_mag:.02f}$;  $ZP_{i} = \Delta m + ZP_{{abs}} = {zp:.02f}$"
        axes[0].annotate(
            texto,
            xy=(0.5, 0.5),
            xycoords="axes fraction",
            ha="center",
            va="center",
            bbox=dict(boxstyle="round", facecolor="lightblue", alpha=0.3),
        )
    plt.tight_layout()
    plt.show()


def histograms(
    session: datetime,
    roles: list[Role, ...],
    freqs: list[FreqSequence, ...],
    tstamps: list[FreqSequence, ...],
    names: list[str, ...],
    use_median: bool = False,
    title: str | None = None,
    subtitles: list[str, ...] | None = None,
    labels: list[str, ...] | None = None,
    decimals: list[int, ...] = None,
) -> None:
    """
    Histogram for the ref and test photometer frequencies.
    One row, two couluns
    """
    # Crear figura con 1 fila, n columnas para uno/dos histogramas
    n = len(roles)
    fig, axes = plt.subplots(1, n, figsize=(12, 5))
    if n == 2:
        title = title or f"Histograms of {names[0]} & {names[1]} on {session}"
    else:
        title = title or f"Histograms of {names[0]} on {session}"
        axes = [axes]
    fig.suptitle(title)
    central = "median" if use_median else "mean"
    subtitles = subtitles or [None] * n
    labels = labels or [None] * n
    decimals = decimals or [3] * n
    distributions = list()
    allstats = list()
    for i in range(n):
        distributions.append(Counter([round(f, decimals[i]) for f in freqs[i]]))
        allstats.append(stats(freqs[i], use_median=use_median))

    for i, (ax, distr, name, label, subtitle, mystats, decim) in enumerate(
        zip(axes, distributions, names, labels, subtitles, allstats, decimals)
    ):
        x = list(distr.keys())  # Clave del Counter
        y = list(distr.values())  # Cuenta del Counter
        total = sum(y)
        width = 10 ** (-decim)
        cen, stddev, modes = mystats[0], mystats[1], mystats[2]
        ax.axvline(cen, color="red", linestyle="--", label=f"{central} = {cen:.3f}")
        for i, mode in enumerate(modes, start=1):
            ax.axvline(mode, color="red", linestyle=":", label=f"mode {i}= {mode:.3f}")
        ax.axvspan(
            cen - 2 * stddev,
            cen + 2 * stddev,
            alpha=0.1,
            color="blue",
            label=rf"$2\sigma$ = {stddev:.3f}",
        )
        ax.bar(x, y, width=width, alpha=0.8)
        ax.set_title(name)
        if label is not None:
            ax.set_xlabel(label)
        ax.set_ylabel(f"Counts ({total} Total)")
        ax.legend()
        ax.xaxis.set_major_formatter(FormatStrFormatter(f"% .{decim}f"))
        ax.set_xticks(x)
        ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
