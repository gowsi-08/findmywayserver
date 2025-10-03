import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
import joblib
from flask import Flask, request, jsonify

app = Flask(__name__)

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

# --- Flask route ---
@app.route('/getlocation', methods=['POST'])
def get_location():
    data = request.get_json()
    df_test = pd.DataFrame(data)
    df_test['BSSID'] = df_test['BSSID'].astype(str).str.strip().str.lower()
    # Group all rows as a single scan
    feature = [df_test.set_index('BSSID').get('Signal Strength dBm').get(bssid, -100) for bssid in all_bssids]
    y_pred = knn.predict([feature])
    return jsonify([{"predicted": y_pred[0]}])

@app.route('/getHello', methods=['POST'])
def get():
    return jsonify([{"predicted": "Hello from Flask"}])

if __name__ == '__main__':
    app.run(debug=True)
