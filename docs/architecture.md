# Architecture

## Runtime Shape

```text
Desktop UI
  -> localhost FastAPI relay
    -> provider API
    -> SQLite
```

The frontend never calls model providers directly. It sends authenticated requests to the local API service. The API service checks session state, loads role and task context, calls the configured model provider, and stores execution logs.

## Core Modules

- Company: one local AI company for MVP.
- Role: a position in the AI company, backed by an Agent prompt.
- Task: a Boss request that runs through the company workflow.
- Task Step: one role's execution within a task.
- Provider: local model provider configuration.

