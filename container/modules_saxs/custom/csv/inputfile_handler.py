from __future__ import annotations

import csv
import re
from collections.abc import Generator, Iterable
from pathlib import Path

import pandas as pd
from rdetoolkit.exceptions import StructuredError
from rdetoolkit.models.rde2types import RdeOutputResourcePath
from rdetoolkit.rde2util import CharDecEncoding

from modules_saxs.inputfile_handler import FileReader as SaxsFileReader
from modules_saxs.interfaces import ExtendMetaType
from modules_tool.saxs_fit_de import main_fitting


class FileReader(SaxsFileReader):
    """Reads and processes structured csv files into data and metadata blocks.

    This class is responsible for reading structured files which have specific patterns for data and metadata.
    It then separates the contents into data blocks and metadata blocks.

    Attributes:
        data (dict[str, pd.DataFrame]): Dictionary to store separated data blocks.
        meta (dict[str, list[str]]): Dictionary to store separated metadata blocks.

    """

    __mode__ = "csv"

    def __init__(self, config: dict):
        super().__init__(config)
        self.meta: dict[str, ExtendMetaType] = {}

    def read(
        self,
        resource_paths: RdeOutputResourcePath,
    ) -> Generator[
        tuple[pd.DataFrame, ExtendMetaType] | tuple[pd.DataFrame, ExtendMetaType, pd.DataFrame, pd.DataFrame],
        None,
        None,
    ]:
        """Read the structured file and returns separated data and metadata.

        Args:
            resource_paths (RdeOutputResourcePath): The path of the structured file to read.

        Returns:
            tuple[tuple[pd.DataFrame, ExtendMetaType], ...]: A tuple containing two dictionaries -
            the first one for data blocks and the second one for metadata blocks.

        Raises:
            StructuredError: If the file is formatted incorrectly.

        """
        self.resource_paths = resource_paths

        if len(resource_paths.rawfiles) == 1:
            srcpath_data = resource_paths.rawfiles[0]
        else:
            err_msg = "Files of the same length are not permitted."
            raise StructuredError(err_msg)

        enc = CharDecEncoding.detect_text_file_encoding(srcpath_data)
        with open(srcpath_data, encoding=enc) as f:
            df_data, self.meta = self.split_data_meta(csv.reader(f))
        if not df_data or not self.meta:
            err_msg = f"Cannot read the file because it is formatted incorrectly: {srcpath_data}"
            raise StructuredError(err_msg)

        for series_value_i, _ in df_data.items():
            self.data[series_value_i] = df_data[series_value_i]

        mode = self.config["saxs"]["mode"]
        if not (
            mode == "saxs_fitting"
            and Path(srcpath_data).suffix.lower() == ".csv"
        ):
            err_msg = (
                "CSV format is not supported for the selected mode, "
                "or no mode has been selected. "
                f"Please select a valid mode. (mode='{mode}', file='{srcpath_data}')"
            )
            raise StructuredError(err_msg)

        fitting_data, fitting_result = main_fitting(
            srcpath_data=srcpath_data,
            data=self.data,
            config=self.config,
            resource_paths=self.resource_paths,
        )

        self.region_num = len(self.data)

        for data_key, meta_key in zip(self.data, self.meta, strict=True):
            yield (
                self.convert_dtype(self.data[data_key]),
                self.meta[meta_key],
                self.convert_dtype(fitting_data[data_key]),
                fitting_result[data_key],
            )

    def get_region_number(self, *, input_path: Path | None = None) -> int:
        """Get the number of regions.

        Args:
            input_path (Path | None): Measurement file path.

        Returns:
            int: Number of regions.

        """
        # if input_path is None:
        #     return self.region_num
        # data_meta_mappings = [df_data for df_data, _ in self.read(input_path)]
        # self.region_num = len(data_meta_mappings)
        return self.region_num

    def split_data_meta(self, contents: Iterable) -> tuple[dict[str, pd.DataFrame], dict[str, ExtendMetaType]]:
        """Private method to split the contents into data and metadata blocks.

        Args:
            contents (str): The contents of the structured file as a string.

        Returns:
            tuple[dict[str, pd.DataFrame], dict[str, ExtendMetaType]]: A tuple containing two dictionaries -
            the first one for data blocks and the second one for metadata blocks.

        """
        data = list(contents)
        meta_blocks: dict[str, ExtendMetaType] = {}
        data_blocks: dict[str, pd.DataFrame] = {}

        meta_blocks["series_meta1"] = {}
        data_blocks["series_value1"] = pd.DataFrame(data[1:], columns=data[0])

        return data_blocks, meta_blocks

    def search_element_with_substring(
            self,
            header_info: ExtendMetaType,
            substring: str,
            *,
            pattern: str = r'"(.*?)"',
    ) -> str:
        """Search element with substring.

        Args:
            header_info (ExtendMetaType): The header information dictionary.
            substring (str): Element.
            pattern (str): Delimiter.

        Returns:
            str: Value of the relevant element.

        """
        substring_lists = [element for element in header_info if substring in element]
        _substring: str = ""
        if len(substring_lists) > 0:
            _substring = str(substring_lists[0])
        else:
            return ""

        match = re.search(pattern, _substring)
        return "" if match is None else match.group(1)

    def convert_dtype(self, dataframe: pd.DataFrame, *, totype: str = "float") -> pd.DataFrame:
        """Convert data type.

        Args:
            dataframe (pd.DataFrame): Data frame before conversion.
            totype (str): Converted data type.

        Returns:
            pd.DataFrame: Data frame after conversion.

        """
        return dataframe.map(self.__helper_convert_string_numeric, dtype=totype)

    def __helper_convert_string_numeric(self, x: str, dtype: str) -> int | float:
        """Convert string numeric.

        Args:
            x (str): Before conversion.
            dtype (str): Converted data type.

        Returns:
            int | float: After conversion.

        """
        if dtype not in ["float", "int"]:
            err_msg = f"UnSupported dtype: {dtype}"
            raise StructuredError(err_msg)
        try:
            if dtype == "float":
                return float(x)
            return int(x)
        except ValueError:
            err_msg = f"Failed to convert {x} to {dtype}"
            raise StructuredError(err_msg) from None
