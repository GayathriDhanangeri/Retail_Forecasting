# Retail Intelligence & Demand Forecasting
Run: `pip install -r requirements.txt` > `python src/generate_data.py` (or drop a real CSV in data/raw) > run `notebooks/01_retail_analysis.ipynb` top to bottom.
Outputs: `data/clean/retail_clean.csv`, `data/clean/retail.db`, `models/sales_model.joblib`, `models/metrics.json`, `data/clean/forecast_output.csv`. Then build Power BI per `powerbi/README.md`.
## Assumptions
Synthetic: customer_id, units_returned, promo_flag, discount_pct, and all transactions (seed 42). Net sales = sales as recorded (already after discount); gross = units*unit_price.
