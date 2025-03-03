-- Скрипт для создания таблицы facebook_ad_metrics
CREATE TABLE IF NOT EXISTS facebook_ad_metrics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    account_id TEXT NOT NULL,
    campaign_name TEXT NOT NULL,
    spend DECIMAL(10, 2) NOT NULL,
    impressions INTEGER NOT NULL,
    clicks INTEGER NOT NULL,
    ctr DECIMAL(5, 2) NOT NULL,
    cpc DECIMAL(10, 2) NOT NULL,
    conversations INTEGER NOT NULL,
    cost_per_conversation DECIMAL(10, 2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы для ускорения запросов
CREATE INDEX IF NOT EXISTS idx_facebook_ad_metrics_date ON facebook_ad_metrics(date);
CREATE INDEX IF NOT EXISTS idx_facebook_ad_metrics_account_id ON facebook_ad_metrics(account_id);
CREATE INDEX IF NOT EXISTS idx_facebook_ad_metrics_campaign_name ON facebook_ad_metrics(campaign_name);

-- Комментарии к таблице и полям
COMMENT ON TABLE facebook_ad_metrics IS 'Таблица для хранения метрик рекламных кампаний Facebook';
COMMENT ON COLUMN facebook_ad_metrics.date IS 'Дата, за которую собраны метрики';
COMMENT ON COLUMN facebook_ad_metrics.account_id IS 'ID рекламного аккаунта Facebook';
COMMENT ON COLUMN facebook_ad_metrics.campaign_name IS 'Название рекламной кампании';
COMMENT ON COLUMN facebook_ad_metrics.spend IS 'Расход в USD';
COMMENT ON COLUMN facebook_ad_metrics.impressions IS 'Количество показов';
COMMENT ON COLUMN facebook_ad_metrics.clicks IS 'Количество кликов';
COMMENT ON COLUMN facebook_ad_metrics.ctr IS 'CTR (Click-Through Rate) в процентах';
COMMENT ON COLUMN facebook_ad_metrics.cpc IS 'CPC (Cost Per Click) в USD';
COMMENT ON COLUMN facebook_ad_metrics.conversations IS 'Количество переписок/конверсий';
COMMENT ON COLUMN facebook_ad_metrics.cost_per_conversation IS 'Стоимость одной переписки/конверсии в USD';
COMMENT ON COLUMN facebook_ad_metrics.is_active IS 'Флаг активности кампании'; 