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

from ..constants import ZP_ABS


def stats(series: list[float, ...], use_median: bool = False) -> tuple[float, float, list[float,...]]:
    """Compute mean(/median and std dev around central tendency"""
    central = statistics.median_low(series) if use_median else statistics.fmean(series)
    std_dev = statistics.stdev(series, xbar=central)
    modes = statistics.multimode(series)
    return central, std_dev, modes


def samples(
    session: datetime,
    ref_freqs: list[float, ...],
    ref_tstamps: list[datetime, ...],
    test_freqs: list[float, ...],
    test_tstamps: list[datetime, ...],
    ref_name: str,
    test_name: str,
    use_median: bool = False,
    zp_abs: float = ZP_ABS,
) -> None:
    """Grafica Frecuencia vs Tiempo en N rondas"""
    session_id = session.strftime("%Y-%m-%dT%H:%M:%S")
    fig, axes = plt.subplots(1, figsize=(15, 5))
    central = "median" if use_median else "mean"
    axes = [axes]
    for i, ax in zip(range(1, len(axes)+1), axes):
        ref_cen, ref_std, _ = stats(ref_freqs, use_median=use_median)
        tst_cen, tst_std, _ = stats(test_freqs, use_median=use_median)
        delta_mag = -2.5 * log10(ref_cen / tst_cen)
        zp = zp_abs + delta_mag
        ax.set_title(f"Session {session_id}")
        ax.set_ylabel("Frecuency (Hz)")
        # Medidas
        ax.plot(ref_tstamps, ref_freqs, color="tab:red", marker=".", linestyle="none", label=f"{ref_name}")
        ax.plot(
            test_tstamps, test_freqs, color="tab:blue", marker=".", linestyle="none", label=f"{test_name}"
        )
        # Tendencias centrales
        ax.axhline(y=ref_cen, linestyle=":", color="tab:red", label=f"{central} = {ref_cen:.3f}")
        ax.axhline(y=tst_cen, linestyle=":", color="tab:blue", label=f"{central} = {tst_cen:.3f}")
        # Barra horizontal semitransparente para la cota de error estimada (2 sigma)
        ax.axhspan(
            ref_cen - 2 * ref_std,
            ref_cen + 2 * ref_std,
            alpha=0.1,
            color="red",
            label=rf"$2\sigma$ ref = {ref_std:.3f}",
        )
        ax.axhspan(
            tst_cen - 2 * tst_std,
            tst_cen + 2 * tst_std,
            alpha=0.1,
            color="blue",
            label=rf"$2\sigma$ test = {tst_std:.3f}",
        )
        # caja central de calibración de ronda
        texto = rf"$ \Delta m = {delta_mag:.02f}$;  $ZP_{i} = \Delta m + ZP_{{abs}} = {zp:.02f}$"
        ax.annotate(
            texto,
            xy=(0.5, 0.5),
            xycoords="axes fraction",
            ha="center",
            va="center",
            bbox=dict(boxstyle="round", facecolor="lightblue", alpha=0.3),
        )
        ax.legend()
    plt.tight_layout()
    plt.show()


def histograms(
    session: datetime,
    ref_freqs: list[float, ...],
    ref_tstamps: list[datetime, ...],
    test_freqs: list[float, ...],
    test_tstamps: list[datetime, ...],
    ref_name: str,
    test_name: str,
    use_median: bool = False,
    title: str | None = None,
    subtitles: tuple[str, str] | None = None,
    labels: tuple[str, str] | None = None,
    decimals: tuple[int, int] = (3, 2),
) -> None:
    """
    Histogram for the ref and test photometer frequencies.
    One row, two couluns
    """
    # Crear figura con 1 fila, 2 columnas para dos histogramas
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    title = title or f"Histograms of {ref_name} & {test_name} on {session}"
    fig.suptitle(title)
    central = "median" if use_median else "mean"
    names = [ref_name, test_name]
    subtitles = subtitles or [None, None]
    labels = labels or [None, None]
    ref_histo = Counter([round(f, decimals[0]) for f in ref_freqs])
    test_histo = Counter([round(f, decimals[1]) for f in test_freqs])
    ref_stats = stats(ref_freqs, use_median=use_median)
    test_stats = stats(test_freqs, use_median=use_median)
    distributions = [ref_histo, test_histo]
    allstats = [ref_stats, test_stats]
    for i, (ax, distr, name, label, subtitle, mystats, decim) in enumerate(
        zip(axes, distributions, names, labels, subtitles, allstats, decimals)
    ):
        x = list(distr.keys())  # Clave del Counter
        y = list(distr.values())  # Cuenta del Counter
        total = sum(y)
        width = 10 ** (-decim)
        cen, stddev, modes = mystats[0], mystats[1], mystats[2]
        ax.axvline(cen, color="red", linestyle="--", label=f"{central} = {cen:.3f}")
        for mode in modes:
            ax.axvline(mode, color="red", linestyle=":", label=f"mode = {mode:.3f}")
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
