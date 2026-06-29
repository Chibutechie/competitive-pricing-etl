{% snapshot snap_competitor_pricing %}

 {{
   config(
      target_schema='snapshots',
      unique_key='comparison_id',
      strategy='timestamp',
      updated_at='loaded_at'
    )
  }}

  select
    comparison_id,
    product_name,
    competitor_name,
    competitor_price,
    our_price,
    price_difference,
    percent_difference,
    price_position,
    date_checked,
    loaded_at
  from {{ ref('stg_competitor_pricing') }}

{% endsnapshot %}