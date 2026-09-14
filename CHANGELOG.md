# Changelog

All notable changes to AI Content OS are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.1.0] — 2026-09-14

Correctness and supply-chain work on top of 1.0.0. No new product surface.

### Fixed

- **CI had been running zero jobs on every push since it was set up** — an
  invalid workflow trigger meant the pipeline reported nothing rather than
  failing. Every check in this list only started running once that was fixed.
- Two real bugs surfaced while resolving mypy errors, not merely type
  annotations.
- A broken CDATA wrapper in the docs, and a coverage badge that displayed a
  number nothing produced.
- ESLint was missing from the frontend entirely; added, with the lint and type
  errors it then reported all fixed.

### Security

- Five dependencies with known CVEs bumped.
- Least-privilege `permissions:` declared on every workflow, and every action
  pinned to a commit SHA.
- `js-yaml` raised to 4.3.1.
- `pip-audit` runs as a warning rather than a gate while #1 is open, so it
  reports without blocking unrelated work.

### Changed

- ORM models migrated to the SQLAlchemy 2.0 typed style.
- Backend formatted with `ruff format`.
- Leftover references to AI coding tools removed from the source.

### Added

- Mermaid architecture diagram in the documentation (#2).

## [1.0.0] — 2026-07-21

Initial public release.

### Multi-Agent System

- 8 specialized AI agents: Research, Writer, SEO, Editor, Translator, Designer, Publisher, Reviewer
- Agent router with role-based dispatch and task routing
- Base agent class with pluggable system prompts and tool access
- Agent execution with context passing and result aggregation

### Workflow Engine

- Visual workflow builder with drag-and-drop step arrangement
- Conditional branching and parallel execution
- Retry logic with configurable backoff
- Human approval gates for sensitive steps
- Workflow templates for common content pipelines (article, social post, video script)
- Context propagation between workflow steps

### Model Router

- Multi-provider support: OpenAI (GPT-4o), Anthropic (Claude), DeepSeek
- Intelligent model selection based on task type, cost constraints, and quality requirements
- Automatic fallback between providers
- Cost estimation before execution
- Token usage tracking per request

### Content Management

- Full content lifecycle: research, write, optimize, review, translate, publish
- Content versioning and revision history
- Project organization with multi-project support
- Content status tracking (draft, in review, published, archived)

### Brand Consistency Engine

- Brand identity profiles (voice, tone, style guide, vocabulary)
- Automatic style enforcement across all generated content
- Brand-aware content scoring
- Multi-brand support per organization

### Research & Knowledge

- RAG-powered research studio
- Document upload and ingestion (PDF, DOCX, TXT, Markdown)
- Knowledge base management with semantic search
- Source citation and attribution

### Real-Time Communication

- WebSocket-based real-time updates
- Streaming chat with LLM responses
- Live workflow progress tracking
- Agent collaboration in real time

### Memory System

- Long-term memory for users, projects, and brands
- Persistent context across sessions
- Semantic memory retrieval
- Memory scoping per project and brand

### Analytics & Cost Control

- Token usage tracking across all model calls
- Cost breakdown by model, agent, and workflow
- Performance metrics (latency, success rate, quality scores)
- Usage dashboards and reporting

### Plugin System

- Plugin SDK with base classes for agents, tools, and integrations
- Plugin registry with auto-discovery
- Plugin marketplace support
- Hook system for extending existing behavior

### API Layer

- FastAPI REST API with full OpenAPI documentation
- JWT-based authentication with refresh tokens
- API key authentication for programmatic access
- Rate limiting (configurable per endpoint)
- Request logging and error handling middleware
- CORS support for frontend integration

### Admin Dashboard

- User management (CRUD, roles, permissions)
- System health monitoring
- Cost analytics and budget controls
- Audit logging for compliance

### Frontend

- React 18 SPA with TypeScript
- Tailwind CSS with full dark mode support
- Vite for fast development and builds
- Responsive design for desktop and tablet
- Dashboard, chat, workflow builder, and content editor views

### Infrastructure

- Docker and Docker Compose for containerized deployment
- SQLite for development, PostgreSQL for production
- Alembic database migrations
- Redis integration for background task queue
- GitHub Actions CI/CD pipeline

### Developer Experience

- Comprehensive test suite (unit and integration)
- Ruff for linting and formatting
- MyPy for type checking
- Pre-commit hooks
- Environment-based configuration with `.env.example`

### Security

- Password hashing with bcrypt
- JWT token expiration and refresh
- Input validation on all endpoints
- Rate limiting to prevent abuse
- Audit logging for sensitive operations
- Secrets excluded from version control

---

*This is the initial release. Future versions will follow the [Keep a Changelog](https://keepachangelog.com/) format with additions, changes, deprecations, removals, and fixes sections.*
]]>