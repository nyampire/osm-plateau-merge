import json
import sys
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

def load_geojson(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

def save_geojson(filename, data):
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Saved to {filename}")
    except Exception as e:
        print(f"Error writing file: {e}")

def process_centroids(input_file, output_file):
    # GeoJSONファイルを読み込む
    geojson = load_geojson(input_file)

    # 新しいフィーチャーコレクションを作成
    centroid_collection = {
        "type": "FeatureCollection",
        "features": []
    }

    # 属性のリストを保持するセット
    all_attributes = set()

    # 各フィーチャーに対して処理を行う
    for feature in geojson['features']:
        geom = shape(feature['geometry'])
        if geom.geom_type in ['Polygon', 'MultiPolygon']:
            # ポリゴンの重心を計算
            centroid = geom.centroid

            # 新しいフィーチャーを作成
            new_feature = {
                "type": "Feature",
                "geometry": mapping(centroid),
                "properties": feature['properties']
            }

            # id属性を削除 (機能1)
            if 'id' in new_feature:
                del new_feature['id']

            # 属性をリストに追加 (機能2の準備)
            all_attributes.update(new_feature['properties'].keys())

            # 重心フィーチャーを新しいコレクションに追加
            centroid_collection['features'].append(new_feature)

    # 結果を保存
    save_geojson(output_file, centroid_collection)

    # 変換されたオブジェクトの属性をリスト化して表示 (機能2)
    print("変換されたオブジェクトの属性リスト:")
    for attr in sorted(all_attributes):
        print(f"- {attr}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <input_file.geojson> <output_file.geojson>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    process_centroids(input_file, output_file)
