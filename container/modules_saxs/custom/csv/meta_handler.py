from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from rdetoolkit.models.rde2types import MetaType, RepeatedMetaType

from modules_saxs.meta_handler import MetaParser as SaxsMetaParser


class MetaParser(SaxsMetaParser):
    """Parses metadata and saves it to a specified path.

    This class is designed to parse metadata from a dictionary and save it to a specified path using
    a provided Meta object. It can handle both constant and repeated metadata.

    Attributes:
        const_meta_info (MetaType | None): Dictionary to store constant metadata.
        repeated_meta_info (RepeatedMetaType | None): Dictionary to store repeated metadata.

    """

    __mode__ = "csv"

    def __init__(self, *, metadata_def_json_path: Path | None = None, config: dict[str, str | None]):
        super().__init__(metadata_def_json_path=metadata_def_json_path, config=config)
        self.repeated_meta_info: RepeatedMetaType = defaultdict(list)

    def parse(self, data: MetaType) -> tuple[MetaType, RepeatedMetaType]:
        """Parse and extract constant and repeated metadata from the provided data."""
        self.const_meta_info = dict(data.items())
        self.repeated_meta_info = {}
        return self.const_meta_info, self.repeated_meta_info
