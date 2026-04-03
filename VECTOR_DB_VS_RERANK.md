# Vector DB vs Reranking — Complete Guide

> How data flows through pgvector and the reranker in this project.

---

## TABLE OF CONTENTS

1. [What is a Vector DB](#1-what-is-a-vector-db)
2. [What is Reranking](#2-what-is-reranking)
3. [Key Difference](#3-key-difference)
4. [How Data Flows Into pgvector](#4-how-data-flows-into-pgvector)
5. [How Data Flows Out of pgvector](#5-how-data-flows-out-of-pgvector)
6. [How Data Flows Through Reranker](#6-how-data-flows-through-reranker)
7. [Complete End-to-End Flow](#7-complete-end-to-end-flow)
8. [Why You Need Both](#8-why-you-need-both)

---

## 1. WHAT IS A VECTOR DB

A database that stores text as **numbers (vectors)** and finds similar text using **math** instead of keyword matching.

### Normal DB search (keyword):
```
Query:  "Apple profit"
Finds:  rows containing words "Apple" AND "profit"
Misses: "AAPL net income was $99.8B"  ← no word match but same meaning
```

### Vector DB search (semantic):
```
Query:  "Apple profit"
Embed:  [0.021, -0.14, 0.87, ...]
Finds:  vectors CLOSEST in meaning — catches "AAPL net income" ✅
```

### In your project — pgvector

Regular PostgreSQL with the `pgvector` extension installed.
Adds a `vector` column type and the `<=>` cosine distance operator.

```sql
-- Your table
CREATE TABLE document_chunks (
    id         SERIAL PRIMARY KEY,
    source     TEXT,                      -- filename
    page       INT,                       -- page number
    text       TEXT,                      -- original chunk text
    embedding  vector(1024),              -- 1024 float numbers
    chunk_index INT,
    doc_type   TEXT
);
```

---

## 2. WHAT IS RERANKING

A second model that reads **query + chunk together** and gives a precise relevance score.

```
Embedding:   reads texts separately → compares vectors
Reranking:   reads query + chunk as ONE input → outputs score
```

Your reranker: `ms-marco-MiniLM-L-12-v2`
- Runs locally on CPU
- ~33MB — downloaded once by flashrank
- No API key, no network call

---

## 3. KEY DIFFERENCE

| | Vector DB (pgvector) | Reranker (ms-marco) |
|--|---------------------|---------------------|
| **What it does** | Finds similar vectors | Scores how well chunk answers query |
| **How** | Math: cosine distance | Neural network reads both together |
| **Speed** | Very fast (vector math) | Slower (neural network per pair) |
| **Accuracy** | Approximate | Precise |
| **Scale** | Entire DB (thousands of chunks) | Small set (20 candidates only) |
| **Model** | nvidia/nv-embedqa-e5-v5 | ms-marco-MiniLM-L-12-v2 |
| **Where runs** | PostgreSQL + NVIDIA API | Local CPU |

---

## 4. HOW DATA FLOWS INTO pgvector

### Step 1 — PDF loaded, split into chunks

```
apple_report.pdf
        │
        ▼ pypdf extracts text per page
        │
Page 1: "Apple Inc. designs and manufactures smartphones..."
Page 4: "Total net revenue was $394.3 billion in fiscal 2022..."
Page 6: "Net income was $99.8 billion representing 25.3% margin..."
        │
        ▼ RecursiveCharacterTextSplitter (500 chars, 100 overlap)
        │
Chunk 0: "Apple Inc. designs and manufactures smartphones, personal computers..."
Chunk 1: "...personal computers and wearables. The company sells through..."
Chunk 2: "Total net revenue was $394.3 billion in fiscal 2022, compared..."
Chunk 3: "...compared to $365.8 billion in 2021, an increase of 7.8%..."
Chunk 4: "Net income was $99.8 billion representing a net margin of 25.3%..."
```

### Step 2 — Chunks sent to embedding model

```
POST https://integrate.api.nvidia.com/v1/embeddings
{
  "model": "nvidia/nv-embedqa-e5-v5",
  "input": [
    "Apple Inc. designs and manufactures...",   ← chunk 0
    "...personal computers and wearables...",   ← chunk 1
    "Total net revenue was $394.3 billion...",  ← chunk 2
    "...compared to $365.8 billion in 2021...", ← chunk 3
    "Net income was $99.8 billion..."            ← chunk 4
  ],
  "input_type": "passage"    ← document mode
}
```

Response from NVIDIA:
```json
{
  "data": [
    {"embedding": [0.021, -0.14, 0.87, 0.003, ... 1024 numbers]},  ← chunk 0
    {"embedding": [0.019, -0.13, 0.85, 0.001, ... 1024 numbers]},  ← chunk 1
    {"embedding": [0.052, 0.91,  0.23, -0.44, ... 1024 numbers]},  ← chunk 2
    {"embedding": [0.049, 0.89,  0.21, -0.42, ... 1024 numbers]},  ← chunk 3
    {"embedding": [0.061, 0.88,  0.19, -0.51, ... 1024 numbers]}   ← chunk 4
  ]
}
```

### Step 3 — Stored in PostgreSQL

```python
# vector_store.py — save_chunks()
DocumentChunk(
    source      = "apple_report.pdf",
    page        = 4,
    chunk_index = 2,
    text        = "Total net revenue was $394.3 billion...",
    embedding   = [0.052, 0.91, 0.23, -0.44, ...]   # 1024 floats
)
```

What pgvector actually stores in the DB row:
```
id  | source               | page | text                          | embedding
----|----------------------|------|-------------------------------|------------------
1   | apple_report.pdf     | 1    | Apple Inc. designs...         | [0.021,-0.14,...]
2   | apple_report.pdf     | 1    | ...personal computers...      | [0.019,-0.13,...]
3   | apple_report.pdf     | 4    | Total net revenue $394.3B...  | [0.052, 0.91,...]
4   | apple_report.pdf     | 4    | ...compared to $365.8B...     | [0.049, 0.89,...]
5   | apple_report.pdf     | 6    | Net income was $99.8B...      | [0.061, 0.88,...]
```

---

## 5. HOW DATA FLOWS OUT OF pgvector

### Step 1 — User query arrives

```
"What was Apple's profit margin in 2022?"
```

### Step 2 — Query embedded with query mode

```
POST https://integrate.api.nvidia.com/v1/embeddings
{
  "model": "nvidia/nv-embedqa-e5-v5",
  "input": ["What was Apple's profit margin in 2022?"],
  "input_type": "query"    ← question mode, NOT passage mode
}
```

Response:
```json
{"embedding": [0.058, 0.86, 0.17, -0.49, ... 1024 numbers]}
```

### Step 3 — Cosine distance search in pgvector

```python
# vector_store.py — similarity_search()
SELECT
    id, text, source, page,
    1 - (embedding <=> '[0.058, 0.86, 0.17, -0.49, ...]') AS similarity
FROM document_chunks
ORDER BY embedding <=> '[0.058, 0.86, 0.17, -0.49, ...]'   -- cosine distance
LIMIT 20;
```

What `<=>` does — measures angle between two vectors:
```
query vector:   [0.058, 0.86, 0.17, -0.49, ...]
chunk 5 vector: [0.061, 0.88, 0.19, -0.51, ...]
                  ↑      ↑     ↑      ↑
              very close numbers → small angle → HIGH similarity

cosine distance = 0.03   →   similarity = 1 - 0.03 = 0.97  ✅ top result
```

### Step 4 — pgvector returns top 20

```python
candidates = [
    {"text": "Net income was $99.8B, margin 25.3%...",  "similarity": 0.97, "page": 6},
    {"text": "Total net revenue was $394.3 billion...", "similarity": 0.91, "page": 4},
    {"text": "Gross margin was 43.3% compared to...",   "similarity": 0.87, "page": 5},
    {"text": "Apple reported operating income of...",   "similarity": 0.84, "page": 7},
    ... 16 more
]
```

---

## 6. HOW DATA FLOWS THROUGH RERANKER

### Step 1 — 20 candidates from pgvector go in

```python
# reranker.py
passages = [
    {"id": 0, "text": "Net income was $99.8B, margin 25.3%..."},
    {"id": 1, "text": "Total net revenue was $394.3 billion..."},
    {"id": 2, "text": "Gross margin was 43.3% compared to..."},
    ... 17 more
]
```

### Step 2 — Cross-encoder reads query + each chunk together

For each of the 20 candidates, the model runs:

```
Input to neural network:
[CLS] What was Apple's profit margin in 2022? [SEP] Net income was $99.8B, margin 25.3%... [SEP]
                                    ↓
                           12-layer transformer
                           reads relationship between query and chunk
                                    ↓
                              score: 0.94    ← very relevant

[CLS] What was Apple's profit margin in 2022? [SEP] Total net revenue was $394.3 billion... [SEP]
                                    ↓
                           12-layer transformer
                                    ↓
                              score: 0.43    ← less relevant (revenue ≠ margin)
```

`[CLS]` = special start token. Absorbs meaning of entire input pair → produces final score.
`[SEP]` = separator. Tells model "query ends here, chunk begins here".

### Step 3 — Sort by score, return top 5

```python
results = ranker.rerank(RerankRequest(query=query, passages=passages))

# results sorted by score:
[
    {"id": 0, "score": 0.94},   ← "margin 25.3%"        BEST MATCH
    {"id": 2, "score": 0.81},   ← "Gross margin 43.3%"
    {"id": 5, "score": 0.76},   ← "operating margin..."
    {"id": 8, "score": 0.61},   ← "profitability analysis"
    {"id": 1, "score": 0.43},   ← "revenue $394.3B"      MOVED DOWN
]
```

Notice: "revenue" chunk was #2 by cosine (similarity 0.91) but moved to #5 by reranker (score 0.43) — because revenue ≠ margin.

### Step 4 — Formatted context string returned

```
[Source 1: apple_report.pdf, page 6 | rerank: 0.94 | cosine: 0.97]
Net income was $99.8 billion representing a net margin of 25.3%...

---

[Source 2: apple_report.pdf, page 5 | rerank: 0.81 | cosine: 0.87]
Gross margin was 43.3% compared to 41.8% in prior year...

---

[Source 3: apple_report.pdf, page 7 | rerank: 0.76 | cosine: 0.84]
Operating margin improved to 30.3% driven by...
```

This string is injected directly into the LLM prompt as `retrieved_context`.

---

## 7. COMPLETE END-TO-END FLOW

```
INGESTION TIME
══════════════════════════════════════════════════════

apple_report.pdf
      │
      ▼ pypdf → pages of text
      │
      ▼ chunker → 500-char chunks with 100-char overlap
      │
      ▼ embedder (nvidia/nv-embedqa-e5-v5, input_type=passage)
      │          NVIDIA API call → returns 1024-dim vectors
      │
      ▼ vector_store → INSERT INTO document_chunks
                       (text, embedding, source, page)
      ✅ stored in pgvector


QUERY TIME
══════════════════════════════════════════════════════

"What was Apple's profit margin in 2022?"
      │
      ▼ embedder (nvidia/nv-embedqa-e5-v5, input_type=query)
      │          NVIDIA API call → 1024-dim query vector
      │
      ▼ vector_store → SELECT ... ORDER BY embedding <=> query_vec LIMIT 20
      │                pgvector cosine distance → top 20 candidates
      │                each has text + similarity score
      │
      ▼ reranker (ms-marco-MiniLM-L-12-v2, LOCAL CPU)
      │          reads (query, each chunk) as pair → 20 scores
      │          sorts by score → top 5
      │
      ▼ retriever → formats top 5 into context string with citations
      │
      ▼ injected into aggregator_agent prompt as retrieved_context
      │
      ▼ LLM writes answer citing source + page numbers
```

---

## 8. WHY YOU NEED BOTH

### Only embedding (no rerank):
```
Query:  "What was Apple's profit margin?"
Result: top 5 by cosine similarity

Problem:
  "Apple revenue $394.3B" scores 0.91 cosine  ← similar words but wrong answer
  "Apple margin 25.3%"    scores 0.89 cosine  ← right answer ranked lower!

Without rerank → wrong chunk given to LLM → wrong answer
```

### Only reranking (no vector DB):
```
Must run cross-encoder on EVERY chunk in DB
  10,000 chunks × reranker = 10,000 neural network passes
  Takes minutes — completely unusable
```

### Both together:
```
pgvector  →  scans 10,000 chunks in milliseconds
             returns top 20 candidates (fast, approximate)
                    ↓
reranker  →  runs cross-encoder on only 20 pairs
             returns true top 5 (slow but on tiny set)
                    ↓
LLM gets the 5 best chunks → accurate answer
```

```
pgvector  =  fast coarse filter    (10,000 → 20)
reranker  =  slow precise scorer   (20 → 5)

Speed of vector search + Accuracy of cross-encoder = Best of both
```
