import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
from datetime import datetime
from math import log10
import statistics
from collections import Counter


ZP_ABS = 20.44


def stats(series: list[float, ...], use_median: bool = True) -> tuple[float, float]:
    """Compute mean(/median and std dev around central tendency"""
    central = statistics.median_low(series) if use_median else statistics.fmean(series)
    std_dev = statistics.stdev(series, xbar=central)
    modes = statistics.multimode(series)
    return central, std_dev, modes


def plot_samples(
    session: datetime,
    ref_freqs: list[float, ...],
    ref_tstamps: list[datetime, ...],
    test_freqs: list[float, ...],
    test_tstamps: list[datetime, ...],
    zp_abs: float = ZP_ABS,
) -> None:
    """Grafica Frecuencia vs Tiempo en N rondas"""
    session_id = session.strftime("%Y-%m-%dT%H:%M:%S")
    fig, axes = plt.subplots(1, figsize=(15, 5))
    axes = [axes]
    for i, ax in zip(range(1, len(axes)+1), axes):
        ref_med, ref_std, _ = stats(ref_freqs)
        tst_med, tst_std, _ = stats(test_freqs)
        delta_mag = -2.5 * log10(ref_med / tst_med)
        zp = zp_abs + delta_mag
        ax.set_title(f"Session {session_id}")
        ax.set_ylabel("Frecuency (Hz)")
        # Medidas
        ax.plot(ref_tstamps, ref_freqs, color="tab:red", marker=".", linestyle="none", label="ref")
        ax.plot(
            test_tstamps, test_freqs, color="tab:blue", marker=".", linestyle="none", label="test"
        )
        # Tendencias centrales
        ax.axhline(y=ref_med, linestyle=":", color="tab:red", label=f"Median = {ref_med:.3f}")
        ax.axhline(y=tst_med, linestyle=":", color="tab:blue", label=f"Median = {tst_med:.3f}")
        # Barra horizontal semitransparente para la cota de error estimada (2 sigma)
        ax.axhspan(
            ref_med - 2 * ref_std,
            ref_med + 2 * ref_std,
            alpha=0.1,
            color="red",
            label=rf"$2\sigma$ ref = {ref_std:.3f}",
        )
        ax.axhspan(
            tst_med - 2 * tst_std,
            tst_med + 2 * tst_std,
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


def plot_histograms(
    distributions: list[Counter],
    title=str,
    labels: tuple[str, str] | None = None,
    subtitles: tuple[str, str] | None = None,
    centrals: tuple[str, str] | None = None,
    decimals: tuple[int, int] = (2, 2),
) -> None:
    """
    Histogram for the ref and test photometer frequencies.
    One row, two couluns
    """
    # Crear figura con 1 fila, 2 columnas para dos histogramas
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(title)
    subtitles = subtitles or [None, None]
    centrals = centrals or [None, None]
    for i, (ax, distr, label, subtitle, central, decim) in enumerate(
        zip(axes, distributions, labels, subtitles, centrals, decimals)
    ):
        x = list(distr.keys())  # Clave del Counter
        y = list(distr.values())  # Cuenta del Counter
        total = y.sum()
        width = 10 ** (-decim)
        ax.bar(x, y, width=width, alpha=0.8)
        if central is not None:
            mean, median, modes = central[0], central[1], central[2]
            ax.axvline(mean, color="red", linestyle="--", label=f"Mean = {mean:.3f}")
            ax.axvline(median, color="red", linestyle=":", label=f"Median = {median:.3f}")
            for mode in modes:
                ax.axvline(mean, color="red", linestyle="-.", label=f"Local Max. = {mode:.3f}")
        if subtitle is not None:
            ax.set_title(subtitle)
        ax.set_xlabel(label)
        ax.set_ylabel(f"Counts ({total} Total)")
        ax.legend()
        ax.xaxis.set_major_formatter(FormatStrFormatter(f"% .{decim}f"))
        ax.set_xticks(x)
        ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
