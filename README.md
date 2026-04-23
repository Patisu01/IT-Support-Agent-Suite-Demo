# POS Incident Agent POC

This proof of concept follows the project challenge flow using checked-in source files:

- `data\Asset Metadata.csv`
- `data\ITSM Log.csv.xlsx`
- `data\Standard Operating Procedure_POS Restart Sequence.docx`

The demo simulates an agent that:

1. Ingests a synthetic `POS Offline` ticket.
2. Enriches the ticket with asset and ITSM history context.
3. Retrieves the most relevant SOP restart steps.
4. Calls mock action endpoints.
5. Produces an auditable execution log and a manager-ready summary.

## Important assumptions

The provided source files are close to the challenge brief, but not perfectly aligned:

- The asset file uses `SW-0004` style IDs while the ITSM file uses `Store_042` style location codes.
- The SOP includes a restart sequence, but its brand-specific section is empty.
- The asset file does not include a brand column.

To keep the POC runnable and transparent, the project adds:

- a local `store_alias_map` to reconcile ITSM and CMDB identifiers
- a local `model_family_map` to infer a provider family from POS model names
- a LangChain retrieval layer built with `RecursiveCharacterTextSplitter`, `FAISS`, and the `sentence-transformers/all-MiniLM-L6-v2` embedding model cached locally for stronger semantic search

The embedding model is downloaded once and cached locally beside the SOP source so repeat demo runs stay fast and self-contained.

## Project layout

- `src/pos_agent_poc.py` - main demo entrypoint
- `src/poc_support.py` - parsers, retriever, and mock tools
- `config/poc_config.json` - local source paths and mapping assumptions
- `outputs/` - generated run logs

## Run

Use the bundled Python runtime:

```powershell
& "C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" .\src\pos_agent_poc.py
```

The script writes:

- a console execution trace
- `outputs\pos_incident_demo_log.txt`
- `outputs\pos_incident_summary.txt`

## Default demo ticket

The demo uses `Store_042 (Northside)` because your ITSM history shows repeated `POS Terminal Freeze` incidents there, making it a good stand-in for the requested `POS Offline` scenario.
