import sys
import os
import subprocess
import re
from urllib.parse import quote
from pyproj import Proj, transform
import requests
import json

# スクリプトのディレクトリを取得
script_dir = os.path.dirname(os.path.abspath(__file__))

def calculate_bbox(mesh_code):
    # JGD2000 (EPSG:4612) から平面直角座標系 (EPSG:2451) への変換を設定
    jgd2000 = Proj(init='epsg:4612')
    plane = Proj(init='epsg:2451')

    # メッシュコードから緯度経度を計算
    lat = int(mesh_code[:2]) / 1.5
    lon = int(mesh_code[2:4]) + 100

    # 2次メッシュ
    lat += int(mesh_code[4:5]) * 5 / 60
    lon += int(mesh_code[5:6]) * 7.5 / 60

    # 3次メッシュ
    lat += int(mesh_code[6:7]) * 30 / 3600
    lon += int(mesh_code[7:8]) * 45 / 3600

    # 3次メッシュの大きさ（約1km四方）を考慮
    lat_max = lat + 30 / 3600
    lon_max = lon + 45 / 3600

    return lon, lat, lon_max, lat_max

def extract_mesh_code(filename):
    # ファイル名から8桁の数字を抽出
    match = re.search(r'(\d{8})', filename)
    if match:
        return match.group(1)
    return None

def get_overpass_data(min_lat, min_lon, max_lat, max_lon):
    overpass_url = "https://overpass.osm.jp/api/interpreter"
    overpass_query = f"""
    [out:xml][timeout:25];
    (
      way["building"]({min_lat},{min_lon},{max_lat},{max_lon});
      relation["building"]({min_lat},{min_lon},{max_lat},{max_lon});
    );
    (._;>;);
    out meta;
    """
    response = requests.post(overpass_url, data={"data": overpass_query})
    response.raise_for_status()
    return response.text

def main():
    if len(sys.argv) != 2 or not sys.argv[1].endswith('.osm'):
        print("Usage: python3.9 start-processing.py <input.osm>")
        sys.exit(1)

    input_file = sys.argv[1]
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    if '/' in base_name:
        base_name = base_name.split('/')[-1]

    print(f"Input file: {input_file}")
    print(f"Base name: {base_name}")

    # カレントディレクトリに 'work' ディレクトリを作成
    work_dir = 'work'
    os.makedirs(work_dir, exist_ok=True)

    mesh_code = extract_mesh_code(base_name)
    if not mesh_code:
        print("Error: Could not extract mesh code from filename.")
        sys.exit(1)

    print(f"Extracted mesh code: {mesh_code}")

    min_lon, min_lat, max_lon, max_lat = calculate_bbox(mesh_code)

    print(f"Boundary box: {min_lon},{min_lat},{max_lon},{max_lat}")

    # Overpass Turboを使用して建物データをダウンロード
    print("Downloading building data from Overpass Turbo...")
    overpass_data = get_overpass_data(min_lat, min_lon, max_lat, max_lon)
    output_file = os.path.join(work_dir, f"{base_name}_buildings.osm")

    print(f"Creating file: {output_file}")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(overpass_data)

    # OSMファイルをGeoJSONに変換
    print("Converting .osm to GeoJSON...")
    result = subprocess.run(["osmtogeojson", input_file], capture_output=True, text=True, check=True)
    geojson_data = json.loads(result.stdout)

    geojson_file = os.path.join(work_dir, f"{base_name}.geojson")
    with open(geojson_file, 'w', encoding='utf-8') as f:
        json.dump(geojson_data, f)

    # ファイルが正しく書き込まれたか確認
    if os.path.exists(geojson_file) and os.path.getsize(geojson_file) > 0:
        print(f"GeoJSON file successfully created: {geojson_file}")
    else:
        print("Error: GeoJSON file was not created or is empty.")
        sys.exit(1)

    # GeoJSONをcentroid
    print("Centroiding GeoJSON...")
    centroid_geojson = os.path.join(work_dir, f"{base_name}_centroid.geojson")
    centroid_script = os.path.join(script_dir, "_osm-polygon-centroid.py")
    print(f"Running: python3.9 {centroid_script} {geojson_file} {centroid_geojson}")
    subprocess.run(["python3.9", centroid_script, geojson_file, centroid_geojson], check=True)

    # centroidされたGeoJSONから特定の属性を削除する処理を追加
    print("Removing specified attributes from centroided GeoJSON...")
    with open(centroid_geojson, 'r') as f:
        geojson_data = json.load(f)

    attributes_to_remove = ["id", "ref:MLIT_PLATEAU"]
    modified_features = 0

    for feature in geojson_data['features']:
        properties = feature.get('properties', {})
        for attr in attributes_to_remove:
            if attr in properties:
                del properties[attr]
                modified_features += 1

        # "building"属性が"yes"の場合のみ削除
        if properties.get("building") == "yes":
            del properties["building"]
            modified_features += 1

    # 修正したGeoJSONを保存
    modified_centroid_geojson = os.path.join(work_dir, f"{base_name}_modified_centroid.geojson")
    with open(modified_centroid_geojson, 'w') as f:
        json.dump(geojson_data, f)

    print(f"Modified {modified_features} features in the centroided GeoJSON file.")
    print(f"Modified centroided GeoJSON saved as: {modified_centroid_geojson}")

    # 修正されたcentroidされたGeoJSONを.osmに変換
    print("Converting modified centroided GeoJSON back to .osm...")
    centroid_osm = os.path.join(work_dir, f"{base_name}_centroid.osm")

    try:
        result = subprocess.run(["geojsontoosm", modified_centroid_geojson], capture_output=True, text=True, check=True)
        with open(centroid_osm, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
        print(f"Successfully converted {modified_centroid_geojson} to {centroid_osm}")
    except subprocess.CalledProcessError as e:
        print(f"Error converting GeoJSON to OSM: {e}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)


    # ファイルの存在確認
    buildings_file = os.path.join(work_dir, f"{base_name}_buildings.osm")

    if not os.path.exists(buildings_file):
        print(f"Error: {buildings_file} does not exist.")
        sys.exit(1)

    if not os.path.exists(centroid_osm):
        print(f"Error: {centroid_osm} does not exist.")
        sys.exit(1)

    # マージ
    print("Merging centroid data with building data...")
    merged_file = os.path.join(script_dir, f"{base_name}_merged.osm")
    try:
        subprocess.run(["python3.9", os.path.join(script_dir, "_merge-building-addrs.py"), buildings_file, centroid_osm, "-o", merged_file], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error merging files: {e}")
        sys.exit(1)

    print("Process completed.")
    print(f"Final merged file: {merged_file}")
    print(f"Intermediate files are stored in the '{work_dir}' directory.")

    print("\nOverpass Turbo query coordinates:")
    print(f"min_lat: {min_lat}")
    print(f"min_lon: {min_lon}")
    print(f"max_lat: {max_lat}")
    print(f"max_lon: {max_lon}")

if __name__ == "__main__":
    main()
