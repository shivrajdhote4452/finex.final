-- FinEx Sprint 4: AI Financial Assistant and RAG Schema
-- Task ID: S4-DAT-01
-- Author: Shivraj Dhote
-- Date: 16 October 2026

CREATE TABLE IF NOT EXISTS document_registry (
    id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    doc_type VARCHAR(50) NOT NULL, -- 'regulatory_guide', 'annual_report', 'factsheet', 'bhavcopy_notice'
    publisher VARCHAR(100) NOT NULL, -- 'SEBI', 'RBI', 'NSE', 'AMFI'
    publishing_date DATE NOT NULL,
    reporting_period VARCHAR(50), -- e.g. 'FY26', 'Q2-2026'
    security_symbol VARCHAR(20), -- Optional ticker if company specific
    isin VARCHAR(20),
    source_url VARCHAR(500),
    content_hash VARCHAR(64) NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE', -- 'ACTIVE', 'SUPERSEDED', 'QUARANTINED'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) REFERENCES document_registry(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    section_title VARCHAR(200),
    page_number INTEGER,
    word_count INTEGER NOT NULL,
    embedding_vector JSON, -- Or pgvector if extension enabled
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_doc_chunk UNIQUE (document_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS ai_conversations (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS ai_messages (
    id VARCHAR(64) PRIMARY KEY,
    conversation_id VARCHAR(64) NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    intent_detected VARCHAR(50),
    correlation_id VARCHAR(64) NOT NULL,
    latency_ms DOUBLE PRECISION,
    model_version VARCHAR(50),
    is_fallback BOOLEAN DEFAULT FALSE,
    citation_chunk_ids JSON, -- Array of chunk IDs cited in answer
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_feedback (
    id VARCHAR(64) PRIMARY KEY,
    message_id VARCHAR(64) NOT NULL REFERENCES ai_messages(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating IN (1, -1)), -- 1 = Thumbs Up, -1 = Thumbs Down
    feedback_type VARCHAR(50), -- 'accurate', 'hallucination', 'missing_citation', 'helpful'
    comments TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_message_feedback UNIQUE (user_id, message_id)
);

CREATE TABLE IF NOT EXISTS retrieval_events (
    id VARCHAR(64) PRIMARY KEY,
    correlation_id VARCHAR(64) NOT NULL,
    conversation_id VARCHAR(64),
    query_text TEXT NOT NULL,
    filter_metadata JSON,
    top_k INTEGER NOT NULL,
    retrieved_chunk_ids JSON,
    latency_ms DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_conversations_user ON ai_conversations(user_id, is_deleted);
CREATE INDEX IF NOT EXISTS idx_ai_messages_conv ON ai_messages(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_doc ON document_chunks(document_id);
