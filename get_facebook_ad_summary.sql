-- Скрипт для получения детальных данных по каждой кампании
SELECT 
    date,
    account_id,
    campaign_name,
    spend,
    impressions,
    clicks,
    ctr,
    cpc,
    conversations,
    cost_per_conversation,
    is_active
FROM 
    facebook_ad_metrics
WHERE 
    date = '2025-03-01' AND
    account_id = 'act_4795321857166878'
ORDER BY 
    spend DESC;

-- Скрипт для получения сводных данных по всем кампаниям
SELECT 
    date,
    account_id,
    SUM(spend) AS total_spend,
    SUM(conversations) AS total_conversations,
    CASE 
        WHEN SUM(conversations) > 0 
        THEN ROUND(SUM(spend) / SUM(conversations), 2)
        ELSE 0 
    END AS avg_cost_per_conversation,
    COUNT(*) AS active_campaigns_count
FROM 
    facebook_ad_metrics
WHERE 
    date = '2025-03-01' AND
    account_id = 'act_4795321857166878' AND
    is_active = TRUE
GROUP BY 
    date, account_id; 