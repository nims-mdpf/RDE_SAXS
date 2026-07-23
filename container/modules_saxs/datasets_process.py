from __future__ import annotations

from typing import Final

from rdetoolkit.models.rde2types import RdeInputDirPaths, RdeOutputResourcePath
from rdetoolkit.rde2util import Meta

from modules_saxs.factory import SaxsFactory


def dataset(srcpaths: RdeInputDirPaths, resource_paths: RdeOutputResourcePath) -> None:
    """Execute structured processing in SAXS.

    Execute structured text processing, metadata extraction, and visualization.
    It handles structured text processing, metadata extraction, and graphing.
    Other processing required for structuring may be implemented as needed.

    Args:
        srcpaths (RdeInputDirPaths): Paths to input resources for processing.
        resource_paths (RdeOutputResourcePath): Paths to output resources for saving results.

    Returns:
        None

    Note:
        The actual function names and processing details may vary depending on the project.

    """
    config = SaxsFactory.get_config(resource_paths, srcpaths.tasksupport)
    metadata_def, module = SaxsFactory.get_objects(resource_paths.rawfiles, srcpaths.tasksupport, config)

    mode = config["saxs"].get("mode", "saxs")
    compressd_files: list[str] = []
    region_num: int | None = None
    repeat_meta: Meta | None = None
    if mode == "saxs_fitting":
        for data, meta, fitting_data, fitting_result in module.file_reader.read(resource_paths):
            region_num = module.file_reader.get_region_number()
            const_meta, repeat_meta = module.meta_parser.parse(meta)
            module.structured_processor.save_csv(
                resource_paths,
                fitting_data,
                fitting_result,
                region_num=region_num,
            )

            if resource_paths.rawfiles[0].suffix == ".rasx":
                compressd_files = module.file_reader.get_files_from_rasx(resource_paths.rawfiles[0])
                module.structured_processor.save_structured_contents(resource_paths, compressd_files)

            module.graph_plotter.plot_main(
                data,
                resource_paths,
                region_num,
                repeat_meta,
                fitting_data,
            )

            module.invoice_writer.overwrite_invoice_measured_date(
                resource_paths.rawfiles[0].suffix,
                resource_paths,
                const_meta,
                repeat_meta,
            )

        module.meta_parser.set_const_meta(config, fitting_result)

    if mode == "saxs":
        for data, meta in module.file_reader.read(resource_paths):
            region_num = module.file_reader.get_region_number()
            const_meta, repeat_meta = module.meta_parser.parse(meta)

            module.structured_processor.save_csv(
                resource_paths,
                data,
                None,
                region_num=region_num,
            )

            if resource_paths.rawfiles[0].suffix == ".rasx":
                compressd_files = module.file_reader.get_files_from_rasx(resource_paths.rawfiles[0])
                module.structured_processor.save_structured_contents(resource_paths, compressd_files)

            module.graph_plotter.plot_main(
                data,
                resource_paths,
                region_num,
                repeat_meta,
                None,
            )

            module.invoice_writer.overwrite_invoice_measured_date(
                resource_paths.rawfiles[0].suffix,
                resource_paths,
                const_meta,
                repeat_meta,
            )
    if config.get("saxs").get("main_image_setting"):
        default_values: dict = {}
        default_values['main_image_setting'] = config.get("saxs").get("main_image_setting")
        module.meta_parser.const_meta_info.update(default_values)

    module.meta_parser.save_meta(
        resource_paths.meta.joinpath("metadata.json"),
        Meta(metadata_def),
    )

    multi_resion_num: Final[int] = 2
    if region_num == multi_resion_num:
        module.graph_plotter.multiplot_main(resource_paths, repeat_meta)
