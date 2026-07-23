from __future__ import annotations

import os
import re
import zipfile
from collections.abc import Generator
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd
from rdetoolkit.exceptions import StructuredError
from rdetoolkit.models.rde2types import RdeOutputResourcePath

from modules_saxs.inputfile_handler import FileReader as SaxsFileReader
from modules_saxs.interfaces import ExtendMetaType
from modules_saxs.models import Data0, Data1, MeasurementConditions, Root
from modules_tool.saxs_fit_de import main_fitting

_SINGLE_FILE_COUNT = 1
_PAIR_FILE_COUNT = 2


class FileReader(SaxsFileReader):
    """A class to read rasx files and return a list of measurement data and settings.

    This class reads the information stored in rasx files (information described in Root.xml),
    retrieving both the measurement data and the configured settings file used during the measurement.

    Args:
        Attributes:
        data (dict[str, pd.DataFrame]): Stores the measurement data contained in Profile*.xml files,
                                        converted into pandas.DataFrame format.
        meta (dict[str, list[str]]): Stores the settings file used during measurement,
                                     contained in MeasurementConditions*.xml files, as an ExtendMetaType.

    """

    __mode__ = "rasx"
    TWOTHETA_Q_DATA = 3
    TWOTHETA_Q_DATA_REF_CORRECTED = 5

    def __init__(self, config: dict):
        super().__init__(config)
        self.meta: dict[str, MeasurementConditions] = {}

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

        self.meta = self.get_metadata(srcpath_data)
        df_data = self.get_data(srcpath_data)

        if not df_data or not self.meta:
            err_msg = f"Cannot read the file because it is formatted incorrectly: {srcpath_data}"
            raise StructuredError(err_msg)

        df_reference: dict[str, pd.DataFrame] | None = None
        if srcpath_ref:
            df_reference = self.get_data(srcpath_ref)

            if not df_reference:
                err_msg = f"Cannot read the file because it is formatted incorrectly: {srcpath_ref}"
                raise StructuredError(err_msg)

        self.region_num = len(df_data.keys())
        mode = self.config["saxs"]["mode"]

        prepared_data: dict[str, pd.DataFrame] = {}
        prepared_meta: dict[str, MeasurementConditions] = {}

        for index, profile_key in enumerate(
            sorted(
                df_data.keys(),
                key=lambda x: int(self._extract_number(x)),
            ),
            start=1,
        ):
            region_key = f"series_value{index}"

            meta_key = self._find_metadata_key(
                profile_key,
                self.meta,
            )

            prepared_data[region_key] = self._prepare_data(
                df_data,
                df_reference,
                self.meta,
                profile_key,
                meta_key,
            )

            prepared_meta[region_key] = self.meta[meta_key]

        self.meta = prepared_meta
        if mode == "saxs":
            yield from self._yield_saxs(prepared_data)

        elif mode == "saxs_fitting":
            fitting_data, fitting_result = main_fitting(
                srcpath_data=srcpath_data,
                data=prepared_data,
                config=self.config,
                resource_paths=self.resource_paths,
            )

            yield from self._yield_saxs_fitting(
                prepared_data,
                fitting_data,
                fitting_result,
            )

        else:
            err_msg = (
                "rasx format is not supported for the selected mode, "
                "or no mode has been selected. "
                f"Please select a valid mode. (mode='{mode}', file='{srcpath_data}')"
            )
            raise StructuredError(err_msg)

    def _yield_saxs(
        self,
        data: dict[str, pd.DataFrame],
    ) -> Generator[tuple[pd.DataFrame, ExtendMetaType], None, None]:
        """Yield SAXS data and metadata."""
        for region_key, dataframe in data.items():
            yield (
                dataframe,
                self.meta[region_key],
            )

    def _yield_saxs_fitting(
        self,
        data: dict[str, pd.DataFrame],
        fitting_data: dict[str, pd.DataFrame],
        fitting_result: dict[str, pd.DataFrame],
    ) -> Generator[
        tuple[pd.DataFrame, ExtendMetaType, pd.DataFrame, pd.DataFrame],
        None,
        None,
    ]:
        """Yield SAXS fitting data, metadata, and fitting results."""
        for region_key, dataframe in data.items():
            yield (
                dataframe,
                self.meta[region_key],
                fitting_data[region_key],
                fitting_result[region_key],
            )

    def _find_metadata_key(
        self,
        profile_key: str,
        metadata: dict[str, MeasurementConditions],
    ) -> str:
        """Match Profile*.txt and MeasurementConditions*.xml.

        Example:
            Data0/Profile0.txt
            ->
            Data0/MesurementConditions0.xml

        """
        profile_number = self._extract_number(profile_key)

        for meta_key in metadata:
            meta_number = self._extract_number(meta_key)

            if profile_number == meta_number:
                return meta_key

        err_msg = f"Cannot find metadata for {profile_key}"
        raise StructuredError(err_msg)

    def _extract_number(
        self,
        filepath: str,
    ) -> str:
        """Extract index from Profile or MeasurementConditions filename."""
        filename = os.path.basename(filepath)

        match = re.search(
            r"(?:Profile|MesurementConditions)(\d+)",
            filename,
        )

        if match is None:
            err_msg = f"Cannot extract index from {filepath}"
            raise StructuredError(err_msg)

        return match.group(1)

    def _prepare_data(
        self,
        df_data: dict[str, pd.DataFrame],
        df_reference: dict[str, pd.DataFrame] | None,
        meta: ExtendMetaType,
        data_key: str,
        meta_key: str,
    ) -> pd.DataFrame:
        """Prepare data."""
        header = self.make_header(meta[meta_key])
        ref_df = df_reference[data_key] if df_reference else None

        return self.reformat_dataframe(
            df_data[data_key],
            ref_df,
            meta[meta_key],
            header=header,
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
        # self.region_num = len([f for f in self.get_files_from_rasx(input_path) if "Profile" in f])
        return self.region_num

    def get_metadata(self, rasx_path: Path) -> dict[str, MeasurementConditions]:
        """Get metadata from compressed files.

        Args:
            rasx_path (Path): rasx raw file

        Yields:
            Tuple[str, MeasurementConditions]: the target file name and metadata within the compressed file

        Note:
            If you change the data class MeasurementConditions to a dictionary type:
            >>> rasx = SimpleRasxHangler('test.rasx')
            >>> for filename, meta in rasx.get_metadata():
            >>>     # convert dataclass to dict
            >>>     print(meta.dict())

        """
        metadata_files = [f for f in self.get_files_from_rasx(rasx_path) if "MesurementConditions" in f]
        self.metadata_map: dict[str, MeasurementConditions] = {}
        for filename in metadata_files:
            xml_data = self.open_file(filename, rasx_path)
            convert_xml_to_meta = self.__extract_metadata_from_xml(xml_data)
            convert_xml_to_meta = cast(MeasurementConditions, convert_xml_to_meta)
            if convert_xml_to_meta is not None:
                self.metadata_map[filename] = convert_xml_to_meta
            else:
                err_msg = "Could not read metadata [xml]"
                raise StructuredError(err_msg)
        return self.metadata_map

    def get_data(self, rasx_path: Path) -> dict[str, pd.DataFrame]:
        """Get mesurementdata from compressed files.

        Args:
            rasx_path (Path): rasx raw file

        Return:
            Tuple[str, pd.DataFrame]: the target file name and mesurementdata within the compressed file

        """
        files = [f for f in self.get_files_from_rasx(rasx_path) if "Profile" in f]
        self.data_maps: dict[str, pd.DataFrame] = {}
        for file in files:
            data = self.open_compressedfile_dataframe(file, rasx_path)
            self.data_maps[file] = data
        return self.data_maps

    def make_header(self, header_info: MeasurementConditions) -> list[str]:
        """Make a header using provided header information.

        Args:
            header_info (MeasurementConditions): The header information dictionary.

        Returns:
            list[str]: The constructed header string.

        """
        x_label = header_info.scaninformation.AxisName
        x_unit = header_info.scaninformation.PositionUnit
        y_label = "Intensity"
        y_unit = header_info.scaninformation.IntensityUnit
        return [f"{x_label} ({x_unit})", f"{y_label} ({y_unit})"]

    def reformat_dataframe(
        self,
        df_data: pd.DataFrame,
        df_reference: pd.DataFrame | None,
        header_info: MeasurementConditions,
        *,
        header: list[str],
    ) -> pd.DataFrame:
        """Reformat data frames. Multiply the second and third columns of measured data and add a header.

        Args:
            df_data (pd.DataFrame): raw dataframe.
            df_reference (pd.DataFrame | None): reference dataframe.
            header_info (MeasurementConditions): header info.
            header (list[str] | None): header of the CSV file.

        Returns:
            pd.DataFrame: Reformatted data frame.

        """
        intensity_name: str = df_data.columns[1]
        reformat_dataframe: pd.DataFrame = df_data
        header_original = header.copy()
        header_original.append("")

        wavelength = self._calculate_wavelength(header_info)
        if header[0].startswith(("2θ", "2Theta", "2θ/θ", "2Theta-Theta", "TwoThetaTheta", "2Theta-Theta")):
            df_temp = pd.DataFrame()
            df_temp['2theta_rad'] = self._calculate_2theta_rag(df_data, header_info)
            df_temp['theta_rad'] = df_temp['2theta_rad'] / 2.0
            df_temp['q'] = (4.0 * np.pi / wavelength) * np.sin(df_temp['theta_rad'])
            df_data[2] = df_data[0]  # 元の2θは[2]に移動（plotがx=[0], y=[1]固定なので）
            df_data[0] = df_temp['q']
            header.append(header[0])  # header[0]を[2]にコピー
            header[0] = "q (Angstrom^-1)"
        df_data.columns = header

        if df_data.shape[1] >= self.TWOTHETA_Q_DATA:
            intensity_name: str = df_data.columns[1]
            df_data = df_data.rename(columns={df_data.columns[1]: "data: " + df_data.columns[1]})
            df_data = df_data[[df_data.columns[2], df_data.columns[0], df_data.columns[1]]]
            if df_reference is None:
                reformat_dataframe = df_data

        if df_reference is not None and df_reference.shape[1] > 1:
            df_reference.columns = header_original
            df_reference = df_reference.rename(columns={
                df_reference.columns[1]: "ref: " + df_reference.columns[1],
            })
            df_reference = df_reference[[df_reference.columns[1]]]
            reformat_dataframe = pd.concat([df_data, df_reference], axis=1)
            reformat_dataframe["Corrected: " + intensity_name] = \
                (pd.to_numeric(reformat_dataframe.iloc[:, 2], errors='coerce')
                    - pd.to_numeric(reformat_dataframe.iloc[:, 3], errors='coerce')).round(5)

        return reformat_dataframe

    def get_files_from_rasx(self, rasx_path: Path) -> list[str]:
        """Get all file names in a .rasx file.

        Args:
            rasx_path (Path): rasx raw file

        Returns:
            list[str]: list of file names contained in rasx

        Raise:
            MyError: If an input rasx has an invalid configuration
            (such as not containing the correct file), an exception will be raised.

        Note:
            The files contained in the rasx are those stored in the ContentHashList of root.xml.
            Since rasx only contains two elements, it filters by data0 and data1.

        """
        with zipfile.ZipFile(str(rasx_path), "r") as rasx:
            root_xml_files = [name for name in rasx.namelist() if name.startswith("root.")]
            contents = self.open_file(root_xml_files[0], rasx_path)
        instance = Root.from_xml(contents)
        return self.__filter_list_from_rootxml_content(instance)

    def open_file(self, file_name: str, rasx_path: Path) -> bytes | str:
        """Open a specific file stored in a .rasx file.

        Args:
            file_name (str): name of the target file
            rasx_path (Path): rasx raw file

        Returns:
            str | bytes : contents of the file specified by the argument

        """
        _, ext = os.path.splitext(file_name)
        with zipfile.ZipFile(str(rasx_path), "r") as rasx, rasx.open(file_name) as frasx:
            contents = frasx.read()

        if ext in [".rasx", ".zip"]:
            return contents
        return contents.decode("utf-8")

    def open_compressedfile_dataframe(self, file_name: str, rasx_path: Path) -> pd.DataFrame:
        """Get a text file from a compressed file (rasx) and create a data frame.

        Args:
            file_name (str): text file to be converted into a data frame
            rasx_path (Path): rasx raw file

        Returns:
            pd.DataFrame: data frame read from file

        """
        with zipfile.ZipFile(str(rasx_path), "r") as cmpf, cmpf.open(file_name) as f:
            return pd.read_csv(f, sep="\t", header=None)

    def __filter_list_from_rootxml_content(self, root_xml_obj: Root | None) -> list[str]:
        """Filter list from rootxml content.

        Args:
            root_xml_obj (Root | None): Root xml object.

        Returns:
            list[str]: Filtered list.

        Raises:
            StructuredError: If the file is formatted incorrectly.

        """
        if root_xml_obj is None or (root_xml_obj.data0 is None and root_xml_obj.data1 is None):
            err_msg = "A file with an invalid configuration has been inputted."
            raise StructuredError(err_msg)

        filtered_list = []
        filtered_list.extend(self._extract_paths_from_data(root_xml_obj.data0, "Data0"))
        filtered_list.extend(self._extract_paths_from_data(root_xml_obj.data1, "Data1"))

        if not filtered_list:
            err_msg = "A file with an invalid configuration has been inputted."
            raise StructuredError(err_msg)

        return filtered_list

    def _extract_paths_from_data(self, data_obj: Data0 | Data1 | None, data_prefix: str) -> list[str]:
        """Extract paths from a data object.

        Args:
            data_obj: The data object containing contenthashlist.
            data_prefix (str): The prefix to be added to the data paths.

        Returns:
            list[str]: A list of data paths.

        """
        if data_obj is None:
            return []

        paths = []
        for contentslist in data_obj.contenthashlist:
            dataname = contentslist.get("Name")
            if dataname:
                datapath = os.path.join(data_prefix, dataname)
                paths.append(datapath)

        return paths

    def __extract_metadata_from_xml(self, xml_data: bytes | str) -> MeasurementConditions | None:
        """Extract metadata from XML data stored in compressed files (.rasx).

        Args:
            xml_data (bytes | str): textualized XML data

        Returns:
            MeasurementConditions: stores and returns metadata from XML into the data class MeasurementConditions.

        """
        return MeasurementConditions.from_xml(xml_data)

    def _calculate_wavelength(self, header_info: MeasurementConditions) -> float:
        """Calculate wavelength.

        Args:
            header_info (MeasurementConditions): header info.

        Returns:
            float: wavelength

        """
        k_alpha1: float = float(header_info.hwconfigurations.xraygenerator.WavelengthKalpha1) \
            if header_info.hwconfigurations.xraygenerator is not None else 0
        k_alpha2: float = float(header_info.hwconfigurations.xraygenerator.WavelengthKalpha2) \
            if header_info.hwconfigurations.xraygenerator is not None else 0
        k_alpha = (2 * k_alpha1 + k_alpha2) / 3
        return float(k_alpha)

    def _calculate_2theta_rag(self, df: pd.DataFrame, header_info: MeasurementConditions) -> pd.DataFrame:
        """Calculate 2theta rag.

        Args:
            df (pd.DataFrame): dataframe.
            header_info (MeasurementConditions): header infomation.

        Returns:
            pd.DataFrame: dataframe.

        """
        df_result = df.copy()

        x_unit = header_info.scaninformation.PositionUnit
        if x_unit == 'deg':
            return np.radians(df_result[0].astype(float))
        return df_result[0].astype(float)
