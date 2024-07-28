# Plateauタグ・コンフレーション

このリポジトリには、国土交通省 [Plateauプロジェクト](https://www.mlit.go.jp/plateau/)で配布されているデータから抽出されたタグ情報（例: eleなど）を、OpenStreetMap(OSM)にすでに入力されているbuildingポリゴンデータと合成させるためのスクリプト集が含まれています。

## スクリプト

1. `start-processing.py`: ワークフロー全体を制御するメインスクリプト
2. `_merge-building-addrs.py`: OSM由来の建物外形データと、Plateau由来のタグ情報をマージするスクリプト
3. `_osm-polygon-centroid.py`: GeoJSON形式のポリゴンの重心を計算するスクリプト

## 機能

- メッシュコードに基づいてOverpass Turbo APIから建物外形データをダウンロード
- OSM形式のPlateauデータをGeoJSON形式に変換
- Plateauデータのポリゴンの重心を計算
- Plateauデータをもとにした重心データから、指定された属性を削除
  削除対象となる属性：
  - ref:MLIT_PLATEAU
  - id (OSMからGeoJSONに変換する際に自動的に含まれるタグ。OSMにおけるオブジェクトのIDとは別)
  - building（値が"yes"の場合のみ削除）
- OSM由来の建物の外形データとPlateau由来のタグ情報をマージ
- 処理済みのGeoJSONをOSM形式に再変換

## 必要条件

- Python 3.9以上
- 必要なPythonパッケージ：
  - pyproj
  - requests
  - shapely
- 外部ツール：
  - [osmtogeojson](https://github.com/tyrasd/osmtogeojson)
  - [geojsontoosm](https://github.com/tyrasd/geojsontoosm)

## 事前準備

必要なPythonパッケージをインストールします：

```
pip install pyproj requests shapely
```

## 使用方法

1. メイン処理スクリプトを実行：

```
python3.9 start-processing.py <input.osm>
```

`<input.osm>`を入力OSMファイルのパスに置き換えてください。入力ファイル名には8桁のメッシュコードが含まれている必要があります。

2. スクリプトは`work`ディレクトリを作成し、中間ファイルをそこに保存します。
3. 最終的にマージされたファイルは、スクリプトを実行したディレクトリに`<base_name>_merged.osm`として保存されます。

## 入力ファイルについて

- 入力ファイルは、yuuhayashi氏が作成したcitygml-osmスクリプトの1st処理で生成されたOSMファイルを利用してください。詳細は以下のURLを参照ください：
  https://github.com/yuuhayashi/citygml-osm
- あるいは、yuuhayashi氏が処理を行ったあとのファイルを以下のURLから入手し、入力ファイルとして利用することができます：
  http://surveyor.mydns.jp/task-bldg/city

## 重要な注意事項

このスクリプトで処理した.osmファイルのアップロードは、[OSMのインポートガイドライン](https://wiki.openstreetmap.org/wiki/Import/Guidelines)、および[機械的編集の行動規則](https://wiki.openstreetmap.org/wiki/Automated_Edits_code_of_conduct)に沿って利用し、コミュニティでの議論が完了するまで行わないでください。
2024年7月現在、まだ議論は開始されていません。

## ワークフロー

1. 入力ファイル名からメッシュコードを抽出
2. メッシュコードに基づいてバウンディングボックスを計算
3. Overpass Turbo APIから建物データをダウンロード
4. 入力OSMをGeoJSONに変換
5. GeoJSONのポリゴンの重心を計算
6. 重心化されたGeoJSONから指定された属性を削除
7. 修正された重心GeoJSONをOSMに再変換
8. 建物データと重心データをマージ

## 注意事項

- スクリプトを実行する前に、必要なPythonパッケージと外部ツールがすべてインストールされていることを確認してください。
- スクリプトは入力ファイルに特定の命名規則（8桁のメッシュコードを含む）を想定しています。
- 中間ファイルは`work`ディレクトリに保存され、デバッグや追加の分析に使用できます。

## ライセンス

MIT

ただし、プログラムの生成にはClaude 3.5 Sonnetを利用しているため、将来的に修正される可能性があります。
また、_merge-building-addrs.pyについてはbalrog-kunのスクリプトをベースにしています。
https://gist.github.com/balrog-kun/4241509
