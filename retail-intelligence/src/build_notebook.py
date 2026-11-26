import json
class _V4:
    @staticmethod
    def new_notebook(): return {"cells": [], "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    @staticmethod
    def new_markdown_cell(t): return {"cell_type": "markdown", "metadata": {}, "source": t, "id": None}
    @staticmethod
    def new_code_cell(t): return {"cell_type": "code", "metadata": {}, "source": t, "outputs": [], "execution_count": None, "id": None}
class nbf:
    v4 = _V4
    @staticmethod
    def write(nb, path):
        for i, c in enumerate(nb["cells"]): c["id"] = f"cell{i:03d}"
        json.dump(nb, open(path, "w"), indent=1)
nb = nbf.v4.new_notebook(); C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s)); code = lambda s: C.append(nbf.v4.new_code_cell(s))

md("# Retail Intelligence & Demand Forecasting\nRun top to bottom from the `notebooks/` folder. Steps: 1 Load/validate, 2 Clean + measures, 3 EDA, 4 SQL, 5 Forecast model.")
code("""import json, sqlite3, warnings
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib.pyplot as plt, seaborn as sns
import joblib
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
warnings.filterwarnings('ignore'); sns.set_theme(style='whitegrid')
ROOT = Path('..'); RAW = ROOT/'data/raw/retail_raw.csv'; CLEAN = ROOT/'data/clean'; MODELS = ROOT/'models'""")

md("## 1. Load & inspect raw data")
code("""raw = pd.read_csv(RAW)
print(raw.shape); display(raw.head()); display(raw.isna().sum())
print('Exact duplicates:', raw.duplicated().sum())
print(raw['category'].value_counts(dropna=False))""")

md("## 2. Validate & clean (functions, loops, conditionals)\nEvery rule logs how many rows it affected, so the cleaning is auditable.")
code("""def clean_retail(df):
    log, df = [], df.copy()
    def note(rule, before, after): log.append({'rule': rule, 'rows_affected': before - after})

    n = len(df); df = df.drop_duplicates(); note('drop exact duplicates', n, len(df))

    for col in ['category', 'store_id', 'region', 'product_id']:          # loop over text columns
        if col in df: df[col] = df[col].astype('string').str.strip()
    df['category'] = df['category'].str.title().str.replace(' & ', ' & ')   # inconsistent categories

    df['order_date'] = pd.to_datetime(df['order_date'], format='%Y-%m-%d', errors='coerce')
    n = len(df); df = df[df['order_date'].notna()]; note('invalid dates', n, len(df))

    # region missing -> recover from store_id mapping (conditional imputation)
    mapping = df.dropna(subset=['region']).drop_duplicates('store_id').set_index('store_id')['region']
    miss = df['region'].isna(); df.loc[miss, 'region'] = df.loc[miss, 'store_id'].map(mapping)
    log.append({'rule': 'region recovered from store_id', 'rows_affected': int(miss.sum())})

    df['customer_id'] = df['customer_id'].fillna('UNKNOWN')
    log.append({'rule': 'customer_id missing -> UNKNOWN', 'rows_affected': int((df['customer_id'] == 'UNKNOWN').sum())})

    n = len(df); df = df[(df['units_sold'] > 0) & (df['unit_price'] > 0) & df['discount_pct'].between(0, 1)]
    note('invalid units/price/discount', n, len(df))
    n = len(df); df = df.dropna(subset=['store_id', 'product_id', 'sales']); note('missing key fields', n, len(df))
    return df.reset_index(drop=True), pd.DataFrame(log)

df, cleaning_log = clean_retail(raw)
display(cleaning_log); print('Raw', len(raw), '-> Clean', len(df))
assert df['order_id'].is_unique and df.isna().sum().sum() == 0""")

md("### Measures")
code("""df['gross_sales']    = df['units_sold'] * df['unit_price']
df['net_sales']      = df['sales']
df['discount_amt']   = df['gross_sales'] - df['net_sales']
df['returned_value'] = df['units_returned'] * df['unit_price'] * (1 - df['discount_pct'])
df['return_rate']    = df['units_returned'] / df['units_sold']
df['year_month']     = df['order_date'].dt.to_period('M').astype(str)
df['dow']            = df['order_date'].dt.dayofweek

orders = df['order_id'].nunique()
print(f"Gross {df.gross_sales.sum():,.0f} | Net {df.net_sales.sum():,.0f} | Discount {df.discount_amt.sum():,.0f}")
print(f"Return rate (units) {df.units_returned.sum()/df.units_sold.sum():.2%} | AOV {df.net_sales.sum()/orders:,.2f}")
print('Note: each order_id is one product line in this dataset, so AOV = average line value.')
CLEAN.mkdir(exist_ok=True, parents=True)
df.to_csv(CLEAN/'retail_clean.csv', index=False)
CHECK_TOTAL = round(df.net_sales.sum(), 2)""")

md("## 3. Exploratory analysis")
code("""display(df[['units_sold','unit_price','discount_pct','net_sales']].describe(percentiles=[.05,.25,.5,.75,.95]).T)
q1, q3 = df.net_sales.quantile([.25, .75]); iqr = q3 - q1
lo, hi = q1 - 1.5*iqr, q3 + 1.5*iqr
out = df[(df.net_sales < lo) | (df.net_sales > hi)]
print(f'IQR outliers: {len(out)} rows ({len(out)/len(df):.1%}); upper fence {hi:,.0f}')
print(out.groupby('category').size())""")
code("""fig, ax = plt.subplots(2, 2, figsize=(14, 9))
m = df.groupby('year_month').net_sales.sum(); m.plot(ax=ax[0,0], marker='o'); ax[0,0].set_title('Monthly net sales (seasonality)'); ax[0,0].tick_params(axis='x', rotation=60)
df.groupby('category').net_sales.sum().sort_values().plot.barh(ax=ax[0,1], title='Net sales by category')
df.groupby('store_id').net_sales.sum().sort_values().plot.barh(ax=ax[1,0], title='Net sales by store')
sns.boxplot(data=df, x='category', y='net_sales', ax=ax[1,1]); ax[1,1].set_yscale('log'); ax[1,1].set_title('Order value distribution (log)'); ax[1,1].tick_params(axis='x', rotation=30)
plt.tight_layout(); plt.show()""")
code("""# Promotion effects
promo = df.groupby('promo_flag').agg(lines=('order_id','count'), avg_units=('units_sold','mean'), avg_net=('net_sales','mean'),
                                     avg_disc=('discount_pct','mean'), return_rate=('units_returned','sum'))
promo['return_rate'] = promo['return_rate'] / df.groupby('promo_flag').units_sold.sum()
display(promo)
# Daily-store level: is promo exposure linked to higher net sales?
ds = df.groupby(['order_date','store_id']).agg(net=('net_sales','sum'), promo_share=('promo_flag','mean')).reset_index()
print('Corr(promo share, daily store net sales):', round(ds.net.corr(ds.promo_share), 3))
df['disc_band'] = pd.cut(df.discount_pct, [-.01, 0, .05, .15, .2, .3], labels=['0%','5%','10-15%','20%','30%'])
display(df.groupby('disc_band').agg(avg_units=('units_sold','mean'), avg_net=('net_sales','mean'), lines=('order_id','count')))
print('Association only - promos were not randomized, so this is not proof of causation.')""")
code("""# weakest products and stores
prod = df.groupby(['product_id','category']).net_sales.sum().sort_values().reset_index()
display(prod.head(5)); 
print('Return rate by category'); display((df.groupby('category').units_returned.sum()/df.groupby('category').units_sold.sum()).round(3))
plt.figure(figsize=(9,4)); sns.heatmap(df.pivot_table(index='store_id', columns=df.order_date.dt.month, values='net_sales', aggfunc='sum'), cmap='YlGnBu'); plt.title('Store x month net sales'); plt.show()""")

md("## 4. SQL (SQLite)\nQueries live in `../sql/queries.sql`; they run here and in DB Browser for SQLite.")
code("""db = CLEAN/'retail.db'
con = sqlite3.connect(db)
df.assign(order_date=df.order_date.dt.strftime('%Y-%m-%d')).drop(columns=['disc_band'], errors='ignore').to_sql('sales', con, if_exists='replace', index=False)
sql_text = (ROOT/'sql/queries.sql').read_text()
for i, stmt in enumerate([s.strip() for s in sql_text.split(';') if 'SELECT' in s.upper()], 1):
    title = next((l for l in stmt.splitlines() if l.startswith('--')), f'-- Query {i}')
    print(title); display(pd.read_sql_query(stmt, con))
sql_total = pd.read_sql_query('SELECT ROUND(SUM(net_sales),2) t FROM sales', con).t[0]
assert abs(sql_total - CHECK_TOTAL) < 0.01, 'SQL total does not reconcile with pandas'
print('Reconciled: pandas == SQL ==', CHECK_TOTAL)""")

md("## 5. Forecasting daily store-level net sales\nTarget: daily net sales per store. Features use only information known in advance (calendar, planned promo exposure) plus lagged sales. Time-ordered split, no shuffling.")
code("""d = df.groupby(['order_date','store_id']).agg(net=('net_sales','sum'), promo_share=('promo_flag','mean'), avg_disc=('discount_pct','mean')).reset_index()
d = d.sort_values(['store_id','order_date'])
g = d.groupby('store_id').net
d['lag_7']  = g.shift(7); d['lag_14'] = g.shift(14); d['lag_364'] = g.shift(364)
d['roll_28'] = g.transform(lambda s: s.shift(7).rolling(28).mean())
d['dow'] = d.order_date.dt.dayofweek; d['month'] = d.order_date.dt.month; d['weekend'] = (d.dow >= 5).astype(int)
d['dow_sin'] = np.sin(2*np.pi*d.dow/7); d['dow_cos'] = np.cos(2*np.pi*d.dow/7)
d['mon_sin'] = np.sin(2*np.pi*d.month/12); d['mon_cos'] = np.cos(2*np.pi*d.month/12)
d = pd.concat([d, pd.get_dummies(d.store_id, prefix='store', dtype=int)], axis=1)
d = d.dropna(subset=['lag_7','lag_14','roll_28']).sort_values('order_date')   # lag_364 only available in year 2 -> excluded from features
FEATS = ['lag_7','lag_14','roll_28','promo_share','avg_disc','weekend','dow_sin','dow_cos','mon_sin','mon_cos'] + [c for c in d if c.startswith('store_') and c != 'store_id']
cut = d.order_date.max() - pd.Timedelta(days=90)
train, test = d[d.order_date <= cut], d[d.order_date > cut]
print('train', len(train), 'test', len(test), '| test starts', test.order_date.min().date())

def evaluate(name, y, p):
    return {'model': name, 'MAE': mean_absolute_error(y, p), 'RMSE': mean_squared_error(y, p) ** .5, 'R2': r2_score(y, p)}
res = [evaluate('Baseline: same day last week (lag_7)', test.net, test.lag_7)]
lr = LinearRegression().fit(train[FEATS], train.net); res.append(evaluate('Linear regression', test.net, lr.predict(test[FEATS])))
gs = GridSearchCV(GradientBoostingRegressor(random_state=42),
                  {'n_estimators': [100, 300], 'max_depth': [2, 3], 'learning_rate': [0.05, 0.1], 'subsample': [0.8, 1.0]},
                  cv=TimeSeriesSplit(4), scoring='neg_mean_absolute_error', n_jobs=-1).fit(train[FEATS], train.net)
best = gs.best_estimator_; res.append(evaluate('Tuned gradient boosting', test.net, best.predict(test[FEATS])))
results = pd.DataFrame(res).round(3); display(results); print('Best params:', gs.best_params_)""")
code("""test = test.assign(pred=best.predict(test[FEATS]), error=lambda x: x.pred - x.net)
fig, ax = plt.subplots(1, 2, figsize=(14, 4))
t = test.groupby('order_date')[['net','pred']].sum(); t.plot(ax=ax[0], title='Actual vs predicted (all stores, test period)')
sns.histplot(test.error, bins=40, ax=ax[1]); ax[1].set_title('Forecast error (pred - actual)'); plt.tight_layout(); plt.show()
print(f"Over-forecast (stock risk): {(test.error>0).mean():.0%} of store-days | Under-forecast (stock-out risk): {(test.error<0).mean():.0%}")
print(f"Mean over-forecast {test.error[test.error>0].mean():,.0f} | mean under-forecast {test.error[test.error<0].mean():,.0f}")
plt.figure(figsize=(7,4)); imp = pd.Series(best.feature_importances_, FEATS).sort_values(); imp.tail(10).plot.barh(title='Feature importance'); plt.show()""")
code("""MODELS.mkdir(exist_ok=True)
joblib.dump({'model': best, 'features': FEATS}, MODELS/'sales_model.joblib')
results.to_json(MODELS/'metrics.json', orient='records', indent=2)
test[['order_date','store_id','net','pred']].rename(columns={'net':'actual','pred':'predicted'}).to_csv(CLEAN/'forecast_output.csv', index=False)
print('Saved model, metrics, forecast_output.csv')""")

md("""## Limitations & inventory implications
- Synthetic data: relationships (promo lift, seasonality) were built in, so real data will be noisier and scores lower.
- Only ~2 years of history: one holiday season in the training window limits seasonal learning.
- Promo share is treated as known in advance; in practice, the promo calendar must be available at forecast time.
- Errors are in sales dollars, not units; for stocking decisions, forecast units per product and store.
- Under-forecasts cause stock-outs and lost margin; over-forecasts tie up cash and cause markdowns. Weight errors by which cost is higher per category (e.g., Grocery spoilage vs Electronics holding cost).
- Associations between discounts and sales are not causal.""")
nb['cells'] = C; nbf.write(nb, 'notebooks/01_retail_analysis.ipynb')
