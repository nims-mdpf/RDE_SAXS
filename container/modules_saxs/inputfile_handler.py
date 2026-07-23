from pathlib import Path

import pandas as pd
from rdetoolkit.models.rde2types import RdeOutputResourcePath

from modules_saxs.interfaces import IInputFileParser


class FileReader(IInputFileParser):
    """Reads and processes structured ras files into data and metadata blocks.

    This class is responsible for reading structured files which have specific patterns for data and metadata.
    It then separates the contents into data blocks and metadata blocks.

    Attributes:
        data (dict[str, pd.DataFrame]): Dictionary to store separated data blocks.
        meta (dict[str, list[str]]): Dictionary to store separated metadata blocks.

    """

    def __init__(self, config: dict):
        self.data: dict[str, pd.DataFrame] = {}
        self.region_num = 0
        self.fitting_data: dict[str, pd.DataFrame] = {}
        self.fitting_result: dict[str, pd.DataFrame] = {}
        self.config = config
        self.resource_paths: RdeOutputResourcePath

    def get_files_from_rasx(self, rasx_path: Path) -> list[str]:
        """Substance is in rigaku/rasx/inputfile_handler.py (only .rasx)."""
        return []
