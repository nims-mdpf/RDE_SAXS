from pathlib import Path
from types import SimpleNamespace

import pytest

from rdetoolkit.exceptions import StructuredError

from modules_saxs.rigaku.ras.inputfile_handler import FileReader


RDE_CONFIG_YAML = {
    "saxs": {
        "mode": "saxs",
    }
}

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_ROOT = PROJECT_ROOT / "inputdata" / "rigaku"


@pytest.mark.skipif(
    not INPUT_ROOT.exists(),
    reason="test inputdata is not available",
)
def create_resource_paths(rawfiles):
    """read()用の最低限resource_paths"""

    return SimpleNamespace(
        rawfiles=rawfiles,
    )


def test_read_single_ras():
    """1ファイル入力"""

    reader = FileReader(RDE_CONFIG_YAML)

    input_file = (
        INPUT_ROOT
        / "case3"
        / "inputdata"
        / "testdata-14.ras"
    )

    result = list(
        reader.read(
            create_resource_paths((input_file,))
        )
    )

    assert len(result) > 0


def test_read_ras_with_reference():
    """raw/referenceの2ファイル入力"""

    reader = FileReader(RDE_CONFIG_YAML)

    input_dir = (
        INPUT_ROOT
        / "case1"
        / "inputdata"
    )

    result = list(
        reader.read(
            create_resource_paths(
                (
                    input_dir / "testdata-14.ras",
                    input_dir / "testdata-14_blank.ras",
                )
            )
        )
    )

    assert len(result) > 0


def test_read_three_files():
    """3ファイル以上は許可しない"""

    reader = FileReader(RDE_CONFIG_YAML)

    input_file = (
        INPUT_ROOT
        / "case3"
        / "inputdata"
        / "testdata-14.ras"
    )

    with pytest.raises(StructuredError) as exc:

        list(
            reader.read(
                create_resource_paths(
                    (
                        input_file,
                        input_file,
                        input_file,
                    )
                )
            )
        )

    assert str(exc.value) == "Only one or two raw files are supported."


def test_read_same_stem_length(tmp_path):
    """stem長が同じファイルは禁止"""

    reader = FileReader(RDE_CONFIG_YAML)

    src = (
        INPUT_ROOT
        / "case3"
        / "inputdata"
        / "testdata-14.ras"
    )

    file1 = tmp_path / "aaaa.ras"
    file2 = tmp_path / "bbbb.ras"

    file1.write_bytes(src.read_bytes())
    file2.write_bytes(src.read_bytes())

    with pytest.raises(StructuredError) as exc:

        list(
            reader.read(
                create_resource_paths(
                    (
                        file1,
                        file2,
                    )
                )
            )
        )

    assert str(exc.value) == "Files of the same length are not permitted."
