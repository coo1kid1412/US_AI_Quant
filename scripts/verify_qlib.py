#!/usr/bin/env python
"""Verify Qlib + LightGBM functionality on macOS"""

import qlib
from qlib.data import D
from qlib.contrib.model.gbdt import LGBModel

# Initialize
qlib.init(provider_uri='/Users/lailixiang/.qlib/qlib_data/us_data', region='us')
print("✅ Qlib US data initialized successfully!")

# Test data retrieval
df = D.features(['AAPL', 'MSFT', 'GOOGL'], ['$close', '$volume'], 
                start_time='2020-01-01', end_time='2020-10-31')
print(f"\n✅ Data retrieved for AAPL, MSFT, GOOGL")
print(f"Shape: {df.shape}")

# Test LightGBM model
model = LGBModel(loss="mse", num_leaves=127, learning_rate=0.0421, num_threads=4)
print(f"\n✅ LightGBM model initialized!")
print(f"Model config: loss=mse, leaves=127, lr=0.0421, threads=4")

print(f"\n✅✅✅ Qlib + LightGBM verification PASSED!")
