-- Run against table `sales` in data/clean/retail.db (created in notebook section 4)

-- Q1 Top 10 products by net revenue
SELECT product_id, category, ROUND(SUM(net_sales),2) AS revenue, SUM(units_sold) AS units
FROM sales GROUP BY product_id, category ORDER BY revenue DESC LIMIT 10;

-- Q2 Bottom 10 products (weak performers)
SELECT product_id, category, ROUND(SUM(net_sales),2) AS revenue
FROM sales GROUP BY product_id, category ORDER BY revenue ASC LIMIT 10;

-- Q3 Monthly revenue and month-over-month growth
WITH m AS (SELECT strftime('%Y-%m', order_date) AS ym, SUM(net_sales) AS revenue FROM sales GROUP BY ym)
SELECT ym, ROUND(revenue,2) AS revenue,
       ROUND(100.0*(revenue - LAG(revenue) OVER (ORDER BY ym)) / LAG(revenue) OVER (ORDER BY ym), 1) AS mom_growth_pct
FROM m ORDER BY ym;

-- Q4 Regional contribution
SELECT region, ROUND(SUM(net_sales),2) AS revenue,
       ROUND(100.0*SUM(net_sales)/(SELECT SUM(net_sales) FROM sales),1) AS pct_of_total
FROM sales GROUP BY region ORDER BY revenue DESC;

-- Q5 Store ranking within region
SELECT region, store_id, ROUND(SUM(net_sales),2) AS revenue,
       RANK() OVER (PARTITION BY region ORDER BY SUM(net_sales) DESC) AS rank_in_region
FROM sales GROUP BY region, store_id;

-- Q6 Promo vs non-promo
SELECT promo_flag, COUNT(*) AS lines, ROUND(AVG(net_sales),2) AS avg_line_net, ROUND(AVG(discount_pct)*100,1) AS avg_disc_pct,
       ROUND(1.0*SUM(units_returned)/SUM(units_sold),4) AS return_rate
FROM sales GROUP BY promo_flag;

-- Q7 Repeat customers (2+ distinct orders)
WITH c AS (SELECT customer_id, COUNT(DISTINCT order_id) AS orders FROM sales WHERE customer_id <> 'UNKNOWN' GROUP BY customer_id)
SELECT CASE WHEN orders>=2 THEN 'Repeat' ELSE 'One-time' END AS segment, COUNT(*) AS customers
FROM c GROUP BY segment;

-- Q8 Reconciliation check: must match pandas total
SELECT ROUND(SUM(net_sales),2) AS total_net_sales, COUNT(*) AS rows FROM sales;
