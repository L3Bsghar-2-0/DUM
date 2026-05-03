import numpy as np
import os
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

data_dir = r"c:\Users\Adem\OneDrive\Desktop\DUM\data\processed"
model_dir = r"c:\Users\Adem\OneDrive\Desktop\DUM\src\extractor\models"
os.makedirs(model_dir, exist_ok=True)

def train_model():
    print("Loading data...")
    X = np.load(os.path.join(data_dir, "X_train.npy"))
    y = np.load(os.path.join(data_dir, "y_train.npy"))
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print(f"Training Multi-Output Random Forest...")
    # Constrained parameters for Edge deployment: small depth, few trees
    model = RandomForestRegressor(
        n_estimators=10, 
        max_depth=5, 
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    
    # Evaluation
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    mae_per_sensor = mean_absolute_error(y_test, predictions, multioutput='raw_values')
    
    print(f"Overall MAE: {mae:.4f}")
    print(f"MAE Power (kW): {mae_per_sensor[0]:.4f}")
    print(f"MAE Gas (Nm3/h): {mae_per_sensor[1]:.4f}")
    
    # Save model
    model_path = os.path.join(model_dir, "edge_model.pkl")
    joblib.dump(model, model_path)
    
    # Calculate and save standard deviation of errors for anomaly threshold
    errors = np.abs(y_test - predictions)
    std_errors = np.std(errors, axis=0)
    np.save(os.path.join(model_dir, "error_thresholds.npy"), std_errors)
    
    print(f"Model saved to {model_path}")
    print(f"Model size: {os.path.getsize(model_path) / 1024:.2f} KB")

if __name__ == "__main__":
    train_model()
