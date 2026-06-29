select 
    s.comparison_id,
    p.product_key,
    c.competitor_key,
    s.product_name,
    s.competitor_name,
    s.competitor_price,
    s.our_price,
    s.price_difference,
    s.percent_difference,
    s.price_position,
    s.in_stock_competitor,
    s.date_checked,
    s.loaded_at

from {{ ref('stg_competitor_pricing') }} s

left join {{ ref('dim_product') }} p
    on s.product_name = p.product_name

left join {{ ref('dim_competitor') }} c
    on s.competitor_name = c.competitor_name