from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from rdetoolkit.exceptions import StructuredError

from modules_saxs.custom.csv.inputfile_handler import FileReader


RDE_CONFIG_YAML = {
    "saxs": {
        "mode": "saxs_fitting",
    }
}


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_ROOT = PROJECT_ROOT / "inputdata" / "custom"


def create_resource_paths(rawfiles):
    """read()用の最低限resource_paths"""

    return SimpleNamespace(
        rawfiles=rawfiles,
        struct=Path("data/structured"),
        other_image=Path("data/other_image"),
    )


@pytest.mark.skipif(
    not INPUT_ROOT.exists(),
    reason="test inputdata is not available",
)
def test_read_csv(mocker):
    """CSVファイルを1つ読み込める"""

    reader = FileReader(RDE_CONFIG_YAML)

    input_file = (
        INPUT_ROOT
        / "case1"
        / "inputdata"
        / "testdata-14.csv"
    )

    dummy_fitting_data = pd.DataFrame(
        {
            "q": [1.0, 2.0],
            "intensity": [10.0, 20.0],
        }
    )

    dummy_fitting_result = pd.DataFrame(
        {
            "parameter": ["test"],
            "value": [1.0],
        }
    )

    mocker.patch(
        "modules_saxs.custom.csv.inputfile_handler.main_fitting",
        return_value=(
            {
                "series_value1": dummy_fitting_data,
            },
            {
                "series_value1": dummy_fitting_result,
            },
        ),
    )

    result = list(
        reader.read(
            create_resource_paths(
                (input_file,)
            )
        )
    )

    assert len(result) == 1

    dataframe, meta, fitting_data, fitting_result = result[0]

    assert isinstance(dataframe, pd.DataFrame)
    assert isinstance(meta, dict)
    assert isinstance(fitting_data, pd.DataFrame)
    assert isinstance(fitting_result, pd.DataFrame)


def test_read_two_csv_files():

    reader = FileReader(RDE_CONFIG_YAML)

    input_file = (
        INPUT_ROOT
        / "case1"
        / "inputdata"
        / "testdata-14.csv"
    )

    with pytest.raises(StructuredError):

        list(
            reader.read(
                create_resource_paths(
                    (
                        input_file,
                        input_file,
                    )
                )
            )
        )
