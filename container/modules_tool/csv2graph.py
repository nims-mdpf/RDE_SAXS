from __future__ import annotations

import os
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objs as go
from matplotlib.legend import Legend
from plotly.offline import plot as plotly_plot

PLOT_PARAMS = {
    "font.size": 20,
    "xtick.labelsize": 20,
    "ytick.labelsize": 20,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "axes.xmargin": 0,
}
FIG_SIZE = (8.85, 8)

LEGEND_CENTER_THRESHOLD = 0.5
LEGEND_RIGHT_THRESHOLD = 0.7
LEGEND_BOTTOM_OFFSET = 0.05
LEGEND_TOP_OFFSET = 0.98
LEGEND_BOTTOM_THRESHOLD = 0.9


def sanitize_filename(name: str) -> str:
    """Sanitize a filename by replacing invalid characters with underscores."""
    return re.sub(r'[\\/*?:"<>|]', "_", name)


def configure_plot_params() -> None:
    """Configure Matplotlib plot parameters."""
    for key, value in PLOT_PARAMS.items():
        plt.rcParams[key] = value


def plot_all_graphs(
    df: pd.DataFrame,
    name: str,
    xaxis_label: str,
    yaxis_label: str,
    legends: list[str],
    logy: bool,
    dual_scale: bool = False,
    output_dir: str | None = None,
    main_image_dir: str | None = None,
    x_col: int | list[int] = 0,
    y_cols: list[int] | None = None,
    logx: bool = False,
    html: bool = False,
    direction_cols: list[int] | None = None,
    direction_filter: str | None = None,
    legend_info: str | None = None,
    title: str | None = None,
    xlim: list[float] | None = None,
    ylim: list[float] | None = None,
    grid: bool = False,
    invert_x: bool = False,
    invert_y: bool = False,
    return_fig: bool = False,
    max_legend_items: int | None = None,
) -> plt.Figure | None:
    """Plot all data on one graph.

    Args:
        df: DataFrame containing plotting data.
        name: Base name for output files.
        xaxis_label: X-axis label.
        yaxis_label: Y-axis label.
        legends: Legend labels.
        logy: Use logarithmic Y-axis.
        dual_scale: Output both linear and log scale graphs.
        output_dir: Output directory.
        main_image_dir: Directory for main image output.
        x_col: X-axis column index or indexes.
        y_cols: Y-axis column indexes.
        logx: Use logarithmic X-axis.
        html: Output interactive HTML plot.
        direction_cols: Direction column indexes.
        direction_filter: Filter for direction values.
        legend_info: Additional legend information text.
        title: Plot title.
        xlim: X-axis limits.
        ylim: Y-axis limits.
        grid: Enable grid.
        invert_x: Invert X-axis.
        invert_y: Invert Y-axis.
        return_fig: Return matplotlib Figure.
        max_legend_items: Maximum legend items.

    """
    x_cols, y_cols = _prepare_plot_columns(
        df,
        x_col,
        y_cols,
    )

    image_dir = _get_main_image_dir(
        output_dir,
        main_image_dir,
    )

    fig, ax = plt.subplots(
        figsize=FIG_SIZE,
        tight_layout=True,
    )

    _configure_plot_axes(
        ax,
        logx,
        logy,
        xlim,
        ylim,
        invert_x,
        invert_y,
        grid,
    )

    if direction_cols is not None:
        _plot_direction_series(
            ax,
            df,
            x_cols,
            y_cols,
            legends,
            direction_cols,
            direction_filter,
        )
    else:
        _plot_normal_series(
            ax,
            df,
            x_cols,
            y_cols,
            legends,
        )

    ax.set_xlabel(xaxis_label)
    ax.set_ylabel(yaxis_label)
    ax.set_title(
        title if title is not None else os.path.basename(name),
        pad=20,
    )

    if legends:
        ax.legend()

    if legend_info:
        _draw_plot_legend_info(
            ax,
            legend_info,
        )

    image_path = os.path.join(
        image_dir,
        f"{name}.png",
    )

    if return_fig:
        return fig

    fig.savefig(image_path)
    plt.close(fig)

    if html:
        plot_html(
            df,
            name=name,
            xaxis_label=xaxis_label,
            yaxis_label=yaxis_label,
            legends=legends,
            logy=logy,
            output_dir=output_dir,
            x_col=x_col,
            y_cols=y_cols,
            logx=logx,
            direction_cols=direction_cols,
            direction_filter=direction_filter,
            legend_info=legend_info,
            max_legend_items=max_legend_items,
        )

    return None


def _prepare_plot_columns(
    df: pd.DataFrame,
    x_col: int | list[int],
    y_cols: list[int] | None,
) -> tuple[list[int], list[int]]:
    x_cols = x_col if isinstance(x_col, list) else [x_col]

    if y_cols is None:
        y_cols = list(range(df.shape[1]))
        for x in x_cols:
            if x in y_cols:
                y_cols.remove(x)

    if len(x_cols) != len(y_cols):
        if len(x_cols) == 1:
            x_cols = x_cols * len(y_cols)
        else:
            msg = (
                f"x_cols ({len(x_cols)}) and y_cols ({len(y_cols)}) "
                "must have the same length"
            )
            raise ValueError(msg)

    return x_cols, y_cols


def _get_main_image_dir(
    output_dir: str | None,
    main_image_dir: str | None,
) -> str:
    if output_dir is None:
        return str(Path.cwd())

    if not os.path.exists(output_dir):
        msg = f"Output directory does not exist: {output_dir}"
        raise FileNotFoundError(msg)

    if not os.path.isdir(output_dir):
        msg = f"Output path is not a directory: {output_dir}"
        raise NotADirectoryError(msg)

    if main_image_dir is None:
        return output_dir

    if not os.path.exists(main_image_dir):
        msg = f"Main image directory does not exist: {main_image_dir}"
        raise FileNotFoundError(msg)

    if not os.path.isdir(main_image_dir):
        msg = f"Main image path is not a directory: {main_image_dir}"
        raise NotADirectoryError(msg)

    return main_image_dir


def _configure_plot_axes(
    ax: plt.Axes,
    logx: bool,
    logy: bool,
    xlim: list[float] | None,
    ylim: list[float] | None,
    invert_x: bool,
    invert_y: bool,
    grid: bool,
) -> None:
    if logx:
        ax.set_xscale("log")

    if logy:
        ax.set_yscale("log")

    if xlim is not None:
        ax.set_xlim(xlim[0], xlim[1])

    if ylim is not None:
        ax.set_ylim(ylim[0], ylim[1])

    if invert_x:
        ax.invert_xaxis()

    if invert_y:
        ax.invert_yaxis()

    if grid:
        ax.grid(True)


def _plot_normal_series(
    ax: plt.Axes,
    df: pd.DataFrame,
    x_cols: list[int],
    y_cols: list[int],
    legends: list[str],
) -> None:
    color_map = {}
    colors = plt.cm.tab10(range(10))
    color_idx = 0

    for i, legend in enumerate(legends):
        if legend not in color_map:
            color_map[legend] = colors[color_idx % len(colors)]
            color_idx += 1

        x = df.iloc[:, x_cols[i]].values
        y = df.iloc[:, y_cols[i]].values

        ax.plot(
            x,
            y,
            label=legend,
            color=color_map[legend],
        )


def _draw_plot_legend_info(
    ax: plt.Axes,
    legend_info: str,
) -> None:
    """Draw additional legend information on the plot."""
    legend_info_formatted = legend_info.replace("\\n", "\n")

    legend_obj = ax.get_legend()

    if legend_obj:
        plt.gcf().canvas.draw()

        legend_bbox = legend_obj.get_window_extent(
            renderer=plt.gcf().canvas.get_renderer(),
        )
        legend_bbox_axes = legend_bbox.transformed(
            ax.transAxes.inverted(),
        )

        legend_fontsize = (
            legend_obj.get_texts()[0].get_fontsize()
            if legend_obj.get_texts()
            else 10
        )

        legend_center_x = (
            legend_bbox_axes.x0 + legend_bbox_axes.x1
        ) / 2

        legend_center_y = (
            legend_bbox_axes.y0 + legend_bbox_axes.y1
        ) / 2

        is_right = (
            legend_center_x > LEGEND_CENTER_THRESHOLD
            or legend_bbox_axes.x1 > LEGEND_RIGHT_THRESHOLD
        )

        is_bottom = (
            legend_center_y < LEGEND_CENTER_THRESHOLD
        )

        if is_bottom:
            if legend_bbox_axes.y1 + LEGEND_BOTTOM_OFFSET < 1.0:
                text_y = (
                    legend_bbox_axes.y1
                    + (LEGEND_BOTTOM_OFFSET / 2)
                )
                valign = "bottom"
            else:
                text_y = LEGEND_TOP_OFFSET
                valign = "top"
        else:
            text_y = legend_bbox_axes.y0 - 0.05
            valign = "top"

        if is_right:
            text_x = legend_bbox_axes.x1
            halign = "right"
        else:
            text_x = legend_bbox_axes.x0
            halign = "left"

        if is_bottom and text_y > LEGEND_BOTTOM_THRESHOLD:
            text_x = LEGEND_TOP_OFFSET
            halign = "right"

        ax.text(
            text_x,
            text_y,
            legend_info_formatted,
            transform=ax.transAxes,
            fontsize=max(8, legend_fontsize - 2),
            verticalalignment=valign,
            horizontalalignment=halign,
            linespacing=1.2,
        )

    else:
        ax.text(
            0.98,
            0.98,
            legend_info_formatted,
            transform=ax.transAxes,
            fontsize=18,
            verticalalignment="top",
            horizontalalignment="right",
            linespacing=1.2,
        )


def _plot_direction_series(
    ax: plt.Axes,
    df: pd.DataFrame,
    x_cols: list[int],
    y_cols: list[int],
    legends: list[str],
    direction_cols: list[int],
    direction_filter: str | None,
) -> None:
    series_color_map = {}
    series_colors = plt.cm.tab10(range(10))
    color_idx = 0

    for i, legend in enumerate(legends):
        if legend not in series_color_map:
            series_color_map[legend] = (
                series_colors[color_idx % len(series_colors)]
            )
            color_idx += 1

        x = df.iloc[:, x_cols[i]].values
        y = df.iloc[:, y_cols[i]].values
        directions = df.iloc[:, direction_cols[i]].values

        unique_directions = sorted(
            {d for d in directions if pd.notna(d)},
        )

        if direction_filter is not None:
            unique_directions = [
                d for d in unique_directions
                if d == direction_filter
            ]

        for j, direction in enumerate(unique_directions):
            mask = directions == direction

            if len(x[mask]) > 0:
                ax.plot(
                    x[mask],
                    y[mask],
                    color=series_color_map[legend],
                    label=legend if j == 0 else "",
                    alpha=0.8,
                )


def plot_html(
    df: pd.DataFrame,
    name: str,
    xaxis_label: str,
    yaxis_label: str,
    legends: list[str],
    logy: bool,
    output_dir: str | None = None,
    x_col: int | list[int] = 0,
    y_cols: list[int] | None = None,
    logx: bool = False,
    direction_cols: list[int] | None = None,
    direction_filter: str | None = None,
    legend_info: str | None = None,
    max_legend_items: int | None = None,
) -> None:
    """Generate an interactive HTML plot using Plotly."""
    x_cols, y_cols = _prepare_xy_columns(
        df,
        x_col,
        y_cols,
    )

    traces = []
    color_map = {}
    colors = [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
    ]

    color_idx = 0

    for i, legend in enumerate(legends):
        if legend not in color_map:
            color_map[legend] = colors[color_idx % len(colors)]
            color_idx += 1

        x = df.iloc[:, x_cols[i]]
        y = df.iloc[:, y_cols[i]]

        has_direction = (
            direction_cols
            and i < len(direction_cols)
            and direction_cols[i] is not None
        )

        if has_direction:
            direction_data = df.iloc[:, direction_cols[i]]

            traces.extend(
                _create_direction_traces(
                    df=df,
                    x=x,
                    y=y,
                    legend=legend,
                    color=color_map[legend],
                    direction_data=direction_data,
                    direction_filter=direction_filter,
                ),
            )
        else:
            traces.append(
                go.Scatter(
                    x=x,
                    y=y,
                    mode="lines",
                    name=legend,
                    line={"color": color_map[legend]},
                    legendgroup=legend,
                ),
            )

    layout = go.Layout(
        title=name,
        xaxis={
            "title": xaxis_label,
            "type": "log" if logx else "linear",
        },
        yaxis={
            "title": yaxis_label,
            "type": "log" if logy else "linear",
        },
        showlegend=True,
        updatemenus=[
            {
                "buttons": [
                    {
                        "label": "X Linear",
                        "method": "relayout",
                        "args": [{"xaxis.type": "linear"}],
                    },
                    {
                        "label": "X Log",
                        "method": "relayout",
                        "args": [{"xaxis.type": "log"}],
                    },
                ],
                "direction": "down",
                "showactive": True,
                "active": 1 if logx else 0,
                "x": 1.15,
                "xanchor": "left",
                "y": 1.08,
                "yanchor": "top",
                "type": "dropdown",
            },
            {
                "buttons": [
                    {
                        "label": "Y Linear",
                        "method": "relayout",
                        "args": [{"yaxis.type": "linear"}],
                    },
                    {
                        "label": "Y Log",
                        "method": "relayout",
                        "args": [{"yaxis.type": "log"}],
                    },
                ],
                "direction": "down",
                "showactive": True,
                "active": 1 if logy else 0,
                "x": 1.15,
                "xanchor": "left",
                "y": 1.03,
                "yanchor": "top",
                "type": "dropdown",
            },
        ],
    )

    fig = go.Figure(
        data=traces,
        layout=layout,
    )

    _add_legend_annotation(
        fig,
        legend_info,
    )

    html_dir = _get_html_dir(output_dir)

    html_file = os.path.join(
        html_dir,
        f"{name}.html",
    )

    plotly_plot(
        fig,
        filename=html_file,
        auto_open=False,
    )


def _prepare_xy_columns(
    df: pd.DataFrame,
    x_col: int | list[int],
    y_cols: list[int] | None,
) -> tuple[list[int], list[int]]:
    """Prepare x and y column indexes."""
    x_cols = x_col if isinstance(x_col, list) else [x_col]

    if y_cols is None:
        y_cols = list(range(df.shape[1]))
        for x in x_cols:
            if x in y_cols:
                y_cols.remove(x)

    if len(x_cols) != len(y_cols):
        if len(x_cols) == 1:
            x_cols = x_cols * len(y_cols)
        else:
            msg = (
                f"x_cols ({len(x_cols)}) and y_cols ({len(y_cols)}) "
                "must have the same length"
            )
            raise ValueError(msg)

    return x_cols, y_cols


def _get_html_dir(output_dir: str | None) -> str:
    """Get HTML output directory."""
    if output_dir is not None:
        html_dir = os.path.join(output_dir, "../structured/")
        html_dir = os.path.normpath(html_dir)
        os.makedirs(html_dir, exist_ok=True)
        return html_dir

    return str(Path.cwd())


def _create_direction_traces(
    df: pd.DataFrame,
    x: pd.Series,
    y: pd.Series,
    legend: str,
    color: str,
    direction_data: pd.Series,
    direction_filter: str | None,
) -> list[go.Scatter]:
    """Create plotly traces grouped by direction."""
    traces = []
    first_direction = True

    for direction_value in direction_data.unique():
        if pd.isna(direction_value):
            continue

        if (
            direction_filter is not None
            and direction_value != direction_filter
        ):
            continue

        mask = direction_data == direction_value

        traces.append(
            go.Scatter(
                x=x[mask],
                y=y[mask],
                mode="lines",
                name=legend,
                line={"color": color},
                legendgroup=legend,
                showlegend=first_direction,
            ),
        )

        first_direction = False

    return traces


def _add_legend_annotation(
    fig: go.Figure,
    legend_info: str | None,
) -> None:
    """Add legend information annotation."""
    if legend_info is None:
        return

    legend_info_formatted = legend_info.replace("\\n", "<br>")

    fig.add_annotation(
        text=legend_info_formatted,
        xref="paper",
        yref="paper",
        x=1.0,
        y=1.02,
        xanchor="right",
        yanchor="bottom",
        showarrow=False,
        font={"size": 12},
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor="rgba(0,0,0,0.2)",
        borderwidth=1,
    )


def get_column_index(df: pd.DataFrame, col_spec: int | str) -> int:
    """Convert column specification to numeric index."""
    if isinstance(col_spec, int):
        return col_spec
    if isinstance(col_spec, str):
        if col_spec.isdigit():
            return int(col_spec)
        if col_spec in df.columns:
            return df.columns.get_loc(col_spec)
        msg = f"Column '{col_spec}' not found in DataFrame"
        raise ValueError(msg)
    msg = f"Invalid column specification: {col_spec}"
    raise ValueError(msg)


def plot_individual_graphs(
    df: pd.DataFrame,
    name: str,
    xaxis_label: str,
    yaxis_label: str,
    legends: list[str],
    logy: bool,
    output_dir: str | None = None,
    x_col: int = 0,
    y_cols: list[int] | None = None,
    logx: bool = False,
    direction_cols: list[int] | None = None,
    direction_filter: str | None = None,
    xlim: list[float] | None = None,
    ylim: list[float] | None = None,
    grid: bool = False,
    invert_x: bool = False,
    invert_y: bool = False,
    title: str | None = None,
    max_legend_items: int | None = None,
    legend_info: str | None = None,
) -> None:
    """Plot individual graphs for each column."""
    if y_cols is None:
        y_cols = list(range(df.shape[1]))
        y_cols.remove(x_col)

    x = df.iloc[:, x_col]
    image_dir = _get_image_dir(output_dir)

    for i, legend in enumerate(legends):
        y = df.iloc[:, y_cols[i]]

        fig, ax = plt.subplots(
            figsize=FIG_SIZE,
            tight_layout=True,
        )

        if logy:
            ax.set_yscale("log")

        if logx:
            ax.set_xscale("log")

        _plot_series(
            ax=ax,
            df=df,
            x=x,
            y=y,
            legend=legend,
            direction_cols=direction_cols,
            direction_filter=direction_filter,
            index=i,
        )

        ax.set_xlabel(xaxis_label)
        ax.set_ylabel(yaxis_label)
        ax.set_title(
            _create_title(title, name, legend),
            pad=20,
        )

        _configure_axes(
            ax=ax,
            xlim=xlim,
            ylim=ylim,
            invert_x=invert_x,
            invert_y=invert_y,
            grid=grid,
        )

        legend_obj = _create_legend(
            ax=ax,
            df=df,
            direction_cols=direction_cols,
            direction_filter=direction_filter,
            index=i,
            max_legend_items=max_legend_items,
        )

        if legend_info:
            _draw_legend_info(
                fig=fig,
                ax=ax,
                legend_obj=legend_obj,
                legend_info=legend_info,
            )

        output_file = os.path.join(
            image_dir,
            f"{sanitize_filename(name)}.png",
        )

        fig.savefig(output_file)
        plt.close(fig)


def _configure_axes(
    ax: plt.Axes,
    xlim: list[float] | None,
    ylim: list[float] | None,
    invert_x: bool,
    invert_y: bool,
    grid: bool,
) -> None:
    """Configure axis limits and appearance."""
    if xlim is not None:
        ax.set_xlim(xlim[0], xlim[1])

    if ylim is not None:
        ax.set_ylim(ylim[0], ylim[1])

    if invert_x:
        ax.invert_xaxis()

    if invert_y:
        ax.invert_yaxis()

    if grid:
        ax.grid(True)


def _get_image_dir(output_dir: str | None) -> str:
    if output_dir is None:
        return str(Path.cwd())

    if not os.path.exists(output_dir):
        msg = f"Output directory does not exist: {output_dir}"
        raise FileNotFoundError(msg)

    if not os.path.isdir(output_dir):
        msg = f"Output path is not a directory: {output_dir}"
        raise NotADirectoryError(msg)

    return output_dir


def _create_title(
    title: str | None,
    name: str,
    legend: str,
) -> str:
    if not title:
        return sanitize_filename(name)

    if "_" in name:
        return f"{title} - {name.split('_')[-1]}"

    return f"{title} - {legend}"


def _plot_series(
    ax: plt.Axes,
    df: pd.DataFrame,
    x: pd.Series,
    y: pd.Series,
    legend: str,
    direction_cols: list[int] | None,
    direction_filter: str | None,
    index: int,
) -> None:
    if not (
        direction_cols
        and index < len(direction_cols)
        and direction_cols[index] is not None
    ):
        ax.plot(x, y, label=legend)
        return

    direction_data = df.iloc[:, direction_cols[index]]

    for direction_value in direction_data.unique():
        if pd.isna(direction_value):
            continue

        if (
            direction_filter is not None
            and direction_value != direction_filter
        ):
            continue

        mask = direction_data == direction_value
        ax.plot(x[mask], y[mask], label=direction_value)


def _create_legend(
    ax: plt.Axes,
    df: pd.DataFrame,
    direction_cols: list[int] | None,
    direction_filter: str | None,
    index: int,
    max_legend_items: int | None,
) -> Legend | None:
    if not (
        direction_cols
        and index < len(direction_cols)
        and direction_cols[index] is not None
    ):
        return None

    direction_data = df.iloc[:, direction_cols[index]]

    unique = [d for d in direction_data.unique() if not pd.isna(d)]

    if direction_filter is not None:
        unique = [d for d in unique if d == direction_filter]

    if len(unique) <= 1:
        return None

    if max_legend_items is not None and len(unique) > max_legend_items:
        return None

    return ax.legend()


def _draw_legend_info(
    fig: plt.Figure,
    ax: plt.Axes,
    legend_obj: plt.Legend | None,
    legend_info: str,
) -> None:
    legend_info = legend_info.replace("\\n", "\n")

    if legend_obj is None:
        ax.text(
            0.98,
            0.98,
            legend_info,
            transform=ax.transAxes,
            fontsize=18,
            verticalalignment="top",
            horizontalalignment="right",
            linespacing=1.2,
        )
        return

    fig.canvas.draw()

    legend_bbox = legend_obj.get_window_extent(
        renderer=fig.canvas.get_renderer(),
    )

    legend_bbox_axes = legend_bbox.transformed(
        ax.transAxes.inverted(),
    )

    fontsize = (
        legend_obj.get_texts()[0].get_fontsize()
        if legend_obj.get_texts()
        else 20
    )

    center_x = (legend_bbox_axes.x0 + legend_bbox_axes.x1) / 2
    center_y = (legend_bbox_axes.y0 + legend_bbox_axes.y1) / 2

    is_right = (
        center_x > LEGEND_CENTER_THRESHOLD
        or legend_bbox_axes.x1 > LEGEND_RIGHT_THRESHOLD
    )

    is_bottom = center_y < LEGEND_CENTER_THRESHOLD

    if is_bottom:
        if legend_bbox_axes.y1 + LEGEND_BOTTOM_OFFSET < 1.0:
            text_y = legend_bbox_axes.y1 + (LEGEND_BOTTOM_OFFSET / 2)
            valign = "bottom"
        else:
            text_y = LEGEND_TOP_OFFSET
            valign = "top"
    else:
        text_y = legend_bbox_axes.y0 - LEGEND_BOTTOM_OFFSET
        valign = "top"

    if is_right:
        text_x = legend_bbox_axes.x1
        halign = "right"
    else:
        text_x = legend_bbox_axes.x0
        halign = "left"

    if is_bottom and text_y > LEGEND_BOTTOM_THRESHOLD:
        text_x = LEGEND_TOP_OFFSET
        halign = "right"

    ax.text(
        text_x,
        text_y,
        legend_info,
        transform=ax.transAxes,
        fontsize=max(8, fontsize - 2),
        verticalalignment=valign,
        horizontalalignment=halign,
        linespacing=1.2,
    )
