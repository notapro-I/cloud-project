CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    template_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (name, version)
);

CREATE TABLE IF NOT EXISTS llm_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    model TEXT NOT NULL,
    latency_ms DOUBLE PRECISION NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    cost DOUBLE PRECISION NOT NULL,
    prompt_template_id UUID NULL REFERENCES prompt_templates(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS quality_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES llm_requests(id) ON DELETE CASCADE,
    score DOUBLE PRECISION NOT NULL CHECK (score >= 1 AND score <= 5),
    feedback TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (request_id)
);

CREATE TABLE IF NOT EXISTS quality_evaluation_queue (
    request_id UUID PRIMARY KEY REFERENCES llm_requests(id) ON DELETE CASCADE,
    sampled BOOLEAN NOT NULL DEFAULT FALSE,
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_requests_created_at ON llm_requests(created_at);
CREATE INDEX IF NOT EXISTS idx_llm_requests_model ON llm_requests(model);
CREATE INDEX IF NOT EXISTS idx_llm_requests_prompt_template_id ON llm_requests(prompt_template_id);
CREATE INDEX IF NOT EXISTS idx_quality_scores_created_at ON quality_scores(created_at);
CREATE INDEX IF NOT EXISTS idx_quality_scores_request_id ON quality_scores(request_id);
CREATE INDEX IF NOT EXISTS idx_eval_queue_processed ON quality_evaluation_queue(processed, sampled, created_at);
