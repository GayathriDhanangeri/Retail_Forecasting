"""Synthetic retail dataset (seeded, reproducible). Replace with Superstore/Online Retail II if preferred.
Documented assumptions: customer_id, units_returned, promo_flag and discount_pct are SYNTHETIC.
Raw file deliberately contains dirty records (dupes, nulls, bad dates, inconsistent categories)."""
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)
dates = pd.date_range("2024-01-01", "2025-12-31")
stores = pd.DataFrame({"store_id": [f"S{i:02d}" for i in range(1, 9)],
                       "region": ["North","North","South","South","East","East","West","West"],
                       "store_factor": [1.3,0.8,1.1,0.6,1.0,0.9,1.2,0.7]})
cats = {"Electronics": (150, 400), "Furniture": (80, 300), "Clothing": (15, 80),
        "Grocery": (2, 15), "Home & Garden": (10, 90)}
prods = []
for c, (lo, hi) in cats.items():
    for k in range(8):
        prods.append({"product_id": f"{c[:3].upper()}{k+1:02d}", "category": c,
                      "unit_price": round(rng.uniform(lo, hi), 2), "pop": rng.uniform(0.3, 1.5)})
prods = pd.DataFrame(prods)
pw = (prods["pop"] / prods["pop"].sum()).values

month_f = {1:.85,2:.85,3:.95,4:1,5:1,6:1.05,7:1.05,8:1,9:.95,10:1.05,11:1.35,12:1.6}
customers = np.array([f"C{i:05d}" for i in range(1, 40001)])
rows, oid = [], 0
for d in dates:
    for _, s in stores.iterrows():
        n = rng.poisson(14 * s.store_factor * month_f[d.month] * (1.25 if d.dayofweek >= 5 else 1))
        promo_day = rng.random() < 0.2
        for _ in range(n):
            oid += 1
            p = prods.iloc[rng.choice(len(prods), p=pw)]
            promo = int(promo_day or rng.random() < 0.05)
            disc = float(rng.choice([.10,.15,.20,.30]) if promo else rng.choice([0,0,0,.05]))
            units = max(1, int(rng.poisson(2 * (1.3 if promo else 1))))
            sales = round(units * p.unit_price * (1 - disc), 2)
            ret = int(rng.binomial(units, 0.12 if p.category == "Clothing" else 0.04))
            rows.append([f"O{oid:07d}", d.strftime("%Y-%m-%d"), rng.choice(customers), s.store_id, s.region,
                         p.product_id, p.category, units, p.unit_price, disc, sales, ret, promo])
df = pd.DataFrame(rows, columns=["order_id","order_date","customer_id","store_id","region","product_id",
                                 "category","units_sold","unit_price","discount_pct","sales","units_returned","promo_flag"])
# --- inject dirt ---
n = len(df)
df.loc[rng.choice(n, 150, replace=False), "customer_id"] = np.nan
df.loc[rng.choice(n, 100, replace=False), "region"] = np.nan
df.loc[rng.choice(n, 60, replace=False), "order_date"] = "31/02/2024"
i = rng.choice(n, 80, replace=False); df.loc[i, "category"] = df.loc[i, "category"].str.upper()
i = rng.choice(n, 80, replace=False); df.loc[i, "category"] = " " + df.loc[i, "category"] + " "
df.loc[rng.choice(n, 40, replace=False), "units_sold"] = -1
df = pd.concat([df, df.sample(200, random_state=1)]).sample(frac=1, random_state=2)
Path("data/raw").mkdir(parents=True, exist_ok=True)
df.to_csv("data/raw/retail_raw.csv", index=False)
print("raw rows:", len(df))
