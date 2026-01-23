# Integrations Analysis

**Generated:** YYYY-MM-DD
**Project:** [project name]

## Summary

[2-3 sentence overview of external integrations - include count of integrations, primary cloud provider if any, and most critical dependencies]

## Findings

### Cloud Provider

| Attribute | Value | Evidence |
|-----------|-------|----------|
| Primary Provider | [AWS/GCP/Azure/Firebase/None] | [SDK packages, config files] |
| Secondary Providers | [list or "None"] | [evidence] |
| Deployment Platform | [Vercel/Netlify/Heroku/Self-hosted/etc] | [config files] |

**Cloud Services Used:**
| Service | Provider | Purpose | Configuration |
|---------|----------|---------|---------------|
| [e.g., S3] | [AWS] | [file storage] | [env vars, config location] |

### External APIs

| Service | Purpose | Auth Method | Client Library | Env Vars |
|---------|---------|-------------|----------------|----------|
| [service name] | [what it's used for] | [API Key/OAuth/JWT/etc] | [package name] | [env vars used] |

**API Client Patterns:**
- HTTP Client: [axios/fetch/got/requests/etc]
- Retry/Circuit Breaker: [yes - library / no]
- Rate Limiting: [implemented / not observed]

### Databases & Storage

**Primary Database:**
| Attribute | Value | Evidence |
|-----------|-------|----------|
| Type | [PostgreSQL/MySQL/MongoDB/etc] | [driver package, connection string] |
| Driver/ORM | [Prisma/TypeORM/mongoose/etc] | [package.json/requirements] |
| Connection | [env var name] | [e.g., DATABASE_URL] |
| Migrations | [yes - tool / no] | [migration directory or tool] |

**Additional Data Stores:**
| Store | Type | Purpose | Connection |
|-------|------|---------|------------|
| [e.g., Redis] | [Cache/Queue/etc] | [session storage/caching/etc] | [REDIS_URL] |

**File Storage:**
| Service | Purpose | Configuration |
|---------|---------|---------------|
| [S3/GCS/Local/etc] | [user uploads/assets/etc] | [env vars, bucket config] |

### Message Queues & Event Systems

| Service | Purpose | Configuration | Consumer/Producer |
|---------|---------|---------------|-------------------|
| [RabbitMQ/Kafka/SQS/etc or "None detected"] | [what it's used for] | [connection env vars] | [where in code] |

### Third-Party SDKs

**Payment Processing:**
| Provider | Purpose | SDK | Env Vars |
|----------|---------|-----|----------|
| [Stripe/PayPal/etc or "None"] | [payments/subscriptions] | [package] | [env vars] |

**Authentication:**
| Provider | Purpose | SDK | Env Vars |
|----------|---------|-----|----------|
| [Auth0/Clerk/Firebase/Custom or "Built-in"] | [user auth/SSO] | [package] | [env vars] |

**Analytics & Monitoring:**
| Service | Purpose | SDK | Env Vars |
|---------|---------|-----|----------|
| [Segment/Amplitude/Sentry/etc or "None"] | [tracking/errors/APM] | [package] | [env vars] |

**Communication:**
| Service | Purpose | SDK | Env Vars |
|---------|---------|-----|----------|
| [SendGrid/Twilio/etc or "None"] | [email/SMS] | [package] | [env vars] |

**Search:**
| Service | Purpose | SDK | Env Vars |
|---------|---------|-----|----------|
| [Elasticsearch/Algolia/etc or "None"] | [full-text search] | [package] | [env vars] |

**Other Integrations:**
| Service | Category | Purpose | SDK | Env Vars |
|---------|----------|---------|-----|----------|
| [any other services] | [category] | [purpose] | [package] | [env vars] |

### Environment Dependencies

**Required Environment Variables:**
| Variable | Service | Required | Default | Notes |
|----------|---------|----------|---------|-------|
| [VAR_NAME] | [which service] | [yes/no] | [default if any] | [notes] |

**Environment Files:**
| File | Purpose | Gitignored |
|------|---------|------------|
| [.env, .env.local, etc] | [purpose] | [yes/no] |

**Secrets Management:**
- Approach: [env vars only / vault / AWS Secrets Manager / etc]
- Notes: [any observations about secrets handling]

### Feature Flags & Remote Config

| Service | Purpose | Configuration |
|---------|---------|---------------|
| [LaunchDarkly/Unleash/etc or "None detected"] | [feature management] | [SDK and env vars] |

## Integration Architecture

```
[ASCII diagram showing how integrations connect]

Example:
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   API       │────▶│  Database   │
│   (React)   │     │  (Express)  │     │  (Postgres) │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌─────────┐  ┌─────────┐  ┌─────────┐
        │  Redis  │  │ Stripe  │  │  S3     │
        │ (cache) │  │(payment)│  │(storage)│
        └─────────┘  └─────────┘  └─────────┘
```

## Risk Assessment

| Integration | Criticality | Fallback | Notes |
|-------------|-------------|----------|-------|
| [service] | [Critical/Important/Nice-to-have] | [yes - how / no] | [single point of failure? rate limits?] |

## Recommendations

### Security
- [Security-related recommendations for integrations]

### Reliability
- [Reliability recommendations - circuit breakers, retries, fallbacks]

### Cost Optimization
- [If applicable - service tier recommendations]

### Maintenance
- [SDK version updates, deprecation notices]

---
*Generated by `/analyze-codebase`*
