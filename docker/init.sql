-- Runs automatically on first Postgres startup

-- Enable pgvector extension (used in Step 5 for RAG embeddings)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create separate DB for Langfuse
CREATE DATABASE langfuse;
