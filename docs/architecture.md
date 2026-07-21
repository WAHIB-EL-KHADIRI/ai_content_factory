# AI Content OS - Architecture

## System Overview

AI Content OS is a multi-agent content creation platform that orchestrates AI models to research, write, optimize, edit, translate, design, and publish content.

## Core Components

### 1. Model Router (`backend/services/model_router.py`)
- Selects optimal AI model for each task
- Considers cost, quality, speed, and features
- Tracks usage and costs per model
- Supports OpenAI, Anthropic, DeepSeek

### 2. Multi-Agent System (`backend/agents/`)
- **BaseAgent** - Abstract base with common model interaction
- **AgentRouter** - Orchestrates agent execution
- **ResearchAgent** - Topic research and analysis
- **WriterAgent** - Content creation
- **SEOAgent** - Search optimization
- **EditorAgent** - Content editing
- **TranslatorAgent** - Multi-language support
- **DesignerAgent** - Visual content
- **PublisherAgent** - Multi-platform publishing
- **ReviewAgent** - Quality assurance

### 3. Workflow Engine (`backend/workflows/`)
- Declarative workflow definition
- Conditional execution
- Variable resolution
- Retry with backoff
- Human approval gates
- Parallel step execution

### 4. Brand Center (`backend/services/brand.py`)
- Brand identity management
- Voice and tone consistency
- Style guide enforcement
- Brand compliance analysis

### 5. Memory System (`backend/services/memory.py`)
- Long-term memory for users, projects, brands
- Relevance-based recall
- Memory types: preferences, context, facts, patterns

### 6. Plugin SDK (`backend/plugins/`)
- Agent plugins
- Tool plugins
- Integration plugins
- Hook system for extensibility

### 7. Analytics Engine (`backend/analytics/`)
- Cost tracking per model/task
- Token usage monitoring
- Quality score tracking
- Performance metrics

## Data Flow

```
User Request
    │
    ▼
Workflow Engine
    │
    ├──▶ Research Agent ──▶ Model Router ──▶ AI Provider
    ├──▶ Writer Agent ──▶ Model Router ──▶ AI Provider
    ├──▶ SEO Agent ──▶ Model Router ──▶ AI Provider
    ├──▶ Editor Agent ──▶ Model Router ──▶ AI Provider
    ├──▶ Review Agent ──▶ Model Router ──▶ AI Provider
    └──▶ Publisher Agent ──▶ Model Router ──▶ AI Provider
            │
            ▼
    Analytics Engine ──▶ Database
            │
            ▼
    Response to User
```

## Database Schema

- **users** - User accounts
- **projects** - Content projects
- **contents** - Created content
- **content_revisions** - Version history
- **brands** - Brand identities
- **workflows** - Workflow definitions
- **workflow_runs** - Execution history
- **memories** - Long-term memory
- **plugins** - Installed plugins
- **content_analytics** - Quality metrics
- **audit_logs** - Activity tracking
- **usage_records** - API usage tracking

## Security

- API key authentication
- Role-based access control
- Audit logging
- Rate limiting
- Input validation
