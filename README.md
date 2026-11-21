# AXON 🤖

**A = Autonomous | X = eXtensible | O = OS | N = Navigator**

AXON is a local MCP (Model Context Protocol) server that gives any LLM
full structured control over your Windows file system.
100% local. No cloud. No API costs. Your data never leaves your machine.

---

## Architecture


```
tools/      ← MCP interface layer    (what the LLM sees and calls)
services/   ← Business logic layer   (how operations actually work)
utils/      ← Infrastructure layer   (validation, logging, recycle bin)
config/     ← Configuration layer    (settings, environment)
```

Design patterns used:
- **Factory Method** — `Settings.from_env()`, `AuditLogger.get_instance()`, `MCPServerFactory.create()`
- **Dependency Injection** — all services receive dependencies via constructor
- **Singleton** — one Settings instance, one AuditLogger per process
- **Single Responsibility** — each class has exactly one reason to change

---

## Tools (30 total)

| Category | Tools |
|---|---|
| File Operations | create, read, write, append, copy, move, rename, delete, exists |
| Folder Operations | create, list, tree, size, copy, move, rename, delete |
| Search | by name, by extension, by date, by size |
| File Info | get info, count, find duplicates, find large, find empty |
| Safety | confirm delete, backup, undo last, audit log |

---

## Tech Stack

| Package | Version | Purpose |
|---|---|---|
| fastmcp | 4.1.4 | MCP server framework |
| send2trash | 2.1.0 | Safe delete via Recycle Bin |
| python-dotenv | 1.0.1 | Environment config |
| Python | >= 3.10 | Runtime |

---

## Setup

```bash
# 1. Clone
git clone https://github.com/yourusername/AXON.git
cd axon

# 2. Install dependencies
uv sync

# 3. Configure allowed paths
# Edit .env — set ALLOWED_PATHS to your folders

# 4. Run the server
uv run python main.py
```

---

## Safety Features

- All paths validated against `ALLOWED_PATHS` before every operation
- Deletes go to Recycle Bin — never permanent
- Undo stack with JSON persistence — `undo_last()` reverses any operation
- Full audit log at `logs/audit.log` — every operation recorded
- Confirm before delete — `confirm_delete()` shows file details first

---


---


