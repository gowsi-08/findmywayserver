import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pymongo import MongoClient
import gridfs
from bson import ObjectId
from io import BytesIO
import pandas as pd

app = Flask(__name__)
CORS(app)

# --- MongoDB Setup ---
mongo_url = "mongodb+srv://selva:selva2004@cluster0.wo0nx.mongodb.net/"
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

# --- Test Data Endpoint ---
@app.route('/admin/testdata', methods=['GET'])
def get_test_data():
    try:
        df_test = pd.read_csv('test.csv')
        df_test['BSSID'] = df_test['BSSID'].astype(str).str.strip().str.lower()
        if 'Location' in df_test.columns:
            df_test['Location'] = df_test['Location'].astype(str).str.strip().str.lower()
        data = df_test.to_dict(orient='records')
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

# --- Health Check ---
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    app.run(debug=False)
