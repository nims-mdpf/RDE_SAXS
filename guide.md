# SAXS用テンプレート

## 概要

SAXS（小角X線散乱）をご利用の方に適したデータセットテンプレートです。以下のバリエーションが提供されています。

- DT0026
  - Rigaku SAXS
- DT0027
  - Rigaku SAXS_fitting
- DT0028
  - Custom SAXS_fitting_CSV

本テンプレートは、Rigaku社のXRD装置から出力されるSAXSデータ（.ras / .rasx）を対象としたデータ処理システムです。Rigaku社の`.ras`、`.rasx`形式、およびSAXSデータセットから出力した`.csv`形式に対応しています。

SAXSの専門家によって監修されたメタ情報を入力ファイルから自動的にRDEが抽出します。また、測定データの可視化や、テンプレートに応じて差分進化アルゴリズム（Differential Evolution, DE）を用いたフィッティング解析を実行します。

### 主な機能

* Rigaku XRD装置 SAXSデータ（`.ras`、`.rasx`）およびSAXSデータセット出力のCSV形式データの登録
* 測定条件・メタ情報の自動抽出
* SAXSプロットおよびHTML(plotlyのグラフ)による可視化
* バックグラウンドデータとの比較表示（DT0026）
* Differential Evolution（DE）によるフィッティング解析（DT0027・DT0028）
* SmartTable対応
* マジックネーム対応（データ名を`${filename}`とすることでファイル名をデータ名へマッピング）

---

# メタ情報

* [メタ情報](docs/requirement_analysis/要件定義_SAXS.xlsx)

---

# 基本情報

## コンテナ情報

* 【コンテナ名】rdecontreg.azurecr.io/nims/mdpf_shared/nims_mdpf_shared_saxs:v1.0

## テンプレート情報

### DT0026

* 【データセットテンプレートID】NIMS_DT0026_SAXS_v1.0
* 【データセットテンプレート名日本語】SAXS データセットテンプレート
* 【データセットテンプレート名英語】SAXS dataset-template
* 【データセットテンプレートの説明】Rigaku製XRD装置のSAXSデータをご利用の方向けのテンプレートです。.rasおよび.rasx形式の測定データからメタ情報を自動抽出し、測定データの可視化を行います。バックグラウンド（リファレンス）データとの比較表示にも対応しています。
* 【バージョン】1.0
* 【データセット種別】加工・計測レシピ型
* 【データ構造化】あり（システム上「あり」を選択）
* 【取り扱い事業】NIMS研究および共同研究プロジェクト（PROGRAM）
* 【装置名】（なし。装置情報を紐づける場合は本テンプレートを複製して設定してください。）

### DT0027

* 【データセットテンプレートID】NIMS_DT0027_SAXS_fitting_v1.0
* 【データセットテンプレート名日本語】SAXS Fitting データセットテンプレート
* 【データセットテンプレート名英語】SAXS Fitting dataset-template
* 【データセットテンプレートの説明】Rigaku製XRD装置のSAXSデータを対象にフィッティング解析を実施するテンプレートです。.rasまたは.rasx形式のデータからメタ情報を抽出し、Differential Evolution（DE）によるフィッティング解析結果を出力します。
* 【バージョン】1.0
* 【データセット種別】加工・計測レシピ型
* 【データ構造化】あり（システム上「あり」を選択）
* 【取り扱い事業】NIMS研究および共同研究プロジェクト（PROGRAM）
* 【装置名】（なし。装置情報を紐づける場合は本テンプレートを複製して設定してください。）

### DT0028

* 【データセットテンプレートID】NIMS_DT0028_SAXS_fitting_CSV_v1.0
* 【データセットテンプレート名日本語】SAXS Fitting CSV データセットテンプレート
* 【データセットテンプレート名英語】SAXS Fitting CSV dataset-template
* 【データセットテンプレートの説明】SAXSデータセットから出力されたCSV形式データを入力とし、Differential Evolution（DE）によるフィッティング解析を実施するテンプレートです。
* 【バージョン】1.0
* 【データセット種別】加工・計測レシピ型
* 【データ構造化】あり（システム上「あり」を選択）
* 【取り扱い事業】NIMS研究および共同研究プロジェクト（PROGRAM）
* 【装置名】（なし。装置情報を紐づける場合は本テンプレートを複製して設定してください。）

---

### データ登録方法
- 送り状画面をひらいて入力ファイルに関する情報を入力する
- 「登録ファイル」欄に登録したいファイルをドラッグアンドドロップする。
  - 複数のファイルを入力し一度に複数のデータを登録することが可能。
  - 複数のファイルを入力する場合は、「データ名」に「${filename}」と入力し「データ名」に入力ファイル名をマッピングさせることができる
- 「登録開始」ボタンを押して（確認画面経由で）登録を開始する

## 構成

### レポジトリ構成

```
saxs
├── README.md
├── container
│   ├── Dockerfile
│   ├── data (入出力データ)
│   ├── main.py
│   ├──modules_saxs (SAXS向けソースコード)
│   │   ├── __init__.py
│   │   ├── custom
│   │   │   ├── __init__.py
│   │   │   └── csv
│   │   │       ├── __init__.py
│   │   │       ├── inputfile_handler.py (入力ファイル読み込み)
│   │   │       └── meta_handler.py (メタデータ解析)
│   │   ├── rigaku
│   │   │   ├── __init__.py
│   │   │   ├── ras
│   │   │   │   ├── __init__.py
│   │   │   │   ├── inputfile_handler.py (入力ファイル読み込み)
│   │   │   │   └── meta_handler.py (メタデータ解析)
│   │   │   └── rasx
│   │   │       ├── __init__.py
│   │   │       ├── inputfile_handler.py (入力ファイル読み込み)
│   │   │       └── meta_handler.py (メタデータ解析)
│   │   ├── datasets_process.py
│   │   ├── factory.py (設定ファイル、使用クラス取得)
│   │   ├── graph_handler.py (グラフ描画)
│   │   ├── inputfile_handler.py (入力ファイル読み込み)
│   │   ├── interfaces.py
│   │   ├── invoice_handler.py
│   │   ├── meta_handler.py (メタデータ解析)
│   │   ├── models.py
│   │   └── structured_handler.py (構造化データ解析)
│   ├──modules_tool
│   │   ├── __init__.py
│   │   ├── csv2graph.py
│   │   └── saxs_fit_de.py
│   ├── pip.conf
│   ├── pyproject.toml
│   ├── requirements-test.txt
│   ├── requirements.txt
│   └── tests (テストコード)
├── docs (ドキュメント)
│   ├── manual
│   │   ├── RDEDatasetTemplateSheet_RDE_SAXS_fitting_CSV.xlsx
│   │   ├── RDEDatasetTemplateSheet_RDE_SAXS_fitting.xlsx
│   │   ├── RDEDatasetTemplateSheet_RDE_SAXS.xlsx
│   │   └── manual.md
│   └── requirement_analysis
│       └── 要件定義_SAXS.xlsx
├── inputdata (サンプルデータ)
│   ├── rigaku (rigaku向け)
│   └── custom (custom向け)
└── templates (テンプレート群)
    ├── saxs (SAXS向けテンプレート)
    │   ├── batch.yaml
    │   ├── catalog.schema.json
    │   ├── invoice.schema.json
    │   ├── jobs.template.yaml
    │   ├── metadata-def.json
    │   └── tasksupport
    │       ├── invoice.schema.json
    │       ├── metadata-def.json
    │       ├── metadata-def_rigaku_ras.json
    │       ├── metadata-def_rigaku_rasx.json
    │       └── rdeconfig.yaml
    ├── saxs_fitting (SAXS_fitting向けテンプレート)
    │   ├── batch.yaml
    │   ├── catalog.schema.json
    │   ├── invoice.schema.json
    │   ├── jobs.template.yaml
    │   ├── metadata-def.json
    │   └── tasksupport
    │       ├── invoice.schema.json
    │       ├── metadata-def.json
    │       ├── metadata-def_rigaku_ras.json
    │       ├── metadata-def_rigaku_rasx.json
    │       └── rdeconfig.yaml
    └── saxs_fitting_csv (SAXS_fitting_csv向けテンプレート)
        ├── batch.yaml
        ├── catalog.schema.json
        ├── invoice.schema.json
        ├── jobs.template.yaml
        ├── metadata-def.json
        └── tasksupport
            ├── invoice.schema.json
            ├── metadata-def.json
            ├── metadata-def_custom_csv.json
            └── rdeconfig.yaml
```

### 動作環境ファイル入出力
- DT0026
```
container/data
├── attachment
├── inputdata
│   ├── testdata-14.ras
│   └── testdata-14_blank.ras
├── invoice
│   └── invoice.json
├── invoice_patch
├── logs
├── main_image
│   └── testdata-14.png
├── meta
│   └── metadata.json
├── nonshared_raw
│   ├── testdata-14.ras
│   └── testdata-14_blank.ras
├── other_image
│   └── testdata-14_raw_ref.png
├── raw
├── structured
│   ├── testdata-14.csv
│   └── testdata-14.html
├── tasksupport
│   ├── invoice.schema.json
│   ├── metadata-def.json
│   ├── metadata-def_rigaku_ras.json
│   ├── metadata-def_rigaku_rasx.json
│   └── rdeconfig.yaml
├── temp
└── thumbnail
    └── testdata-14.png

```

- DT0027
```
container/data
├── attachment
├── inputdata
│   └── testdata-14.ras
├── invoice
│   └── invoice.json
├── invoice_patch
├── logs
├── main_image
│   └── testdata-14_fitting.png
├── meta
│   └── metadata.json
├── nonshared_raw
│   └── testdata-14.ras
├── other_image
│   ├── gaussian_distribution_series_value1.png
│   └── testdata-14.png
├── raw
├── structured
│   ├── saxs_fitting_results.csv
│   ├── testdata-14_fitting.csv
│   ├── testdata-14_fitting.html
│   ├── testdata-14_fitting.log
│   └── testdata-14_raw.html
├── tasksupport
│   ├── invoice.schema.json
│   ├── metadata-def.json
│   ├── metadata-def_rigaku_ras.json
│   ├── metadata-def_rigaku_rasx.json
│   └── rdeconfig.yaml
├── temp
└── thumbnail
    └── testdata-14_fitting.png

```

- DT0028
```
container/data
├── attachment
├── inputdata
│   └── testdata-14.csv
├── invoice
│   └── invoice.json
├── invoice_patch
├── logs
│   ├── rdesys_20260630_132222.log
│   └── rdesys_20260630_132319.log
├── main_image
│   └── testdata-14_fitting.png
├── meta
│   └── metadata.json
├── nonshared_raw
│   └── testdata-14.csv
├── other_image
│   ├── gaussian_distribution_series_value1.png
│   └── testdata-14.png
├── raw
├── structured
│   ├── saxs_fitting_results.csv
│   ├── testdata-14_fitting.csv
│   ├── testdata-14_fitting.html
│   ├── testdata-14_fitting.log
│   └── testdata-14_raw.html
├── tasksupport
│   ├── invoice.schema.json
│   ├── metadata-def.json
│   ├── metadata-def_custom_csv.json
│   └── rdeconfig.yaml
├── temp
└── thumbnail
    └── testdata-14_fitting.png

```

## データ閲覧
- データ一覧画面を開く。
- ギャラリー表示タブでは１データがタイル状に並べられている。データ名をクリックして詳細を閲覧する。
- ツリー表示タブではタクソノミーにしたがってデータを階層表示する。データ名をクリックして詳細を閲覧する。

### 動作環境
- Python: 3.12
- RDEToolKit: 1.7.0