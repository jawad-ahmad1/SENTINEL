# Diagrams

This directory contains architecture and flow diagrams for Sentinel.

## Available Diagrams

See [ARCHITECTURE.md](../../ARCHITECTURE.md) for Mermaid diagrams rendered inline:

- **System Overview** — 4-tier architecture (Nginx → FastAPI → PostgreSQL + Redis)
- **RFID Scan Flow** — Sequence diagram from card tap to database record
- **Authentication Flow** — JWT login, refresh, and cookie management
- **Database Schema** — Entity-relationship diagram

## Generating Diagram Images

To export Mermaid diagrams as images:

```bash
# Install Mermaid CLI
npm install -g @mermaid-js/mermaid-cli

# Export to PNG
mmdc -i diagram.mmd -o diagram.png -t dark -b transparent
```

Or use the [Mermaid Live Editor](https://mermaid.live/) to paste and export diagrams.
