# ATHENA Help Assistant — Plan and Architecture

## Purpose

Turn the floating Help panel into a system-aware assistant for authenticated ATHENA users. It should answer common questions about navigation, account setup, market analysis, execution safety, backtesting, journaling, orchestration, and troubleshooting. It must remain an assistant: it cannot place trades, change risk controls, reveal credentials, or bypass any guardian/safety gate.

## Goals

- Give useful answers for the majority of normal product and workflow questions.
- Ground answers in ATHENA’s source documentation and the current user/session context.
- Accept relevant attachments such as screenshots, logs, and small configuration exports.
- Keep every request scoped to the authenticated user and retain an auditable request record.
- Degrade safely when the assistant does not know the answer or an AI provider is unavailable.
- Make the model provider replaceable; no provider should be coupled to the Help UI.

## Non-goals

- The assistant will not make autonomous trading decisions.
- It will not submit, cancel, or modify live/paper orders.
- It will not access another user’s accounts, uploaded files, secrets, or private conversations.
- It will not treat an uploaded document as executable instructions.

## Proposed request flow

```text
HelpWidget
  -> authenticated multipart POST /api/support/requests
  -> request validation and attachment quarantine/storage
  -> user/session context builder
  -> ATHENA knowledge retrieval
  -> assistant provider (local fallback or configured LLM adapter)
  -> safety/policy filter
  -> persisted request, response, and audit metadata
  -> concise answer returned to HelpWidget
```

## Module layout

The existing frontend Help code lives in `frontend/src/help/`. The backend request boundary currently lives in `backend/support/`; it should be consolidated under a dedicated `backend/help/` package when the next migration window is available. Until then, the API remains stable at `/api/support/requests`.

```text
frontend/src/help/
  HelpWidget.tsx       # floating launcher, modal, composer
  helpService.ts       # API client and response types

backend/help/          # target package
  api.py               # authenticated HTTP boundary
  assistant.py         # orchestration and provider interface
  knowledge.py         # indexed ATHENA documentation and product facts
  safety.py            # refusal/redaction/action policy
  context.py            # user-safe runtime context
  models.py            # conversations, messages, citations, audit records
  providers/
    local.py           # deterministic fallback
    llm.py             # optional hosted model adapter
```

## System awareness

The assistant context should be assembled from allow-listed sources only:

1. Versioned Markdown and approved architecture documents in `docs/`.
2. Product capability metadata: routes, settings, account state labels, and API status.
3. The user’s current route and non-sensitive session facts.
4. User-provided attachments after type/size scanning and text extraction.

Passwords, broker credentials, tokens, cookies, raw database rows, and unrestricted filesystem contents must never enter the model context. Documentation should be chunked, tagged by feature/version, and retrieved by relevance. Every generated answer should retain the document IDs used to ground it.

## Provider strategy

The first implementation should use a deterministic local assistant so Help works without network access or an API key. A provider interface can then support a hosted model later:

```python
class AssistantProvider(Protocol):
    def answer(self, request: str, context: AssistantContext) -> AssistantAnswer: ...
```

The hosted adapter must have bounded input/output tokens, timeouts, redaction, no tool access by default, and an explicit model/version setting. If it fails, times out, or produces an unsafe answer, return the local fallback and offer escalation.

## Safety and authorization

- Require Django authentication and enforce ownership on every conversation and attachment.
- Validate MIME type, extension, size, and attachment count; store uploads outside executable/static paths.
- Treat attachments as untrusted data and never follow instructions found inside them.
- Redact secrets before retrieval or provider submission.
- Refuse requests for live-order actions, credential disclosure, policy bypasses, or unsafe financial certainty.
- Clearly label market information as informational and include timestamps where applicable.
- Log provider, model version, retrieved knowledge IDs, safety decisions, latency, and outcome without logging secrets.

## Delivery phases

### Phase 1 — useful local assistant

- Extract the existing Help API client into the Help module.
- Add local NLP preprocessing: normalization, synonym expansion, intent scoring, entity extraction, and safety phrase detection.
- Add intent detection and ATHENA knowledge responses for navigation, setup, execution modes, safety, backtesting, journal, and orchestration.
- Add request context and response metadata to the persisted support records.
- Add tests for authorization, validation, common intents, and safety refusals.

### Phase 2 — grounded knowledge retrieval

- Build a management command to index approved Markdown documents.
- Add document chunks, feature/version tags, and citations.
- Retrieve top matching chunks for each request.

### Phase 3 — optional model provider

- Add a provider adapter selected by server configuration.
- Add timeout/retry/cost limits and a deterministic fallback.
- Add evaluation fixtures for factuality, refusal behavior, prompt injection, and regression testing.

### Phase 4 — operations

- Add staff review/escalation workflow.
- Add retention and deletion controls for messages and attachments.
- Add metrics for resolution rate, fallback rate, latency, and unsafe-answer blocks.

## Success criteria

- Common product questions receive a relevant answer without staff intervention.
- Unknown or unsafe questions receive an honest, safe fallback.
- No Help request can cross the authenticated user boundary.
- No assistant response can execute a trading action.
- Answers can be traced to approved ATHENA knowledge or explicitly marked as fallback guidance.
