import os
import shutil
from typing import Union, List


def setup_inputdata_folder(
    inputdata_name: Union[str, List[str]],
    format_name: str = "rigaku",
    mode: str = "saxs",
    case_name: str = "case1",
):
    """テスト用でdataフォルダ群の作成とrawファイルの準備

    Args:
        inputdata_name (Union[str, List[str]]): rawファイル名
        format_name (str): 使用するフォーマット名（rigaku）
        mode (str): 使用するフォーマット名2（saxs, saxs_fitting, saxs_fitting_csv）
        case_name (str): case名（case1 など）
    """

    # destination: <project_root>/data
    destination_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data"
    )
    if os.path.exists(destination_path):
        shutil.rmtree(destination_path)

    os.makedirs(os.path.join(destination_path, "inputdata"), exist_ok=True)
    os.makedirs(os.path.join(destination_path, "invoice"), exist_ok=True)

    # rawfile root
    raw_root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "inputdata",
        format_name,
        case_name,
    )

    inputdata_original_path = os.path.join(raw_root, "inputdata")
    invoice_original_path = os.path.join(raw_root, "invoice")

    # inputdata コピー
    if isinstance(inputdata_name, list):
        for fname in inputdata_name:
            shutil.copy(
                os.path.join(inputdata_original_path, fname),
                os.path.join(destination_path, "inputdata"),
            )
    else:
        shutil.copy(
            os.path.join(inputdata_original_path, inputdata_name),
            os.path.join(destination_path, "inputdata"),
        )

    # invoice コピー
    shutil.copy(
        os.path.join(invoice_original_path, "invoice.json"),
        os.path.join(destination_path, "invoice"),
    )

    tasksupport_original_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "templates",
        mode,
        "tasksupport",
    )
    tasksupport_dest_path = os.path.join(destination_path, "tasksupport")
    os.makedirs(tasksupport_dest_path, exist_ok=True)

    for fname in os.listdir(tasksupport_original_path):
        src = os.path.join(tasksupport_original_path, fname)
        dst = os.path.join(tasksupport_dest_path, fname)

        if os.path.isfile(src):
            shutil.copy(src, dst)


class TestOutputCase1:
    """case1
    Rigaku SAXS測定データ（.rasファイル）の入力ケース。
    データ登録モード: インボイスモード
        "testdata-14.ras",
        "testdata-14_blank.ras",

    """

    inputdata: Union[str, List[str]] = [
        "testdata-14.ras",
        "testdata-14_blank.ras",
    ]

    def test_setup(self):
        setup_inputdata_folder(self.inputdata, format_name="rigaku", mode="saxs", case_name="case1")

    def test_raw_data(self, setup_main, data_path):
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "testdata-14.ras"))
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "testdata-14_blank.ras"))

    def test_main_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "main_image", "testdata-14.png"))

    def test_other_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "other_image", "testdata-14_raw_ref.png"))

    def test_structured(self, data_path):
        assert os.path.exists(os.path.join(data_path, "structured", "testdata-14.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "testdata-14.html"))

    def test_thumbnail(self, data_path):
        assert os.path.exists(os.path.join(data_path, "thumbnail", "testdata-14.png"))

    def test_meta(self, data_path):
        assert os.path.exists(os.path.join(data_path, "meta", "metadata.json"))


class TestOutputCase2:
    """case2
    Rigaku SAXS測定データ（.rasxファイル）の入力ケース。
    データ登録モード: インボイスモード
        "testdata.ras",
        "testdata_blank.ras",

    """

    inputdata: Union[str, List[str]] = [
        "testdata.rasx",
        "testdata_blank.rasx",
    ]

    def test_setup(self):
        setup_inputdata_folder(self.inputdata, format_name="rigaku", mode="saxs", case_name="case2")

    def test_raw_data(self, setup_main, data_path):
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "testdata.rasx"))
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "testdata_blank.rasx"))

    def test_main_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "main_image", "testdata.png"))

    def test_other_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "other_image", "testdata_raw_ref.png"))

    def test_structured(self, data_path):
        assert os.path.exists(os.path.join(data_path, "structured", "testdata.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "testdata.html"))
        assert os.path.exists(os.path.join(data_path, "structured", "MesurementConditions0.xml"))
        assert os.path.exists(os.path.join(data_path, "structured", "Profile0.txt"))

    def test_thumbnail(self, data_path):
        assert os.path.exists(os.path.join(data_path, "thumbnail", "testdata.png"))

    def test_meta(self, data_path):
        assert os.path.exists(os.path.join(data_path, "meta", "metadata.json"))


class TestOutputCase3:
    """case3
    Custom SAXS測定データ（.csvファイル）の入力ケース。
    データ登録モード: インボイスモード
        "testdata-14.csv",

    """

    inputdata: Union[str, List[str]] = [
        "testdata-14.csv",
    ]

    def test_setup(self):
        setup_inputdata_folder(self.inputdata, format_name="custom", mode="saxs_fitting_csv", case_name="case1")

    def test_raw_data(self, setup_main, data_path):
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "testdata-14.csv"))

    def test_main_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "main_image", "testdata-14_fitting.png"))

    def test_other_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "other_image", "testdata-14.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "gaussian_distribution_series_value1.png"))

    def test_structured(self, data_path):
        assert os.path.exists(os.path.join(data_path, "structured", "saxs_fitting_results.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "testdata-14_fitting.log"))
        assert os.path.exists(os.path.join(data_path, "structured", "testdata-14_fitting.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "testdata-14_raw.html"))
        assert os.path.exists(os.path.join(data_path, "structured", "testdata-14_fitting.html"))

    def test_thumbnail(self, data_path):
        assert os.path.exists(os.path.join(data_path, "thumbnail", "testdata-14_fitting.png"))

    def test_meta(self, data_path):
        assert os.path.exists(os.path.join(data_path, "meta", "metadata.json"))


class TestOutputCase4:
    """case4
    Rigaku SAXS測定データfittingバージョン（.rasファイル）の入力ケース。
    データ登録モード: インボイスモード
        "testdata-14.ras",

    """

    inputdata: Union[str, List[str]] = [
        "testdata-14.ras",
    ]

    def test_setup(self):
        setup_inputdata_folder(self.inputdata, format_name="rigaku", mode="saxs_fitting", case_name="case3")

    def test_raw_data(self, setup_main, data_path):
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "testdata-14.ras"))

    def test_main_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "main_image", "testdata-14_fitting.png"))

    def test_other_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "other_image", "testdata-14.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "gaussian_distribution_series_value1.png"))

    def test_structured(self, data_path):
        assert os.path.exists(os.path.join(data_path, "structured", "testdata-14_fitting.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "testdata-14_fitting.log"))
        assert os.path.exists(os.path.join(data_path, "structured", "saxs_fitting_results.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "testdata-14_raw.html"))
        assert os.path.exists(os.path.join(data_path, "structured", "testdata-14_fitting.html"))

    def test_thumbnail(self, data_path):
        assert os.path.exists(os.path.join(data_path, "thumbnail", "testdata-14_fitting.png"))

    def test_meta(self, data_path):
        assert os.path.exists(os.path.join(data_path, "meta", "metadata.json"))


class TestOutputCase5:
    """case5
    Rigaku SAXS測定データfittingバージョン（.rasファイル）の入力ケース。
    データ登録モード: インボイスモード
        "testdata.rasx",

    """

    inputdata: Union[str, List[str]] = [
        "testdata.rasx",
    ]

    def test_setup(self):
        setup_inputdata_folder(self.inputdata, format_name="rigaku", mode="saxs_fitting", case_name="case4")

    def test_raw_data(self, setup_main, data_path):
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "testdata.rasx"))

    def test_main_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "main_image", "testdata_fitting.png"))

    def test_other_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "other_image", "testdata.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "gaussian_distribution_series_value1.png"))

    def test_structured(self, data_path):
        assert os.path.exists(os.path.join(data_path, "structured", "testdata_fitting.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "testdata_fitting.log"))
        assert os.path.exists(os.path.join(data_path, "structured", "saxs_fitting_results.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "testdata_raw.html"))
        assert os.path.exists(os.path.join(data_path, "structured", "testdata_fitting.html"))
        assert os.path.exists(os.path.join(data_path, "structured", "MesurementConditions0.xml"))
        assert os.path.exists(os.path.join(data_path, "structured", "Profile0.txt"))

    def test_thumbnail(self, data_path):
        assert os.path.exists(os.path.join(data_path, "thumbnail", "testdata_fitting.png"))

    def test_meta(self, data_path):
        assert os.path.exists(os.path.join(data_path, "meta", "metadata.json"))
