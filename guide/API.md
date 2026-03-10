# SCRIPTUM API Reference

Base URL: `http://localhost:8000`

Interactive API docs available at:
- Swagger UI: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- ReDoc: [http://localhost:8000/api/redoc](http://localhost:8000/api/redoc)

## Health Check

### GET /health

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "service": "scriptum-backend"
}
```

---

## File Upload

### POST /api/v1/files/upload

Upload one or more files (PDF, LaTeX, BibTeX). Max 50 MB per file.

```bash
curl -X POST http://localhost:8000/api/v1/files/upload \
  -F "files=@paper.pdf" \
  -F "files=@references.bib"
```

**Response** `200`:
```json
[
  {
    "file_id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "paper.pdf",
    "file_type": "pdf",
    "size_bytes": 2048576
  }
]
```

**Errors**: `400` invalid file type, `413` file too large

### GET /api/v1/files/{file_id}

Get file metadata.

```json
{
  "file_id": "550e8400-...",
  "filename": "paper.pdf",
  "file_type": "pdf",
  "size_bytes": 2048576,
  "created_at": "2026-03-06T10:30:00Z"
}
```

### DELETE /api/v1/files/{file_id}

Delete an uploaded file. Fails with `409` if linked to a review.

---

## Reviews

### POST /api/v1/reviews

Start a new paper review.

```bash
curl -X POST http://localhost:8000/api/v1/reviews \
  -H "Content-Type: application/json" \
  -d '{
    "file_ids": ["550e8400-..."],
    "journal_name": "neurips",
    "domain_general": "machine learning",
    "domain_specific": "natural language processing",
    "llm_provider": "anthropic",
    "llm_model": "claude-opus-4-6"
  }'
```

**Response** `201`:
```json
{
  "review_id": "660e8400-e29b-41d4-a716-446655440000",
  "status": "pending"
}
```

**Supported journals**: `aaai`, `acm`, `ieee`, `nature`, `neurips`

### GET /api/v1/reviews

List all reviews (paginated).

**Query params**: `skip` (default 0), `limit` (default 20)

```json
{
  "reviews": [
    {
      "id": "660e8400-...",
      "status": "completed",
      "paper_title": "Attention Is All You Need",
      "journal_name": "neurips",
      "created_at": "2026-03-06T10:30:00Z",
      "completed_at": "2026-03-06T10:45:00Z"
    }
  ],
  "total": 1
}
```

### GET /api/v1/reviews/{review_id}

Get review status and progress.

```json
{
  "id": "660e8400-...",
  "status": "reviewing",
  "current_step": "independent_review",
  "progress_percent": 45,
  "agent_statuses": {
    "core_expert": "evaluating",
    "adjacent_expert": "researching",
    "methods_specialist": "analyzing"
  },
  "paper_title": "Attention Is All You Need",
  "journal_name": "neurips",
  "created_at": "2026-03-06T10:30:00Z"
}
```

**Status values**: `pending` (0%), `processing` (10%), `desk_check` (20%), `reviewing` (40%), `aggregating` (80%), `completed` (100%), `failed`, `cancelled`

### GET /api/v1/reviews/{review_id}/report

Get the final review report (only for completed reviews).

```json
{
  "review_id": "660e8400-...",
  "status": "completed",
  "report": {
    "recommendation": "minor_revision",
    "confidence": "high",
    "key_strengths": [
      "Novel attention mechanism with strong theoretical grounding",
      "Comprehensive ablation studies"
    ],
    "key_weaknesses": [
      "Limited analysis of computational costs",
      "Missing comparison with recent concurrent work"
    ],
    "detailed_feedback": {
      "novelty": { "score": 8.5, "feedback": "..." },
      "methodology": { "score": 7.0, "feedback": "..." },
      "clarity": { "score": 9.0, "feedback": "..." }
    },
    "suggested_improvements": [
      "Add runtime/memory comparison table",
      "Discuss limitations section"
    ],
    "executive_summary": "A strong paper introducing a paradigm-shifting architecture..."
  }
}
```

**Recommendation values**: `accept`, `minor_revision`, `major_revision`, `reject`

**Confidence values**: `high`, `medium`, `low`

**Errors**: `404` review not found, `409` review not yet completed

### DELETE /api/v1/reviews/{review_id}

Cancel an in-progress review or delete a completed one.

### POST /api/v1/reviews/{review_id}/feedback

Submit user feedback on a completed review.

```bash
curl -X POST http://localhost:8000/api/v1/reviews/660e8400-.../feedback \
  -H "Content-Type: application/json" \
  -d '{
    "rating": 4,
    "category_ratings": {"accuracy": 5, "usefulness": 4, "detail": 3},
    "comments": "Helpful review, but could be more specific on methodology."
  }'
```

**Rating**: 1-5 (required)

---

## Settings

### GET /api/v1/settings

Get current configuration (API keys are masked).

```json
{
  "llm": {
    "default_provider": "anthropic",
    "providers": {
      "anthropic": {
        "api_key": "sk-ant-***...***",
        "default_model": "claude-opus-4-6",
        "enabled": true
      }
    }
  }
}
```

### PUT /api/v1/settings

Update configuration (partial merge — only provided fields are updated).

```bash
curl -X PUT http://localhost:8000/api/v1/settings \
  -H "Content-Type: application/json" \
  -d '{
    "llm": {
      "providers": {
        "anthropic": {
          "api_key": "sk-ant-new-key"
        }
      }
    }
  }'
```

API keys are encrypted before saving to `~/.scriptum/config.yaml`.

### POST /api/v1/settings/test-connection

Test an LLM connection.

```bash
curl -X POST http://localhost:8000/api/v1/settings/test-connection \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "anthropic",
    "model": "claude-opus-4-6",
    "api_key": "sk-ant-..."
  }'
```

**Response**:
```json
{
  "success": true,
  "latency_ms": 1250,
  "model_info": "claude-opus-4-6"
}
```

### GET /api/v1/settings/ollama/models

List available Ollama models.

```json
{
  "models": [
    {"name": "llama3.1:8b", "size": "4.7 GB"},
    {"name": "llama3.1:70b", "size": "40 GB"}
  ]
}
```

---

## Metrics

### GET /api/v1/metrics/dashboard

Aggregated dashboard statistics.

```json
{
  "total_reviews": 42,
  "completed_reviews": 38,
  "completion_rate": 0.905,
  "average_duration_seconds": 245.3,
  "total_cost_usd": 12.50
}
```

### GET /api/v1/metrics/reviews/{review_id}

Per-review detailed metrics.

```json
{
  "review_id": "660e8400-...",
  "stage_timings": {
    "document_processing": 12.5,
    "desk_check": 8.2,
    "independent_review": 180.3,
    "aggregation": 25.1
  },
  "agent_stats": {
    "core_expert": {"duration_s": 60.1, "tokens": 4500},
    "adjacent_expert": {"duration_s": 55.8, "tokens": 4200},
    "methods_specialist": {"duration_s": 58.3, "tokens": 4100}
  }
}
```

### GET /api/v1/metrics/costs

LLM cost breakdown.

```json
{
  "by_agent": {
    "meta_reviewer": {"total_usd": 3.20, "token_count": 25000},
    "core_expert": {"total_usd": 2.80, "token_count": 22000},
    "adjacent_expert": {"total_usd": 2.50, "token_count": 20000},
    "methods_specialist": {"total_usd": 2.40, "token_count": 19000}
  }
}
```

---

## Chat

### GET /api/v1/reviews/{review_id}/chat/history

Get chat message history (only for completed reviews).

```json
[
  {
    "id": "770e8400-...",
    "role": "user",
    "content": "Can you elaborate on the methodology weakness?",
    "created_at": "2026-03-06T11:00:00Z"
  },
  {
    "id": "770e8401-...",
    "role": "assistant",
    "content": "The main concern with the methodology is...",
    "created_at": "2026-03-06T11:00:05Z"
  }
]
```

---

## WebSocket Endpoints

### WS /ws/reviews/{review_id}

Real-time review progress streaming.

**Connect**:
```javascript
const ws = new WebSocket("ws://localhost:8000/ws/reviews/660e8400-...");
```

**Server messages**:

| Type | Fields | Description |
|------|--------|-------------|
| `progress` | `step`, `agent`, `progress`, `message` | Stage/agent progress update |
| `step_complete` | `step`, `result` | A pipeline stage finished |
| `complete` | `report_id` | Review finished successfully |
| `error` | `message` | Review encountered an error |

**Example messages**:
```json
{"type": "progress", "step": "reviewing", "agent": "core_expert", "progress": 45, "message": "Evaluating novelty..."}
{"type": "step_complete", "step": "desk_check", "result": {"passed": true}}
{"type": "complete", "report_id": "660e8400-..."}
{"type": "error", "message": "Agent timeout exceeded"}
```

**Client messages**:
```json
{"action": "cancel"}
```

### WS /ws/reviews/{review_id}/chat

Streaming chat with the Meta Reviewer.

**Client sends**:
```json
{"content": "What are the main contributions of this paper?"}
```

**Server streams**:
```json
{"type": "token", "content": "The"}
{"type": "token", "content": " main"}
{"type": "token", "content": " contributions"}
...
{"type": "complete"}
```

**Error**:
```json
{"type": "error", "message": "LLM not configured"}
```

The server persists both the user message and the complete assistant response to the database.

---

## Error Response Format

All errors follow a consistent JSON structure:

```json
{
  "error": "ReviewNotFoundError",
  "message": "Review not found.",
  "request_id": "req_abc123"
}
```

Validation errors (422) include additional details:

```json
{
  "error": "ValidationError",
  "message": "Request validation failed.",
  "details": [
    {"loc": ["body", "file_ids"], "msg": "field required", "type": "missing"}
  ],
  "request_id": "req_abc123"
}
```

### Error Codes

| Status | Error Type | When |
|--------|-----------|------|
| 400 | `ReviewError` | Invalid review operation |
| 404 | `ReviewNotFoundError` | Review/file not found |
| 409 | `ReviewStateError` | Operation invalid for current review state |
| 413 | — | File exceeds size limit |
| 422 | `ValidationError` | Request body validation failure |
| 422 | `DocumentProcessingError` | PDF/LaTeX parsing failure |
| 422 | `ParsingError` | Data parsing failure |
| 500 | `ConfigError` | Configuration issue |
| 500 | `AgentError` | Agent execution failure |
| 500 | `InternalServerError` | Unexpected error |
| 502 | `LLMError` | LLM provider failure |
| 504 | `AgentTimeoutError` | Agent exceeded timeout |

All responses include an `X-Request-ID` header for log correlation.
