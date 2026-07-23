from __future__ import annotations

from pathlib import Path
from typing import Final, Literal

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.ticker import ScalarFormatter
from rdetoolkit.errors import catch_exception_with_message
from rdetoolkit.exceptions import StructuredError
from rdetoolkit.models.rde2types import RdeOutputResourcePath, RepeatedMetaType

from modules_saxs.interfaces import IGraphPlotter
from modules_saxs.models import ScaleType
from modules_tool.csv2graph import FIG_SIZE, configure_plot_params, plot_all_graphs, plot_html, plot_individual_graphs


class GraphPlotter(IGraphPlotter[pd.DataFrame]):
    """Utility for plotting data using various types of plots.

    This class provides methods to generate and save different types of plots based on provided data.
    It supports line plots, log-scale plots, and multi-plots where multiple series are plotted on the same graph.

    """

    TWOTHETA_Q_DATA_REF_CORRECTED = 5
    source_lambda = 0.154  # [nm]

    def __init__(
        self,
        main_image_scaletype: Literal[ScaleType.linear, ScaleType.log],
        other_image_scaletype: Literal[ScaleType.linear, ScaleType.log],
        config: dict,
    ):
        """Init.

        Args:
            main_image_scaletype (ScaleType): main image scale type (Linear scale, Logarithmic scale).
            other_image_scaletype (ScaleType): other image scale type (Linear scale, Logarithmic scale).
            config (dict): Configuration dictionary.

        """
        self.title = ""
        self.multi_df: pd.DataFrame = []
        self.main_image_scaletype = main_image_scaletype
        self.other_image_scaletype = other_image_scaletype
        self.config: dict = config

    @catch_exception_with_message(error_message="Error: Could not draw graph")
    def plot_main(
        self,
        data: pd.DataFrame,
        resource_paths: RdeOutputResourcePath,
        region_num: int,
        repeat_meta: RepeatedMetaType,
        fitting_data: pd.DataFrame | None,  # for SAXS fitting
    ) -> None:
        """Plot main.

        Depending on the type of scale and number of regions,
        the graph title, scale, and destination are processed.

        Args:
            data (pd.DataFrame): measurement data.
            resource_paths (RdeOutputResourcePath): Paths to output resources for saving results.
            region_num (int): Number of regions
            repeat_meta (RepeatedMetaType): Repeat meta.
            fitting_data (pd.DataFrame): Fitting data for SAXS fitting.

        """
        single_region_num: Final[int] = 1
        multi_region_num: Final[int] = 2
        image_basename: str = resource_paths.rawfiles[0].stem
        mode = self.config["saxs"]["mode"]
        multi_data = fitting_data if mode == "saxs_fitting" else data
        self._set_multi_dataset(multi_data)

        if len(resource_paths.rawfiles) == 1 or \
                len(str(resource_paths.rawfiles[0])) < len(str(resource_paths.rawfiles[1])):
            image_basename = resource_paths.rawfiles[0].stem
        elif len(str(resource_paths.rawfiles[0])) > len(str(resource_paths.rawfiles[1])):
            image_basename = resource_paths.rawfiles[1].stem

        if mode == "saxs":
            if region_num == single_region_num:
                self._plot_single_region(data, resource_paths, image_basename, repeat_meta)
            elif region_num == multi_region_num:
                self._plot_multiple_regions(data, resource_paths, image_basename, repeat_meta)
        elif mode == "saxs_fitting":
            if region_num == single_region_num:
                self._plot_single_region_fitting(data, resource_paths, image_basename, repeat_meta, fitting_data)
            elif region_num == multi_region_num:
                self._plot_multiple_regions_fitting(data, resource_paths, image_basename, repeat_meta)

    @catch_exception_with_message(error_message="Error: Could not draw graph")
    def multiplot_main(
        self,
        resource_paths: RdeOutputResourcePath,
        repeat_meta: RepeatedMetaType,
    ) -> None:
        """Multiplot main.

        If there are two regions, the two graphs are displayed together.

        Args:
            resource_paths (RdeOutputResourcePath): Paths to output resources for saving results.
            repeat_meta (RepeatedMetaType): Repeat meta.

        """
        image_basename = resource_paths.rawfiles[0].stem
        save_path = resource_paths.main_image.joinpath(f"{image_basename}.png")
        title = self.set_title_from_filename(save_path)
        mode = self.config["saxs"]["mode"]
        if mode == "saxs":
            raw_name = repeat_meta['HW_XG_TARGET_NAME']
            target_name: str = str(raw_name[0]) if raw_name else 'Unknown'
            conversion_formula: str = "Q=(4π/λ) * sinθ"
            legend_info = f"Target: {target_name}\n{conversion_formula}"
            self.multiplot(save_path, title=title, legend_info=legend_info, scale=self.main_image_scaletype)
        elif mode == "saxs_fitting":
            self.multiplot_fitting(resource_paths, title=title, scale=self.main_image_scaletype)

    @catch_exception_with_message(error_message="Error: Could not draw graph")
    def multiplot(
        self,
        save_path: Path,
        *,
        data_series_1: pd.DataFrame | None = None,
        data_series_2: pd.DataFrame | None = None,
        title: str | None = None,
        legend_info: str | None = None,
        xlabel: str | None = None,
        ylabel: str | None = None,
        scale: ScaleType = ScaleType.linear,
    ) -> None:
        """Plot two series of data on the same graph.

        Args:
            save_path (Path): Path where the plot will be saved.
            data_series_1 (pd.DataFrame): First set of data to be plotted.
            data_series_2 (pd.DataFrame): Second set of data to be plotted.
            title (str | None): Title of the graph. Defaults to an empty string.
            legend_info (str | None): legend info of the graph. Defaults to an empty string.
            xlabel (str | None): Label for the x-axis. Defaults to an empty string.
            ylabel (str | None): Label for the y-axis. Defaults to the column name of the first data series.
            scale (ScaleType): Information about the graph scale.

        """
        title, data_series_1, data_series_2 = self._set_data_title(title, data_series_1, data_series_2)

        if data_series_1 is None or data_series_2 is None:
            err_msg = "Error: No input data to multi graphing."
            raise StructuredError(err_msg)

        col_series_1 = data_series_1.columns
        col_series_2 = data_series_2.columns
        xlabel = xlabel or col_series_1[1]
        ylabel = ylabel or col_series_1[2][5:]

        fig, ax = plt.subplots(figsize=FIG_SIZE)

        ax.set_ylabel(ylabel)
        if scale == ScaleType.linear:
            ax.yaxis.set_major_formatter(ScalarFormatter(useMathText=True))
        else:
            ax.set_yscale("log")
        ax.set_title(title)

        # legend infomation
        if legend_info:
            legend_info_formatted = legend_info.replace('\\n', '\n')
            ax.text(0.98, 0.98, legend_info_formatted, transform=ax.transAxes,
                    fontsize=max(8, 20 - 2), verticalalignment='top', horizontalalignment='right',
                    linespacing=1.2)

        data_series_1.plot(ax=ax, x=col_series_1[1], y=col_series_1[-1], legend=False)
        data_series_2.plot(ax=ax, x=col_series_2[1], y=col_series_2[-1], legend=False)

        fig.savefig(save_path)

    @catch_exception_with_message(error_message="Error: Could not draw graph")
    def multiplot_fitting(
        self,
        resource_paths: RdeOutputResourcePath,
        *,
        data_series_1: pd.DataFrame | None = None,
        data_series_2: pd.DataFrame | None = None,
        title: str | None = None,
        scale: ScaleType = ScaleType.linear,
    ) -> None:
        """Plot two series of data on the same graph.

        Args:
            resource_paths (RdeOutputResourcePath): Output path.
            data_series_1 (pd.DataFrame): First set of data to be plotted.
            data_series_2 (pd.DataFrame): Second set of data to be plotted.
            title (str | None): Title of the graph. Defaults to an empty string.
            scale (ScaleType): Information about the graph scale.

        """
        title, data_series_1, data_series_2 = self._set_data_title(title, data_series_1, data_series_2)

        if data_series_1 is None or data_series_2 is None:
            err_msg = "Error: No input data to multi graphing."
            raise StructuredError(err_msg)

        self._plot_fitting_init()

        plt.figure(figsize=(6, 6))
        plt.gca().yaxis.set_major_formatter(ScalarFormatter(useMathText=True))
        plt.gca().ticklabel_format(style="sci", axis="y", scilimits=(0, 0))
        plt.scatter(data_series_1.iloc[:, 0], data_series_1.iloc[:, 1], color='gray', edgecolor='k', s=100)
        plt.scatter(data_series_2.iloc[:, 0], data_series_2.iloc[:, 1], color='gray', edgecolor='k', s=100)
        plt.plot(data_series_1.iloc[:, 0], data_series_1.iloc[:, 2], color='red', lw=3)
        plt.plot(data_series_2.iloc[:, 0], data_series_2.iloc[:, 2], color='red', lw=3)
        plt.title(f"{title}")
        plt.xlabel(r'Scattering vector $q$ [nm$^{-1}$]')
        plt.ylabel('Intensity [counts]')
        plt.yscale('log')
        plt.tight_layout()
        plt.savefig(
            resource_paths.main_image.joinpath(f"{title}.png"),
            dpi=300,
            bbox_inches='tight',
            pad_inches=0.1,
        )
        plt.close('all')

        plot_html(
            data_series_1,
            name=f"{title}",
            xaxis_label='Scattering vector q [nm<sup>-1</sup>]',
            yaxis_label='Intensity [counts]',
            legends=["Experimental", "Fitted"],
            logy=self.main_image_scaletype == ScaleType.log,
            output_dir=str(resource_paths.struct),
            x_col=[0, 0],
            y_cols=[1, 2],
        )

    @catch_exception_with_message(error_message="Type error: illegal type detected")
    def set_title_from_filename(self, filepath: str | Path) -> str:
        """Set the title name of the graph from the filename.

        Args:
            filepath (str | Path): Filename.

        Returns:
            str: Title name of the graph.

        """
        if isinstance(filepath, str):
            filepath = Path(filepath)
        return filepath.stem

    def _set_data_title(
        self,
        title: str | None = None,
        data_series_1: pd.DataFrame | None = None,
        data_series_2: pd.DataFrame | None = None,
    ) -> tuple[str, pd.DataFrame | None, pd.DataFrame | None]:
        """Set the title and multi region data.

        Args:
            title (str | None): Title of the graph. Defaults to an empty string.
            data_series_1 (pd.DataFrame): First set of data to be plotted.
            data_series_2 (pd.DataFrame): Second set of data to be plotted.

        Returns:
            title (str): Title of the graph. Defaults to an empty string.
            data_series_1 (pd.DataFrame): First set of data to be plotted.
            data_series_2 (pd.DataFrame): Second set of data to be plotted.

        """
        if title is None:
            title = self.title if self.title else ""

        if data_series_1 is None and len(self.multi_df) > 1:
            data_series_1 = self.multi_df[0]
        if data_series_2 is None and len(self.multi_df) > 1:
            data_series_2 = self.multi_df[1]

        return title, data_series_1, data_series_2

    def _set_multi_dataset(self, data: pd.DataFrame) -> None:
        """Methods to store datasets to be graphed into instance variables.

        Args:
            data (pd.DataFrame): data to be graphed

        """
        self.multi_df.append(data)

    def _plot_single_region(
            self,
            data: pd.DataFrame,
            resource_paths: RdeOutputResourcePath,
            image_basename: str,
            repeat_meta: RepeatedMetaType,
    ) -> None:
        """Plot for a single region."""
        target_name: str = 'Unknown'
        if repeat_meta['HW_XG_TARGET_NAME']:
            target_name = str(repeat_meta['HW_XG_TARGET_NAME'][0])
        elif repeat_meta['rasx.x-ray_target_material']:
            target_name = str(repeat_meta['rasx.x-ray_target_material'][0])
        conversion_formula: str = "Q=(4π/λ) * sinθ"

        configure_plot_params()

        # Plot main_image
        plot_individual_graphs(
            data,
            name=image_basename,
            xaxis_label=data.columns[1],
            yaxis_label=data.columns[2][5:],  # dalete 'data: '
            legends=[""],
            logy=self.main_image_scaletype == ScaleType.log,
            output_dir=str(resource_paths.main_image),
            x_col=1,
            y_cols=[data.shape[1] - 1],  # Corrected:
            legend_info=f"Target: {target_name}\n{conversion_formula}",
        )

        # Plot other_image
        if data.shape[1] == self.TWOTHETA_Q_DATA_REF_CORRECTED:  # Read reference data if it exists
            plot_all_graphs(
                data,
                name=image_basename + "_raw_ref",
                xaxis_label=data.columns[1],
                yaxis_label=data.columns[2][5:],  # dalete 'data: '
                legends=["data", "ref"],
                logy=self.main_image_scaletype == ScaleType.log,
                output_dir=str(resource_paths.other_image),
                x_col=[1, 1],
                y_cols=[2, 3],  # data:, ref:
                title=image_basename,
            )

        # Plot html
        legends = ["data", "ref", "Corrected"] if data.shape[1] == self.TWOTHETA_Q_DATA_REF_CORRECTED else ["data"]
        x_col: int | list[int] = [1, 1, 1] if data.shape[1] == self.TWOTHETA_Q_DATA_REF_CORRECTED else 1
        # data:, ref:, Corrected:
        y_cols = [2, 3, 4] if data.shape[1] == self.TWOTHETA_Q_DATA_REF_CORRECTED else [data.shape[1] - 1]
        plot_html(
            data,
            name=image_basename,
            xaxis_label=data.columns[1],
            yaxis_label=data.columns[2][5:],  # dalete 'data: '
            legends=legends,
            logy=self.main_image_scaletype == ScaleType.log,
            output_dir=str(resource_paths.struct),
            x_col=x_col,
            y_cols=y_cols,
            legend_info=f"Target: {target_name}<br>{conversion_formula}",
        )

    def _plot_multiple_regions(
            self,
            data: pd.DataFrame,
            resource_paths: RdeOutputResourcePath,
            image_basename: str,
            repeat_meta: RepeatedMetaType,
    ) -> None:
        """Plot for multiple regions."""
        filepath = resource_paths.other_image.joinpath(f"{image_basename}.png") \
            if data.shape[1] == self.TWOTHETA_Q_DATA_REF_CORRECTED \
            else resource_paths.struct.joinpath(f"{image_basename}.html")
        idx = 1
        while True:
            new_filename = f"{filepath.stem}_{idx}_raw_ref{filepath.suffix}" \
                if data.shape[1] == self.TWOTHETA_Q_DATA_REF_CORRECTED \
                else f"{filepath.stem}_{idx}{filepath.suffix}"
            new_filepath = filepath.parent / new_filename
            if not new_filepath.exists():
                break
            idx += 1
        if isinstance(new_filepath, str):
            new_filepath = Path(new_filepath)
        title = new_filepath.stem

        target_name: str = 'Unknown'
        if repeat_meta['HW_XG_TARGET_NAME']:
            target_name = str(repeat_meta['HW_XG_TARGET_NAME'][0])
        elif repeat_meta['rasx.x-ray_target_material']:
            target_name = str(repeat_meta['rasx.x-ray_target_material'][0])
        conversion_formula: str = "Q=(4π/λ) * sinθ"

        configure_plot_params()  # MEMO: Without this, the layout breaks.

        # Plot other_image
        if data.shape[1] == self.TWOTHETA_Q_DATA_REF_CORRECTED:  # Read reference data if it exists
            plot_all_graphs(
                data,
                name=title,
                xaxis_label=data.columns[1],
                yaxis_label=data.columns[2][5:],  # dalete 'data: '
                legends=["data", "ref"],
                logy=self.main_image_scaletype == ScaleType.log,
                output_dir=str(resource_paths.other_image),
                x_col=[1, 1],
                y_cols=[2, 3],  # data:, ref:
                title=title,
            )

        # Plot html
        legends = ["data", "ref", "Corrected"] if data.shape[1] == self.TWOTHETA_Q_DATA_REF_CORRECTED else ["data"]
        x_col: int | list[int] = [1, 1, 1] if data.shape[1] == self.TWOTHETA_Q_DATA_REF_CORRECTED else 1
        # data:, ref:, Corrected:
        y_cols = [2, 3, 4] if data.shape[1] == self.TWOTHETA_Q_DATA_REF_CORRECTED else [data.shape[1] - 1]
        plot_html(
            data,
            name=title,
            xaxis_label=data.columns[1],
            yaxis_label=data.columns[2][5:],  # dalete 'data: '
            legends=legends,
            logy=self.main_image_scaletype == ScaleType.log,
            output_dir=str(resource_paths.struct),
            x_col=x_col,
            y_cols=y_cols,
            legend_info=f"Target: {target_name}<br>{conversion_formula}",
        )

    def _plot_single_region_fitting(
        self,
        data: pd.DataFrame,
        resource_paths: RdeOutputResourcePath,
        image_basename: str,
        repeat_meta: RepeatedMetaType,
        fitting_data: pd.DataFrame,
    ) -> None:
        """Plot for a single region.

        Args:
            data (pd.DataFrame): raw data.
            resource_paths (RdeOutputResourcePath): output path.
            image_basename (str): image basename.
            repeat_meta (RepeatedMetaType): repeat meta
            fitting_data (pd.DataFrame): fitting data

        """
        self._plot_fitting_main_image(fitting_data, resource_paths, image_basename)
        self._plot_fitting_other_image(data, resource_paths, image_basename, None)

    def _plot_multiple_regions_fitting(
        self,
        data: pd.DataFrame,
        resource_paths: RdeOutputResourcePath,
        image_basename: str,
        repeat_meta: RepeatedMetaType,
    ) -> None:
        """Plot for multiple regions.

        Args:
            data (pd.DataFrame): raw data.
            resource_paths (RdeOutputResourcePath): output path.
            image_basename (str): image basename.
            repeat_meta (RepeatedMetaType): repeat meta.

        """
        filepath = resource_paths.other_image.joinpath(f"{image_basename}.png") \
            if data.shape[1] == self.TWOTHETA_Q_DATA_REF_CORRECTED \
            else resource_paths.struct.joinpath(f"{image_basename}_raw.html")
        idx = 1
        while True:
            new_filename = f"{filepath.stem}_{idx}_raw_ref{filepath.suffix}" \
                if data.shape[1] == self.TWOTHETA_Q_DATA_REF_CORRECTED \
                else f"{filepath.stem}_{idx}{filepath.suffix}"
            new_filepath = filepath.parent / new_filename
            if not new_filepath.exists():
                break
            idx += 1

        self._plot_fitting_other_image(data, resource_paths, image_basename, idx)

    def _plot_fitting_init(self) -> None:
        """Set plot parameters."""
        plt.rcdefaults()
        plt.rcParams['font.size'] = 18
        plt.rcParams['xtick.direction'] = 'in'
        plt.rcParams['ytick.direction'] = 'in'
        plt.rcParams['xtick.major.width'] = 1.5
        plt.rcParams['ytick.major.width'] = 1.5
        plt.rcParams['axes.linewidth'] = 1.2
        plt.rcParams['axes.grid'] = False
        plt.rcParams['grid.linestyle'] = '--'
        plt.rcParams['grid.linewidth'] = 1.0

    def _plot_fitting_main_image(
        self,
        data: pd.DataFrame,
        resource_paths: RdeOutputResourcePath,
        image_basename: str,
    ) -> None:
        """Plot for fitting main image.

        Args:
            data (pd.DataFrame): fitting data.
            resource_paths (RdeOutputResourcePath): output path.
            image_basename (str): image basename.

        """
        self._plot_fitting_init()

        plt.figure(figsize=(6, 6))
        plt.gca().yaxis.set_major_formatter(ScalarFormatter(useMathText=True))
        plt.gca().ticklabel_format(style="sci", axis="y", scilimits=(0, 0))
        plt.scatter(data.iloc[:, 0], data.iloc[:, 1], color='gray', edgecolor='k', s=100)
        plt.plot(data.iloc[:, 0], data.iloc[:, 2], color='red', lw=3)
        plt.title(f"{image_basename}_fitting")
        plt.xlabel(r'Scattering vector $q$ [nm$^{-1}$]')
        plt.ylabel('Intensity [counts]')
        if self.main_image_scaletype == ScaleType.log:
            plt.yscale("log")
        else:
            plt.yscale("linear")
        plt.tight_layout()
        plt.savefig(
            resource_paths.main_image.joinpath(f"{image_basename}_fitting.png"),
            dpi=300,
            bbox_inches='tight',
            pad_inches=0.1,
        )
        plt.close('all')

        plot_html(
            data,
            name=f"{image_basename}_fitting",
            xaxis_label='Scattering vector q [nm<sup>-1</sup>]',
            yaxis_label='Intensity [counts]',
            legends=["Experimental", "Fitted"],
            logy=self.main_image_scaletype == ScaleType.log,
            output_dir=str(resource_paths.struct),
            x_col=[0, 0],
            y_cols=[1, 2],
        )

    def _plot_fitting_other_image(
        self,
        data: pd.DataFrame,
        resource_paths: RdeOutputResourcePath,
        image_basename: str,
        idx: int | None,
    ) -> None:
        """Plot for fitting other image.

        Args:
            data (pd.DataFrame): fitting data.
            resource_paths (RdeOutputResourcePath): output path.
            image_basename (str): image basename.
            idx (int): 0-9 (seek).

        """
        data_float = data.to_numpy().astype(float)
        data_q = pd.DataFrame(4 * np.pi * np.sin(np.deg2rad(data_float[:, 0] / 2.0)) / self.source_lambda)
        region_num: str = "_" + str(idx) if idx is not None else ""

        self._plot_fitting_init()

        plt.figure(figsize=(6, 6))
        plt.gca().yaxis.set_major_formatter(ScalarFormatter(useMathText=True))
        plt.gca().ticklabel_format(style="sci", axis="y", scilimits=(0, 0))
        plt.plot(data_q.iloc[:, 0], data.iloc[:, 2])
        plt.title(f"{image_basename}_raw{region_num}")
        plt.xlabel(r'2theta (deg)')
        plt.ylabel('Intensity [counts]')
        if self.main_image_scaletype == ScaleType.log:
            plt.yscale("log")
        else:
            plt.yscale("linear")
        plt.tight_layout()
        plt.savefig(
            resource_paths.other_image.joinpath(f"{image_basename}{region_num}.png"),
            dpi=300,
            bbox_inches='tight',
            pad_inches=0.1,
        )
        plt.close('all')

        plot_html(
            data,
            name=f"{image_basename}_raw{region_num}",
            xaxis_label=r'2theta (deg)',
            yaxis_label='Intensity [counts]',
            legends=["raw"],
            logy=self.main_image_scaletype == ScaleType.log,
            output_dir=str(resource_paths.struct),
            x_col=[0],
            y_cols=[2],
        )
