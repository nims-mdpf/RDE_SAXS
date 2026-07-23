from __future__ import annotations

import re
from collections.abc import Generator
from pathlib import Path

import numpy as np
import pandas as pd
from rdetoolkit.exceptions import StructuredError
from rdetoolkit.models.rde2types import RdeOutputResourcePath
from rdetoolkit.rde2util import CharDecEncoding

from modules_saxs.inputfile_handler import FileReader as SaxsFileReader
from modules_saxs.interfaces import ExtendMetaType
from modules_tool.saxs_fit_de import main_fitting

_SINGLE_FILE_COUNT = 1
_PAIR_FILE_COUNT = 2


class FileReader(SaxsFileReader):
    """Reads and processes structured ras files into data and metadata blocks.

    This class is responsible for reading structured files which have specific patterns for data and metadata.
    It then separates the contents into data blocks and metadata blocks.

    Attributes:
        data (dict[str, pd.DataFrame]): Dictionary to store separated data blocks.
        meta (dict[str, list[str]]): Dictionary to store separated metadata blocks.

    """

    __mode__ = "ras"

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

        srcpath_ref: Path | None = None
        rawfiles = resource_paths.rawfiles

        if len(rawfiles) == _SINGLE_FILE_COUNT:
            srcpath_data = rawfiles[0]

        elif len(rawfiles) == _PAIR_FILE_COUNT:
            sorted_rawfiles = sorted(rawfiles, key=lambda path: len(path.stem))

            if len(sorted_rawfiles[0].stem) == len(sorted_rawfiles[1].stem):
                err_msg = "Files of the same length are not permitted."
                raise StructuredError(err_msg)

            srcpath_data = sorted_rawfiles[0]
            srcpath_ref = sorted_rawfiles[1]

        else:
            err_msg = "Only one or two raw files are supported."
            raise StructuredError(err_msg)

        enc = CharDecEncoding.detect_text_file_encoding(srcpath_data)
        with open(srcpath_data, encoding=enc) as f:
            df_data, self.meta = self.split_data_meta(f.read())
        if not df_data or not self.meta:
            err_msg = f"Cannot read the file because it is formatted incorrectly: {srcpath_data}"
            raise StructuredError(err_msg)

        df_reference: dict[str, pd.DataFrame] | None = None
        if srcpath_ref:
            enc = CharDecEncoding.detect_text_file_encoding(srcpath_ref)
            with open(srcpath_ref, encoding=enc) as f:
                df_reference, _ = self.split_data_meta(f.read())
            if not df_reference:
                err_msg = f"Cannot read the file because it is formatted incorrectly: {srcpath_ref}"
                raise StructuredError(err_msg)

        self._concat_raw_and_ref(df_data, df_reference)

        mode = self.config["saxs"]["mode"]

        self.region_num = len(self.data.keys())
        if mode == "saxs_fitting":
            fitting_data, fitting_result = main_fitting(
                srcpath_data=srcpath_data,
                data=self.data,
                config=self.config,
                resource_paths=self.resource_paths,
            )

            yield from self._yield_saxs_fitting(
                fitting_data,
                fitting_result,
            )
        elif mode == "saxs":
            yield from self._yield_saxs()
        else:
            err_msg = (
                "ras format is not supported for the selected mode, "
                "or no mode has been selected. "
                f"Please select a valid mode. (mode='{mode}', file='{srcpath_data}')"
            )
            raise StructuredError(err_msg)

    def _yield_saxs(self) -> Generator[tuple[pd.DataFrame, ExtendMetaType], None, None]:
        """Yield SAXS data and metadata."""
        for data_key, meta_key in zip(self.data, self.meta, strict=False):
            yield (
                self.convert_dtype(self.data[data_key]),
                self.meta[meta_key],
            )

    def _yield_saxs_fitting(
        self,
        fitting_data: dict[str, pd.DataFrame],
        fitting_result: dict[str, pd.DataFrame],
    ) -> Generator[
        tuple[pd.DataFrame, ExtendMetaType, pd.DataFrame, pd.DataFrame],
        None,
        None,
    ]:
        """Yield SAXS fitting data, metadata, and fitting results."""
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

    def split_data_meta(self, contents: str) -> tuple[dict[str, pd.DataFrame], dict[str, ExtendMetaType]]:
        """Private method to split the contents into data and metadata blocks.

        Args:
            contents (str): The contents of the structured file as a string.

        Returns:
            tuple[dict[str, pd.DataFrame], dict[str, ExtendMetaType]]: A tuple containing two dictionaries -
            the first one for data blocks and the second one for metadata blocks.

        """
        meta_blocks: dict[str, ExtendMetaType] = {}
        data_blocks: dict[str, pd.DataFrame] = {}

        data_pattern = re.findall(r"\*RAS_INT_START\n(.*?)\*RAS_INT_END", contents, re.DOTALL)
        header_pattern = re.findall(r"\*RAS_HEADER_START\n(.*?)\*RAS_HEADER_END", contents, re.DOTALL)
        for i, (data_section, header_section) in enumerate(zip(data_pattern, header_pattern, strict=False), start=1):
            meta_blocks[f"series_meta{i}"] = header_section.strip().split("\n")
            header = self.make_header(meta_blocks[f"series_meta{i}"])

            # convert measured values to dataframes
            data_list = [line.split() for line in data_section.strip().split("\n")]
            df = pd.DataFrame(data_list)
            df[1] = (df[1].astype(float) * df[2].astype(float)).apply(lambda x: f"{x:.4f}")
            df = df.drop(2, axis=1)

            # convert 2θ to q
            header, df = self._convert_theta_to_q(header, df, meta_blocks[f"series_meta{i}"])

            data_blocks[f"series_value{i}"] = df.set_axis(header, axis="columns")

        return data_blocks, meta_blocks

    def make_header(self, header_info: ExtendMetaType) -> list[str]:
        """Make a header using provided header information.

        Args:
            header_info (ExtendMetaType): The header information dictionary.

        Returns:
            list[str]: The constructed header string.

        """
        _x_label = self.search_element_with_substring(header_info, "MEAS_SCAN_AXIS_X")
        x_label = self.__validation_greek_characters(_x_label)
        x_unit = self.search_element_with_substring(header_info, "MEAS_SCAN_UNIT_X")
        y_label = "Intensity"
        y_unit = self.search_element_with_substring(header_info, "MEAS_SCAN_UNIT_Y")
        return [f"{x_label} ({x_unit})", f"{y_label} ({y_unit})"]

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

    def _convert_theta_to_q(
            self,
            header: list[str],
            df: pd.DataFrame,
            header_info: ExtendMetaType,
    ) -> tuple[list[str], pd.DataFrame]:
        """Convert a 2θ axis to a momentum-transfer (q) axis.

        The function expects a DataFrame whose first column (df[0]) holds
        the 2θ values (in degrees) and whose second column (df[1]) holds
        the intensity (or any other y-value).  After conversion the first
        column is replaced by q values expressed in inverse Ångström
        (1/Å).  The original 2θ values are moved to column df[2] so
        that downstream plotting code can continue to use the convention
        x = df[0] and y = df[1].

        The conversion follows the physical relationship:

            q = (4 * π / λ) * sin(θ)

        where

        * θ = 2θ / 2  (in radians)
        * λ is the X-ray wavelength obtained from ``header_info``.

        Args:
            header: List of column-header strings that describes the current
                layout of ``df``. ``header[0]`` is the label of the present
                x-axis (normally something like "2θ (deg)").  The list
                is mutated in-place: the old label is appended to the end,
                and the first element is replaced by the new q-label.
            df: Pandas DataFrame containing the raw diffraction data.
                Expected layout before conversion:

                * ``df[0]`` - 2θ values (degrees)
                * ``df[1]`` - intensity (or any y-value)
                * ``df[2]`` - may be empty; will be filled with the original
                  2θ values after conversion.

            header_info: List of strings extracted from the original file
                header. It must contain the scan-axis identifier
                (e.g. "MEAS_SCAN_AXIS_X") and the information required to
                compute the wavelength.

        Returns:
            tuple: ``(header, df)`` where ``header`` is the possibly updated
            list of column names and ``df`` is the modified DataFrame whose
            first column now holds q values (1/Å).

        """
        wavelength = self._calculate_wavelength(header_info)
        x_label = self.search_element_with_substring(header_info, "MEAS_SCAN_AXIS_X")
        if x_label in ["2θ", "2Theta", "2θ/θ", "2Theta-Theta", "TwoThetaTheta", "2Theta-Theta"]:
            df_temp = pd.DataFrame()
            df_temp['2theta_rad'] = self._calculate_2theta_rag(df, header_info)
            df_temp['theta_rad'] = df_temp['2theta_rad'] / 2.0
            df_temp['q'] = (4.0 * np.pi / wavelength) * np.sin(df_temp['theta_rad'])
            df[2] = df[0]  # 元の2θは[2]に移動（plotがx=[0], y=[1]固定なので）
            df[0] = df_temp['q']
            header.append(header[0])  # header[0]を[2]にコピー
            header[0] = "q (Angstrom^-1)"
        return header, df

    def _concat_raw_and_ref(
        self,
        data_raw: dict[str, pd.DataFrame],
        data_reference: dict[str, pd.DataFrame] | None,
    ) -> None:
        """Concat raw dataframe and reference dataframe.

        Args:
            data_raw (dict[str, pd.DataFrame]): _description_
            data_reference (dict[str, pd.DataFrame]): _description_

        """
        intensity_name: str = ""
        for series_value_i, _ in data_raw.items():
            intensity_name: str = data_raw[series_value_i].columns[1]
            data_raw[series_value_i] = data_raw[series_value_i].rename(columns={
                data_raw[series_value_i].columns[1]: "data: " + data_raw[series_value_i].columns[1],
            })
            data_raw[series_value_i] = data_raw[series_value_i][[
                data_raw[series_value_i].columns[2],
                data_raw[series_value_i].columns[0],
                data_raw[series_value_i].columns[1],
            ]]
            if not data_reference:
                self.data[series_value_i] = data_raw[series_value_i]

        if data_reference:
            for series_value_i in data_reference:
                data_reference[series_value_i] = data_reference[series_value_i].rename(columns={
                    data_reference[series_value_i].columns[1]: "ref: " + data_reference[series_value_i].columns[1],
                })
                data_reference[series_value_i] = data_reference[series_value_i][[
                    data_reference[series_value_i].columns[1],
                ]]
                self.data[series_value_i] = pd.concat(
                    [data_raw[series_value_i], data_reference[series_value_i]],
                    axis=1,
                )
                self.data[series_value_i]["Corrected: " + intensity_name] = \
                    (pd.to_numeric(self.data[series_value_i].iloc[:, 2], errors='coerce')
                     - pd.to_numeric(self.data[series_value_i].iloc[:, 3], errors='coerce')).round(5)

    def _calculate_wavelength(self, header_info: ExtendMetaType) -> float:
        """Calculate wavelength.

        Args:
            header_info (ExtendMetaType): header info.

        Returns:
            float: wavelength

        """
        k_alpha1 = self.search_element_with_substring(header_info, "HW_XG_WAVE_LENGTH_ALPHA1")
        k_alpha1 = float(k_alpha1)
        k_alpha2 = self.search_element_with_substring(header_info, "HW_XG_WAVE_LENGTH_ALPHA2")
        k_alpha2 = float(k_alpha2)
        k_alpha = (2 * k_alpha1 + k_alpha2) / 3
        return float(k_alpha)

    def _calculate_2theta_rag(self, df: pd.DataFrame, header_info: ExtendMetaType) -> pd.DataFrame:
        """Calculate 2theta rag.

        Args:
            df (pd.DataFrame): dataframe.
            header_info (ExtendMetaType): header infomation.

        Returns:
            pd.DataFrame: dataframe.

        """
        df_result = df.copy()
        x_unit = self.search_element_with_substring(header_info, "MEAS_SCAN_UNIT_X")
        if x_unit == 'deg':
            return np.radians(df_result[0].astype(float))
        return df_result[0].astype(float)

    def __helper_convert_string_numeric(self, x: str, dtype: str) -> pd.DataFrame:
        """Convert string numeric.

        Args:
            x (str): Before conversion.
            dtype (str): Converted data type.

        Returns:
            pd.DataFrame: After conversion.

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

    def __validation_greek_characters(self, text: str) -> str:
        """Validate greek characters.

        Args:
            text (str): String to be verified.

        Returns:
            str: Post-validated string.

        """
        char_maps = {"TwoThetaTheta": "2Theta-Theta", "2θ/θ": "2Theta-Theta", "2θ": "2Theta"}
        replace_value = char_maps.get(text)
        if replace_value:
            return replace_value
        return text
