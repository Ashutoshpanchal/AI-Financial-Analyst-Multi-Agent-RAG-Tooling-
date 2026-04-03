# Chunking Strategy — Complete Guide

> Why 500 chars, 100 overlap, and RecursiveCharacterTextSplitter for this project.

---

## TABLE OF CONTENTS

1. [What Strategy We Use](#1-what-strategy-we-use)
2. [Why 500 Characters](#2-why-500-characters)
3. [Why 100 Character Overlap](#3-why-100-character-overlap)
4. [Too Small vs Too Large vs Just Right](#4-too-small-vs-too-large-vs-just-right)
5. [Visual Example — Financial Document](#5-visual-example--financial-document)
6. [Interview Answer](#6-interview-answer)

---

## 1. WHAT STRATEGY WE USE

### RecursiveCharacterTextSplitter

Not a simple fixed character split. Tries to split **intelligently** by trying separators in priority order:

```python
separators=["\n\n", "\n", ". ", " ", ""]
```

Priority order:
```
1st try:  \n\n  →  split on paragraph break   (keeps full paragraphs together)
2nd try:  \n    →  split on line break         (keeps sentences together)
3rd try:  ". "  →  split on sentence end       (keeps sentence complete)
4th try:  " "   →  split on word               (never cuts a word)
last:     ""    →  character split             (absolute last resort)
```

### Why recursive matters

```
Simple split (bad):
  "Apple revenue was $394.3B. Net income
   was $99.8B representing"               ← sentence cut in middle

Recursive split (good):
  "Apple revenue was $394.3B."            ← complete sentence
  "Net income was $99.8B representing..." ← complete sentence
```

The splitter always tries the largest semantic unit first — paragraph → sentence → word — before falling back to smaller units.

---

## 2. WHY 500 CHARACTERS

Three constraints drove this number:

### Constraint 1 — Embedding model token limit

```
nvidia/nv-embedqa-e5-v5  →  max 512 tokens

500 chars ≈ 100-150 tokens (English text)
                ↓
well under 512 token limit — safe headroom
```

If we used 3000 chars → ~450-600 tokens → hits the limit → model truncates → **loses end of chunk**.

### Constraint 2 — Retrieval precision

```
Financial report has:
  Page 4:  revenue figures
  Page 5:  margin analysis
  Page 6:  debt breakdown
  Page 7:  segment data

Query: "What was Apple's profit margin?"

Large chunk (3000 chars = entire page):
  Retrieved chunk has revenue + margin + debt + segments mixed together
  Similarity score diluted — everything looks equally relevant
  LLM buries the margin number in noise

Small chunk (500 chars = one topic):
  Retrieved chunk has ONLY margin discussion
  Similarity score focused — clearly the right chunk
  LLM gets clean, precise answer
```

### Constraint 3 — Financial document structure

Financial reports are written in dense paragraphs where **each paragraph discusses one metric**:

```
Paragraph about revenue (one chunk):
  "Total net revenue was $394.3 billion in fiscal 2022,
   compared to $365.8 billion in 2021, an increase of 7.8%.
   Growth was driven by iPhone sales (+6%) and Services (+14%)."
  → 283 chars → fits in one chunk ✅

Paragraph about margins (next chunk):
  "Net income was $99.8 billion representing a net margin of
   25.3%, compared to 25.9% in the prior year. Gross margin
   was 43.3%, up from 41.8% in fiscal 2021."
  → 221 chars → fits in one chunk ✅
```

500 chars captures exactly one complete financial discussion — not too much, not too little.

---

## 3. WHY 100 CHARACTER OVERLAP

### The boundary problem

Without overlap, related numbers get split across chunks and neither chunk has the full picture:

```
NO OVERLAP:
─────────────────────────────────────────────────────
Chunk 1 (chars 0-500):
  "...Apple's total debt stood at $120B as of September 2022.
   The company maintained $48.3B in cash and equivalents."
                                                    ↑ chunk ends here

Chunk 2 (chars 500-1000):
  "Debt-to-equity ratio improved from 1.89x to 1.73x
   year-over-year. Interest coverage ratio was 28x..."
   ↑ chunk starts here

Query: "Apple debt to equity 2022"
  Chunk 1: has total debt $120B — but NO D/E ratio
  Chunk 2: has D/E ratio 1.73x — but NO debt context
  Neither chunk is complete ❌
```

```
WITH 100-CHAR OVERLAP:
─────────────────────────────────────────────────────
Chunk 1 (chars 0-500):
  "...Apple's total debt stood at $120B as of September 2022.
   The company maintained $48.3B in cash and equivalents."

Chunk 2 (chars 400-900):   ← starts 100 chars back
  "The company maintained $48.3B in cash and equivalents.
   Debt-to-equity ratio improved from 1.89x to 1.73x..."
   ↑ overlap brings context from Chunk 1

Query: "Apple debt to equity 2022"
  Chunk 2: has cash $48.3B AND D/E ratio 1.73x together ✅
```

### Overlap = safety net for boundaries

```
100 chars ≈ 1-2 sentences of financial text
Just enough to carry context across the boundary
Not so much that chunks become redundant
```

---

## 4. TOO SMALL VS TOO LARGE VS JUST RIGHT

### Too Small (< 100 chars)

```python
chunk_size = 50

Chunks produced:
  "Total net revenue was"            ← incomplete thought
  "$394.3 billion in fiscal 2022,"   ← number with no context
  "compared to $365.8 billion"       ← comparison with no subject

Problems:
  ❌ Embedding captures meaningless fragment
  ❌ Vector has no meaningful direction — poor similarity scores
  ❌ LLM receives fragment with no context — cannot answer
  ❌ More chunks = slower retrieval, more noise in top-20
  ❌ Overlap becomes larger than chunk — duplicate content everywhere
```

### Too Large (> 2000 chars)

```python
chunk_size = 3000

Chunks produced:
  Entire page = revenue + margins + debt + segments + geography all mixed

Problems:
  ❌ 3000 chars ≈ 500-700 tokens → hits nvidia/nv-embedqa 512-token limit
  ❌ Embedding model truncates the end → last numbers LOST
  ❌ One vector must represent too many topics → diluted meaning
  ❌ Query about "profit margin" retrieves chunk also containing
     debt, segments, geography — LLM has too much noise
  ❌ Similarity score spreads across many topics → less precise ranking
  ❌ Reranker receives huge text → harder to score precisely
```

### Just Right (500 chars)

```python
chunk_size = 500

Chunks produced:
  Each chunk = one financial discussion (one metric, one paragraph)

Benefits:
  ✅ 500 chars ≈ 100-150 tokens → well under 512-token limit
  ✅ Vector captures one focused topic → precise similarity scores
  ✅ Query about "profit margin" retrieves ONLY margin discussion
  ✅ LLM gets clean, focused context → accurate answer
  ✅ Reranker scores short precise pairs → better ranking
```

---

## 5. VISUAL EXAMPLE — FINANCIAL DOCUMENT

### Input — Apple Annual Report page 4

```
"Apple Inc. reported strong financial results for fiscal year 2022.
Total net revenue was $394.3 billion, compared to $365.8 billion
in fiscal 2021, representing an increase of 7.8% year-over-year.
The growth was primarily driven by iPhone revenue of $205.5 billion,
an increase of 6.6%, and Services revenue of $78.1 billion, an
increase of 14.2%. Mac revenue was $40.2 billion, up 14.1% from
prior year driven by strong demand for the MacBook Pro..."
```

### After chunking (500 chars, 100 overlap)

```
Chunk 0 (chars 0-500):
  "Apple Inc. reported strong financial results for fiscal year 2022.
   Total net revenue was $394.3 billion, compared to $365.8 billion
   in fiscal 2021, representing an increase of 7.8% year-over-year.
   The growth was primarily driven by iPhone revenue of $205.5 billion,
   an increase of 6.6%, and Services revenue of $78.1 billion"
   metadata: {source: "apple_report.pdf", page: 4, chunk_index: 0}

Chunk 1 (chars 400-900):     ← 100-char overlap with Chunk 0
  "an increase of 6.6%, and Services revenue of $78.1 billion,
   an increase of 14.2%. Mac revenue was $40.2 billion, up 14.1%
   from prior year driven by strong demand for the MacBook Pro..."
   metadata: {source: "apple_report.pdf", page: 4, chunk_index: 1}
```

### After embedding

```
Chunk 0 → [0.052, 0.91, 0.23, -0.44, ... 1024 floats]
            ↑ points in "Apple total revenue fiscal 2022" direction

Chunk 1 → [0.041, 0.87, 0.31, -0.38, ... 1024 floats]
            ↑ points in "iPhone Services Mac revenue segments" direction
```

### At query time

```
Query: "What drove Apple's revenue growth in 2022?"
Query vector: [0.048, 0.89, 0.27, -0.41, ...]

Cosine distance to Chunk 0: 0.04  → similarity: 0.96 ← very close
Cosine distance to Chunk 1: 0.06  → similarity: 0.94 ← also close

Both retrieved → reranker picks Chunk 1 as more specific answer ✅
```

---

## 6. INTERVIEW ANSWER

**Q: What chunking strategy did you use? How did you choose chunk size and overlap?**

We used `RecursiveCharacterTextSplitter` with `chunk_size=500` characters and `chunk_overlap=100` characters.

The recursive splitter tries to split on paragraph breaks first, then sentence boundaries, then words — preserving semantic units rather than cutting blindly at a fixed character position.

We chose 500 characters for three reasons:
1. Our embedding model (`nvidia/nv-embedqa-e5-v5`) has a 512-token limit. 500 chars is approximately 100-150 tokens — well within the limit with headroom.
2. Financial reports are structured in dense paragraphs where each paragraph discusses one metric. 500 chars captures exactly one complete financial discussion.
3. Retrieval precision — smaller focused chunks produce more meaningful embeddings and better similarity scores than large mixed-content chunks.

We chose 100-character overlap because financial text often has related numbers across paragraph boundaries. Without overlap, debt figures and D/E ratios can end up in separate chunks where neither has the full context needed to answer a question. 100 chars (about 1-2 sentences) bridges that gap.

**Q: What happens if chunks are too small or too large?**

Too small (< 100 chars): Chunks become meaningless fragments. The embedding model produces noisy vectors with no clear direction. The LLM receives incomplete context and cannot form a coherent answer.

Too large (> 2000 chars): Chunks may exceed the embedding model's token limit causing truncation. More importantly, one chunk covers too many topics — the similarity score gets diluted and retrieval becomes imprecise. A query about profit margins retrieves a chunk that also contains debt, segments, and geography, giving the LLM too much noise.

500 characters is the sweet spot for financial documents specifically — complete enough to be meaningful, small enough to be precise.
