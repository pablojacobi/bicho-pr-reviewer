# Diagrams

Mermaid diagrams of how Bicho is put together. They render natively on GitHub. See also the two
diagrams in [ARCHITECTURE.md](../ARCHITECTURE.md) (layers and the high-level pipeline).

## The LangGraph review workflow

A linear spine into one parallel fan-out superstep (analyzers + scanners), fanned back in via
`operator.add` reducers, then a gated publish tail. Every fan-out node degrades to a diagnostic
instead of raising, so one failure never rolls the superstep back.

```mermaid
flowchart TD
    START([START]) --> FP[fetch_pull_request] --> FC[fetch_changed_files]
    FC --> ND[normalize_diff] --> DL[detect_language] --> GF[gather_file_contents] --> SA[select_analyzers]

    SA -. selected subset .-> COR[correctness]
    SA -.-> SEC[security]
    SA -.-> PER[performance]
    SA -.-> MAI[maintainability]
    SA -.-> TES[tests]
    SA -.-> CON[contracts]
    SA -.-> SG[semgrep]
    SA -.-> PA[pip-audit]

    COR & SEC & PER & MAI & TES & CON & SG & PA --> CF[collect_findings]
    CF --> VF[verify_findings] --> CR[compose_review] --> IG{idempotency_guard}
    IG -- dry-run / already reviewed --> DONE([END])
    IG -- proceed --> SH{stale_head_guard}
    SH -- head moved --> DONE
    SH -- unchanged --> PUB[publish_github_review] --> DONE

    subgraph fanout [parallel superstep: resilient, degrade-not-raise]
        COR
        SEC
        PER
        MAI
        TES
        CON
        SG
        PA
    end
```

## The model-provider abstraction

The domain never imports a model vendor. Every LLM call goes through the `ModelProvider` port; the one
infrastructure implementation wraps a LangChain `ChatOpenAI` pointed at any OpenAI-compatible endpoint,
with retry and a concurrency limit. Adding a provider (Gemini, OpenAI, a local proxy) is configuration.

```mermaid
flowchart LR
    subgraph app [application]
        AN[LLMAnalyzer × 6] --> PORT
        VER[LLMFindingVerifier] --> PORT
    end
    subgraph domain
        PORT[[ModelProvider port]]
    end
    subgraph infra [infrastructure]
        IMPL[LangChainModelProvider<br/>retry + concurrency limit] --> CO[ChatOpenAI]
    end
    PORT -. implemented by .-> IMPL
    CO --> EP{{OpenAI-compatible endpoint}}
    EP --> MM[MiniMax]
    EP --> GEM[Gemini]
    EP --> OAI[OpenAI / proxy]
```

## Webhook to published review

The webhook is acknowledged in milliseconds; the heavy work runs off-request as an isolated background
task. Nothing durable — a restart drops in-flight work, recovered by the manual endpoint.

```mermaid
sequenceDiagram
    participant GH as GitHub
    participant WH as POST /webhooks/github
    participant BR as BackgroundReviewRunner
    participant RS as ReviewService (graph)
    GH->>WH: pull_request event (+ HMAC signature)
    WH->>WH: verify HMAC over raw body
    WH->>WH: filter action, de-dup delivery id
    WH-->>GH: 202 Accepted
    WH->>BR: schedule(request)
    BR->>RS: run(request, options)
    RS->>GH: fetch PR / files / file contents
    RS->>RS: analyzers + scanners → verify → compose
    RS->>GH: publish one review (inline comments + marker)
```

## LangSmith tracing

When `LANGSMITH_TRACING` is set, LangChain sends each run to LangSmith automatically. Every model call
is tagged with its role, prompt version, and correlation id, so a review's calls are grouped and
inspectable. Tracing is force-off in tests.

```mermaid
flowchart LR
    CALL[ModelProvider.structured] -->|tags: role, prompt:version, correlation_id| LC[LangChain run]
    LC -->|LANGSMITH_TRACING=true| LS[(LangSmith project)]
    LC -->|unset / tests| NONE[no trace sent]
```
