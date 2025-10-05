import os
import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
import joblib
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///admin.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
db = SQLAlchemy(app)

# --- Models ---
class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    x = db.Column(db.Float, nullable=False)
    y = db.Column(db.Float, nullable=False)

with app.app_context():
    db.create_all()

# --- Training (run once at startup) ---
df_train = pd.read_csv("./train.csv")
df_train['Location'] = df_train['Location'].astype(str).str.strip().str.lower()
df_train['BSSID'] = df_train['BSSID'].astype(str).str.strip().str.lower()
all_bssids = sorted(df_train['BSSID'].unique())

def build_feature_vector(group, bssid_list):
    bssid_to_signal = dict(zip(group['BSSID'], group['Signal Strength dBm']))
    return [bssid_to_signal.get(bssid, -100) for bssid in bssid_list]

X_train = []
y_train = []
for idx, row in df_train.iterrows():
    feature = [row['Signal Strength dBm'] if bssid == row['BSSID'] else -100 for bssid in all_bssids]
    X_train.append(feature)
    y_train.append(row['Location'])

knn = KNeighborsClassifier(n_neighbors=3)
knn.fit(X_train, y_train)
joblib.dump(knn, "wifi_model.pkl")
print("✅ Model trained on all scans and saved as wifi_model.pkl")

# --- Admin Endpoints ---

@app.route('/admin/upload_map', methods=['POST'])
def upload_map():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'map.png')
    file.save(filepath)
    return jsonify({'success': True, 'url': '/admin/map_image'})

@app.route('/admin/map_image', methods=['GET'])
def get_map_image():
    return send_from_directory(app.config['UPLOAD_FOLDER'], 'map.png')

@app.route('/admin/locations', methods=['POST'])
def save_locations():
    data = request.get_json()
    # data: [{'name': ..., 'x': ..., 'y': ...}, ...]
    Location.query.delete()
    for loc in data:
        db.session.add(Location(name=loc['name'], x=loc['x'], y=loc['y']))
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/locations', methods=['GET'])
def get_locations():
    locs = Location.query.all()
    return jsonify([
        {'name': loc.name, 'x': loc.x, 'y': loc.y}
        for loc in locs
    ])

# --- Existing getlocation endpoint ---
@app.route('/getlocation', methods=['POST'])
def get_location():
    data = request.get_json()
    df_test = pd.DataFrame(data)
    df_test['BSSID'] = df_test['BSSID'].astype(str).str.strip().str.lower()
    feature = [df_test.set_index('BSSID').get('Signal Strength dBm').get(bssid, -100) for bssid in all_bssids]
    y_pred = knn.predict([feature])
    return jsonify([{"predicted": y_pred[0]}])

@app.route('/getHello', methods=['POST'])
def get():
    return jsonify([{"predicted": "Hello from Flask"}])

@app.route('/admin/testdata', methods=['GET'])
def get_test_data():
    # Return test data from test.csv as JSON
    try:
        df_test = pd.read_csv('test.csv')
        # Optionally preprocess as in training
        df_test['BSSID'] = df_test['BSSID'].astype(str).str.strip().str.lower()
        if 'Location' in df_test.columns:
            df_test['Location'] = df_test['Location'].astype(str).str.strip().str.lower()
        # Convert to list of dicts
        data = df_test.to_dict(orient='records')
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

# REMOVE app.run() for production!

# if __name__ == '__main__':
#     app.run(debug=True, host='0.0.0.0', port=5000)
