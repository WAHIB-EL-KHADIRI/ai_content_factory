# Contributing to AI Content OS

Thank you for considering a contribution to AI Content OS! This guide covers everything you need to get up and running.

---

## Table of Contents

- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Issue Guidelines](#issue-guidelines)
- [Architecture Overview](#architecture-overview)
- [Adding a New Agent](#adding-a-new-agent)
- [Adding a Plugin](#adding-a-plugin)
- [Adding a Workflow Step](#adding-a-workflow-step)

---

## Development Setup

### With Docker (recommended)

```bash
git clone https://github.com/your-org/ai-content-os.git
cd ai-content-os
cp .env.example .env
docker compose up -d
```

This starts the backend, frontend, Redis, and database containers. The API will be available at `http://localhost:8000` and the frontend at `http://localhost:3000`.

### Manual Setup

```bash
git clone https://github.com/your-org/ai-content-os.git
cd ai-content-os

# Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Environment
cp .env.example .env
# Edit .env with your API keys

# Start backend
python -m backend.api.app

# Frontend (in a separate terminal)
cd frontend
npm install
npm run dev
```

### Environment Variables

At minimum you need:

- `OPENAI_API_KEY` — for LLM calls
- `DATABASE_URL` — defaults to SQLite for local dev
- `SECRET_KEY` — used for JWT token signing

---

## Code Style

### Python

- **Formatter/Linter:** [Ruff](https://docs.astral.sh/ruff/) — run `ruff format backend/` and `ruff check backend/`
- **Type checker:** [MyPy](https://mypy-lang.org/) — run `mypy backend/`
- **Style:** PEP 8, enforces line length of 100 characters
- **Docstrings:** Required on all public classes and functions (Google style)
- **Imports:** Sorted by Ruff's isort rules

### TypeScript / React

- **Formatter:** Prettier (configured in `frontend/`)
- **Linter:** ESLint (configured in `frontend/`)
- **Types:** Strict TypeScript — no `any` types without justification

### Before Every Commit

```bash
# Python
ruff format backend/
ruff check backend/ --fix
mypy backend/

# Frontend
cd frontend && npm run lint
```

---

## Testing

### Running Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# With coverage report
pytest tests/ -v --cov=backend --cov-report=html
```

### Writing Tests

- **Unit tests** go in `tests/unit/` — should be fast, no external dependencies
- **Integration tests** go in `tests/integration/` — may use the database
- Name test files `test_<module>.py` and test functions `test_<behavior>`
- Use `pytest` fixtures for shared setup (defined in `conftest.py`)

### Coverage Target

Aim for **80%+ coverage** on new code. CI will flag drops below this threshold.

---

## Pull Request Process

1. **Fork** the repo and create a feature branch from `main`
2. **Make your changes** following the code style above
3. **Write tests** for new functionality
4. **Run the full test suite** and ensure it passes:
   ```bash
   ruff check backend/ && mypy backend/ && pytest tests/ -v
   ```
5. **Update documentation** if you changed APIs or added features
6. **Submit your PR** with:
   - A clear title describing the change
   - A description of what changed and why
   - Reference to any related issues (`Closes #123`)
7. **Respond to review feedback** promptly

### PR Checklist

- [ ] Tests pass locally
- [ ] Ruff and MyPy report no errors
- [ ] New code has tests
- [ ] Public functions have docstrings
- [ ] Documentation updated (if applicable)
- [ ] No secrets or API keys committed

---

## Issue Guidelines

### Bug Reports

Include:
- Steps to reproduce
- Expected vs actual behavior
- Python/Node version, OS, and relevant logs

### Feature Requests

Include:
- Clear description of the problem you're solving
- How you envision the solution
- Whether you're willing to implement it

### Good First Issues

Look for issues tagged `good first issue` — these are scoped for new contributors.

---

## Architecture Overview

```
backend/
├── api/          HTTP endpoints, middleware, WebSocket handlers
├── core/         Configuration, auth (JWT), security utilities
├── db/           SQLAlchemy models, database initialization
├── agents/       8 specialized AI agent implementations
├── services/     Business logic (content, brand, memory, model routing)
├── workflows/    Workflow engine, builder, conditions, retry logic
├── analytics/    Cost tracking, token usage, performance metrics
└── plugins/      Plugin SDK, base classes, registry
```

### Key Design Principles

- **Agents are stateless** — they receive context, execute, and return results
- **Services encapsulate business logic** — agents and routes delegate to services
- **Workflows compose agents** — the engine orchestrates multi-step pipelines
- **Plugins extend everything** — agents, tools, workflows, and integrations

---

## Adding a New Agent

1. Create a new file `backend/agents/<name>.py`
2. Extend `BaseAgent` and implement `execute()` and `get_system_prompt()`:

```python
from backend.agents.base import BaseAgent, AgentRole

class MyAgent(BaseAgent):
    role = AgentRole.WRITER  # or add a new role

    async def execute(self, task: dict) -> dict:
        # Your agent logic here
        return {"result": "..."}

    def get_system_prompt(self) -> str:
        return "You are a specialized content agent..."
```

3. Register in `backend/agents/router.py`
4. Add the agent to `AgentRole` enum if needed
5. Write unit tests in `tests/unit/test_agents_<name>.py`
6. Update the agents table in `README.md`

---

## Adding a Plugin

1. Create a new file in `backend/plugins/`
2. Extend one of the base classes:

| Base Class | Use Case |
|-----------|----------|
| `Plugin` | General-purpose plugin |
| `AgentPlugin` | Extends or wraps an agent |
| `ToolPlugin` | Adds a new tool for agents to use |
| `IntegrationPlugin` | Connects to external services |

3. Implement the required methods
4. Register in the `PluginRegistry`
5. Write tests

---

## Adding a Workflow Step

1. Create the step class in `backend/workflows/steps/`
2. Extend `WorkflowStep` and implement `execute()`:

```python
from backend.workflows.engine import WorkflowStep

class MyStep(WorkflowStep):
    name = "my_step"

    async def execute(self, context: dict) -> dict:
        # Process context and return updated context
        return {**context, "my_output": "..."}
```

3. Register in the workflow builder
4. Add to relevant templates
5. Write tests

---

## Questions?

Open a [Discussion](https://github.com/your-org/ai-content-os/discussions) or ask in the `#contributors` channel. We're happy to help.
]]>