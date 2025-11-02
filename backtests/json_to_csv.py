import json
import pandas as pd

# Load the JSON file
with open('../data/v75_candles.json', 'r') as f:
    data = json.load(f)

# Extract the candles
candles = data if isinstance(data, list) else data['candles']

# Convert to a DataFrame
df = pd.DataFrame(candles)

# Keep only what we need
df = df[['epoch', 'open', 'high', 'low', 'close']]

# Convert epoch to readable datetime
df['time'] = pd.to_datetime(df['epoch'], unit='s')

# Reorder columns
df = df[['time', 'open', 'high', 'low', 'close']]

# Save to CSV
df.to_csv('../data/v75_candles.csv', index=False)

print("✅ Saved v75_candles.csv successfully!")
print(df.head())
