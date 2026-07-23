from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from rdetoolkit import rde2util
from rdetoolkit.models.rde2types import MetaType, RepeatedMetaType

from modules_saxs.interfaces import ExtendMetaType, IMetaParser


class MetaParser(IMetaParser[ExtendMetaType]):
    """Parses metadata and saves it to a specified path.

    This class is designed to parse metadata from a dictionary and save it to a specified path using
    a provided Meta object. It can handle both constant and repeated metadata.

    Attributes:
        const_meta_info (MetaType | None): Dictionary to store constant metadata.
        repeated_meta_info (RepeatedMetaType | None): Dictionary to store repeated metadata.

    """

    def __init__(self, *, metadata_def_json_path: Path | None = None, config: dict[str, str | None]):
        self.const_meta_info: MetaType = {}
        self.repeated_meta_info: RepeatedMetaType = {}
        self.metadata_def_json_path = metadata_def_json_path
        self.config: dict = config

    def set_const_meta(
        self,
        config: dict[str, str | None],
        fitting_result: dict[str, pd.DataFrame] | None,
    ) -> None:
        """Set const meta from config and fitting data.

        Args:
            config (dict[str, str | None]): config data.
            fitting_result (dict[str, pd.DataFrame] | None): fitting data.

        """
        default_values: dict = {}
        if self._get_config_value(config, "saxs", "main_image_setting") != "":
            default_values['main_image_setting'] = self._get_config_value(config, "saxs", "main_image_setting")
        if default_values is not None:
            default_values['sample_id'] = self._get_fit_result_value(fitting_result, "sample_id", 0)
            default_values['mean'] = round(float(self._get_fit_result_value(fitting_result, "mean", 0)), 5)
            default_values['sigma'] = round(float(self._get_fit_result_value(fitting_result, "sigma", 0)), 5)
            default_values['intensity'] = round(float(self._get_fit_result_value(fitting_result, "intensity", 0)), 5)
            default_values['cost'] = round(float(self._get_fit_result_value(fitting_result, "cost", 0)), 5)
        if default_values is not None:
            self.const_meta_info.update(default_values)

    def save_meta(
        self,
        save_path: Path,
        metaobj: rde2util.Meta,
        *,
        const_meta_info: MetaType | None = None,
        repeated_meta_info: RepeatedMetaType | None = None,
    ) -> None:
        """Save parsed metadata to a file using the provided Meta object.

        Todo:
        - Not compatible with ras's multi region.

        Args:
            save_path (Path): The path where the metadata will be saved.
            metaobj (rde2util.Meta): The Meta object that handles operate of metadata.
            const_meta_info (MetaType | None): The constant metadata to save. Defaults to the
            internal const_meta_info if not provided.
            repeated_meta_info (RepeatedMetaType | None): The repeated metadata to save. Defaults
            to the internal repeated_meta_info if not provided.

        Returns:
            str: The result of the meta assignment operation.

        """
        if const_meta_info is None:
            const_meta_info = self.const_meta_info
        if repeated_meta_info is None:
            repeated_meta_info = self.repeated_meta_info
        metaobj.assign_vals(const_meta_info)
        metaobj.assign_vals(repeated_meta_info)

        metaobj.writefile(str(save_path))

    def _get_config_value(self, dictionary: Any, key_1: str, key_2: str) -> str:
        """Get config value.

        Args:
            dictionary (dict): dictionary
            key_1 (str): 1st param.
            key_2 (str): 2nd param.

        Returns:
            str: value.

        """
        if isinstance(dictionary, dict):
            value_1 = dictionary.get(key_1)
            if isinstance(value_1, dict):
                value_2 = value_1.get(key_2)
                if isinstance(value_2, str):
                    return value_2

        return ""

    def _get_fit_result_value(self, dictionary: Any, key_1: str, key_2: int) -> str | float:
        """Get fitting result value.

        Args:
            dictionary (dict): dictionary.
            key_1 (str): 1st param.
            key_2 (int): 2nd param.

        Returns:
            str | float: value.

        """
        if isinstance(dictionary, pd.DataFrame):
            value_1 = dictionary.get(key_1)
            value_2 = value_1[key_2]
            if isinstance(value_2, (str, float)):
                return value_2

        return 0
