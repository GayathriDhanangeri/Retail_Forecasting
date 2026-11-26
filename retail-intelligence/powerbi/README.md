# Power BI build guide
**ETL (Power Query):** Get Data > Text/CSV `data/clean/retail_clean.csv`. Set types, add `Dim_Date` (CALENDAR), `Dim_Store` (store_id, region), `Dim_Product` (product_id, category) via Reference + Remove Duplicates.
**Model:** Star schema. Dim_Date[Date] 1:* Fact[order_date]; Dim_Store[store_id] 1:* Fact[store_id]; Dim_Product[product_id] 1:* Fact[product_id]. Mark Dim_Date as date table.

## DAX
```
Gross Sales = SUM(Fact[gross_sales])
Net Sales = SUM(Fact[net_sales])
Discount $ = [Gross Sales] - [Net Sales]
Units Sold = SUM(Fact[units_sold])
Return Rate = DIVIDE(SUM(Fact[units_returned]), [Units Sold])
Orders = DISTINCTCOUNT(Fact[order_id])
AOV = DIVIDE([Net Sales], [Orders])
Net Sales PY = CALCULATE([Net Sales], SAMEPERIODLASTYEAR(Dim_Date[Date]))
YoY % = DIVIDE([Net Sales]-[Net Sales PY],[Net Sales PY])
MoM % = VAR p = CALCULATE([Net Sales], DATEADD(Dim_Date[Date],-1,MONTH)) RETURN DIVIDE([Net Sales]-p,p)
Region Share % = DIVIDE([Net Sales], CALCULATE([Net Sales], ALL(Dim_Store[region])))
Promo Net Sales = CALCULATE([Net Sales], Fact[promo_flag]=1)
```
## Pages
1. **Overview:** KPI cards, monthly trend, region/category bars. Slicers: Date, Region, Store, Category.
2. **Products:** top/bottom N, category mix, return rate.
3. **Promotions:** promo vs non-promo, discount band vs net sales.
4. **Forecast:** import `data/clean/forecast_output.csv` (actual vs predicted).
5. **Store Detail (drill-through):** drag Store into the drill-through field.

Reconcile: the Net Sales card must equal the notebook total.
