import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

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

df_test = pd.read_csv("./test.csv")
df_test['Location'] = df_test['Location'].astype(str).str.strip().str.lower()
df_test['BSSID'] = df_test['BSSID'].astype(str).str.strip().str.lower()

grouped = df_test.groupby("Location")

X_test = []
y_test = []
for location, group in grouped:
    feature = build_feature_vector(group, all_bssids)
    X_test.append(feature)
    y_test.append(location)
y_pred = knn.predict(X_test)
print("\n🔎 Grouped scan predictions (realistic):")
for loc_true, loc_pred in zip(y_test, y_pred):
    print(f"Actual: {loc_true} → Predicted: {loc_pred}")

acc = accuracy_score(y_test, y_pred)
print(f"\n✅ Test Accuracy: {acc:.2f}")

# print("\nClassification Report:")
# print(classification_report(y_test, y_pred, zero_division=0))

# Check for missing labels in training
missing_labels = set(y_test) - set(y_train)
if missing_labels:
    print("\n⚠️ Warning: The following test locations are not present in training data and cannot be predicted:")
    for label in missing_labels:
        print(f"  - {label}")
