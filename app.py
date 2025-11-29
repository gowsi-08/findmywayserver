import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pymongo import MongoClient
import gridfs
from bson import ObjectId
from io import BytesIO
import csv
import math

app = Flask(__name__)
CORS(app)

# --- MongoDB Setup ---
mongo_url = "mongodb+srv://gowsalyaanantharaj:gowsimongodb@cluster1.zh9gr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster1"
client = MongoClient(mongo_url)
db = client['findmyway']
fs = gridfs.GridFS(db)

# --- Upload Map for a Floor ---
@app.route('/admin/upload_map/<floor>', methods=['POST'])
def upload_map(floor):
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    # Remove old map for this floor
    db.maps.delete_many({'floor': floor})
    # Save image to GridFS
    file_id = fs.put(file, filename=f'map_{floor}.png')
    db.maps.insert_one({'floor': floor, 'file_id': file_id})
    return jsonify({'success': True})

# --- Get Map Image for a Floor ---
@app.route('/admin/map_image/<floor>', methods=['GET'])
def get_map_image(floor):
    map_doc = db.maps.find_one({'floor': floor})
    if not map_doc:
        return jsonify({'error': 'Map not found'}), 404
    file_id = map_doc['file_id']
    grid_out = fs.get(file_id)
    return send_file(BytesIO(grid_out.read()), mimetype='image/png')

# --- Get All Locations for a Floor ---
@app.route('/admin/locations/<floor>', methods=['GET'])
def get_locations(floor):
    locs = list(db.locations.find({'floor': floor}))
    return jsonify([
        {'id': str(loc['_id']), 'name': loc['name'], 'x': loc['x'], 'y': loc['y']}
        for loc in locs
    ])

# --- Add or Update Locations for a Floor ---
@app.route('/admin/locations/<floor>', methods=['POST'])
def save_locations(floor):
    data = request.get_json()  # [{'name':..., 'x':..., 'y':...}, ...]
    db.locations.delete_many({'floor': floor})
    for loc in data:
        db.locations.insert_one({
            'floor': floor,
            'name': loc['name'],
            'x': loc['x'],
            'y': loc['y']
        })
    return jsonify({'success': True})

# --- Edit Location ---
@app.route('/admin/location/<loc_id>', methods=['PUT'])
def edit_location(loc_id):
    data = request.get_json()
    result = db.locations.update_one(
        {'_id': ObjectId(loc_id)},
        {'$set': {'name': data.get('name'), 'x': data.get('x'), 'y': data.get('y')}}
    )
    if result.matched_count == 0:
        return jsonify({'error': 'Location not found'}), 404
    return jsonify({'success': True})

# --- Delete Location ---
@app.route('/admin/location/<loc_id>', methods=['DELETE'])
def delete_location(loc_id):
    result = db.locations.delete_one({'_id': ObjectId(loc_id)})
    if result.deleted_count == 0:
        return jsonify({'error': 'Location not found'}), 404
    return jsonify({'success': True})

# --- Test Data Endpoint (CSV reader, no pandas) ---
@app.route('/admin/testdata', methods=['GET'])
def get_test_data():
    try:
        rows = []
        with open('test.csv', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for r in reader:
                # trim strings and normalize keys
                row = {k: (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
                # normalize BSSID and Location to lowercase strings
                if 'BSSID' in row and row['BSSID'] is not None:
                    row['BSSID'] = str(row['BSSID']).strip().lower()
                if 'Location' in row and row['Location'] is not None:
                    row['Location'] = str(row['Location']).strip().lower()
                # try to convert numeric fields where applicable
                for num_key in ['Bandwidth MHz', 'Estimated Distance m', 'Frequency MHz', 'Signal Strength dBm']:
                    if num_key in row and row[num_key] not in (None, ''):
                        try:
                            # prefer int when possible
                            if '.' in row[num_key]:
                                val = float(row[num_key])
                            else:
                                val = int(row[num_key])
                            if isinstance(val, float) and (math.isfinite(val) is False):
                                raise ValueError
                            row[num_key] = val
                        except Exception:
                            pass
                rows.append(row)
        return jsonify(rows)
    except FileNotFoundError:
        return jsonify({'error': 'test.csv not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Health Check ---
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    app.run(debug=False)
