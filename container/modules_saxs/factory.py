from __future__ import annotations

from pathlib import Path

import yaml
from rdetoolkit.exceptions import StructuredError
from rdetoolkit.models.rde2types import RdeOutputResourcePath

from modules_saxs.custom.csv.inputfile_handler import FileReader as CsvFileReader
from modules_saxs.custom.csv.meta_handler import MetaParser as CsvMetaParser
from modules_saxs.graph_handler import GraphPlotter
from modules_saxs.inputfile_handler import FileReader as SaxsFileReader
from modules_saxs.invoice_handler import InvoiceWriter
from modules_saxs.meta_handler import MetaParser as SaxsMetaParser
from modules_saxs.models import ScaleType
from modules_saxs.rigaku.ras.inputfile_handler import FileReader as RasFileReader
from modules_saxs.rigaku.ras.meta_handler import MetaParser as RasMetaParser
from modules_saxs.rigaku.rasx.inputfile_handler import FileReader as RasxFileReader
from modules_saxs.rigaku.rasx.meta_handler import MetaParser as RasxMetaParser
from modules_saxs.structured_handler import StructuredDataProcessor

RIGAKU_SUFFIX_CLASS_MAPPING = {
    "rigaku": {
        ".ras": (RasFileReader, RasMetaParser),
        ".rasx": (RasxFileReader, RasxMetaParser),
    },
}
CUSTOM_SUFFIX_CLASS_MAPPING = {
    "custom": {
        ".csv": (CsvFileReader, CsvMetaParser),
    },
}
FILES_RAW_REFERENCE = 2


class SaxsFactory:
    """Obtain a variety of data for use in the SAX's Structured processing."""

    def __init__(
        self,
        invoice_writer: InvoiceWriter,
        file_reader: SaxsFileReader,
        meta_parser: SaxsMetaParser,
        graph_plotter: GraphPlotter,
        structured_processor: StructuredDataProcessor,
    ):
        self.invoice_writer = invoice_writer
        self.file_reader = file_reader
        self.meta_parser = meta_parser
        self.graph_plotter = graph_plotter
        self.structured_processor = structured_processor

    @staticmethod
    def get_config(resource_paths: RdeOutputResourcePath, path_tasksupport: Path) -> dict:
        """Obtain a variety of data.

        Obtain configuration data.

        Args:
            resource_paths (RdeOutputResourcePath): measurement file.
            path_tasksupport (Path): tasksupport path.

        Returns:
            config (dict): config data.

        """
        if not len(resource_paths.rawfiles):
            err_msg = "No measurement file found."
            raise StructuredError(err_msg)
        # rawfile = resource_paths.rawfiles[0]

        # suffix = rawfile.suffix.lower()
        rdeconfig_file = path_tasksupport.joinpath("rdeconfig.yaml")

        # Get the graph scale of the representative image from rdeconfig.yaml.
        # TODO: Processes that should be moved to rdetoolkit in the future.
        if not rdeconfig_file.exists():
            err_msg = f"File not found: {rdeconfig_file}"
            raise StructuredError(err_msg)
        try:
            with open(rdeconfig_file) as file:
                config = yaml.safe_load(file)
        except Exception:
            err_msg = f"Invalid configuration file: {rdeconfig_file}"
            raise StructuredError(err_msg) from None

        validate_saxs_config(config)

        return config

    @staticmethod
    def get_objects(rawfiles: tuple[Path, ...], path_tasksupport: Path, config: dict) -> tuple[Path, SaxsFactory]:
        """Obtain a variety of data.

        Retrieve the class to be executed.
        Obtain the metadata definition file to be used.

        Args:
            rawfiles (tuple[Path, ...]): measurement file.
            path_tasksupport (Path): tasksupport path.
            config (dict): config data.

        Returns:
            metadata_def (Path): Metadata file path.
            module (Any): classes
                InvoiceWriter (class): Overwrite invoice file.
                FilaReader (class): Reads and processes structured files into data and metadata blocks.
                MetaParser (class): Parses metadata and saves it to a specified path.
                GraphPlotter (class): Utility for plotting data using various types of plots.
                StructuredDataProcessor (class): Template class for parsing structured data.

        """
        if len(rawfiles) > FILES_RAW_REFERENCE:
            err_msg = "Up to two input files are allowed."
            raise StructuredError(err_msg)

        # (manufacturer: rigaku, custom) Input file extension check
        manufacturer = config['saxs']['manufacturer']
        valid_extensions = {
            "rigaku": {".ras", ".rasx"},
            "custom": {".csv"},
        }
        suffix: str = rawfiles[0].suffix.lower()
        for rawfile in rawfiles:
            suffix = rawfile.suffix.lower()
            if suffix not in valid_extensions.get(manufacturer, set()):
                err_msg = f"Format Error: Input data extension is incorrect: {suffix}"
                raise StructuredError(err_msg)

        # Obtain classes according to manufacturer and file extension.
        class_filereader, class_metaparser = get_classes(manufacturer, suffix)
        main_image_scaletype, other_image_scaletype = get_scale_types(config['saxs']['main_image_setting'])
        delimiter_type: str = ""
        metadata_def = path_tasksupport.joinpath(f'metadata-def_{manufacturer}_{suffix[1:]}{delimiter_type}.json')

        module = SaxsFactory(
            InvoiceWriter(config),
            class_filereader(config),
            class_metaparser(metadata_def_json_path=metadata_def, config=config),
            GraphPlotter(main_image_scaletype, other_image_scaletype, config),
            StructuredDataProcessor(config),
        )

        return metadata_def, module


def validate_saxs_config(config: dict) -> None:
    """Validate SAXS-specific configuration."""
    if not isinstance(config, dict):
        msg = "Invalid configuration format."
        raise StructuredError(msg)
    if "saxs" not in config:
        msg = "Missing 'saxs' configuration."
        raise StructuredError(msg)
    saxs_config = config["saxs"]
    if not isinstance(saxs_config, dict):
        msg = "Invalid 'saxs' configuration format."
        raise StructuredError(msg)
    manufacturer = saxs_config.get("manufacturer")
    if manufacturer not in {"rigaku", "custom"}:
        err_msg = (
            "Invalid saxs.manufacturer. "
            f"Expected 'rigaku' or 'custom', got '{manufacturer}'."
        )
        raise StructuredError(err_msg)
    mode = saxs_config.get("mode")
    if mode not in {"saxs", "saxs_fitting"}:
        err_msg = (
            "Invalid saxs.mode. "
            f"Expected 'saxs' or 'saxs_fitting', got '{mode}'."
        )
        raise StructuredError(err_msg)
    main_image_setting = saxs_config.get("main_image_setting")
    if (
        main_image_setting is not None
        and main_image_setting != "log"
    ):
        err_msg = (
            "Invalid saxs.main_image_setting. "
            f"Expected 'log' or omitted, got '{main_image_setting}'."
        )
        raise StructuredError(err_msg)


def get_classes(manufacturer: str, suffix: str) -> tuple[type[SaxsFileReader], type[SaxsMetaParser]]:
    """Get the appropriate FileReader and MetaParser classes based on the manufacturer and file suffix."""
    try:
        match manufacturer:
            case "rigaku":
                return RIGAKU_SUFFIX_CLASS_MAPPING[manufacturer][suffix]
            case "custom":
                return CUSTOM_SUFFIX_CLASS_MAPPING[manufacturer][suffix]
            case _:
                raise KeyError
    except KeyError:
        err_msg = f"Unsupported combination of manufacturer '{manufacturer}' and file extension '{suffix}'"
        raise StructuredError(err_msg) from None


def get_scale_types(main_image_setting: str) -> tuple[ScaleType, ScaleType]:
    """Get the scale types for the main and other images based on the configuration.

    Args:
        main_image_setting (str): The setting for the main image scale type.

    Returns:
        Tuple[ScaleType, ScaleType]: The scale types for the main and other images.

    """
    if main_image_setting == "log":
        return ScaleType.log, ScaleType.linear
    return ScaleType.linear, ScaleType.log
