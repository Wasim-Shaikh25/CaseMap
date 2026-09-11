# Requirements: ephemeral processing — results live on the client, not the server

**Date:** 2026-09-09
**Owner decision (same day):** when anyone uploads one or more documents, the system
processes the bundle and returns the processed data to the user's machine. The user
must be able to see that data locally. Uploaded PDFs (and any server-side working
copy) are removed after processing. **No case data is kept on the server after the
response is sent.**

**Read first:** `FORBIDDEN.md`, `AGENTS.md`, `THESIS.md`, `HEART.md`,
`docs/spec/SCOPE.md`, `docs/spec/ARCHITECTURE.md`.

This folder does **not** widen extraction/graph scope. It records a product constraint
on the still-unbuilt FastAPI/frontend layer (`HEART.md` tier 3). It is a **new**
requirement folder (not a retrofit of `2026-09-09-verbatim-fallback-nodes/`).

## Problem

A hosted store of litigators' case PDFs and extracted graphs would be a retention
surface this project does not want: the owner instructed that processing is
transient and that the user's machine is the place of record after the run.

## Goal

- Accept a **multi-document** upload (a bundle).
- Run the existing extraction/graph pipeline on that bundle.
- Return the processed payload (graph JSON / evidence cards — the same shape
  `poc_run.py` already writes) to the client.
- Persist that payload **on the client** so the user can reopen and inspect it.
- Delete uploaded PDFs and any server temp files as soon as processing finishes
  (success or failure). The server does not keep a case database of user uploads.

## Explicit non-goals (this folder)

- **Not building the FastAPI/React Flow UI in this requirement's first tasks.**
  `HEART.md` tier 3 is still blocked until tier 1 (mandatory ML layer verified
  end-to-end) is proven. This folder records the constraint so that work, when it
  starts, cannot "accidentally" keep PDFs on disk or in SQLite as a product store.
- **Not cookies as the storage mechanism.** Cookies are too small for a case-map
  graph. Client persistence will be a browser store sized for JSON (IndexedDB or
  equivalent). Cookies may hold only a tiny session key if a future design needs
  one — never the graph.
- **Not a multi-tenant hosted SaaS** (`HEART.md` §2 explicitly not built). Ephemeral
  processing is compatible with a local or single-user service.
- **Not changing extraction rules.** Same verbatim-span, no-generative-LLM core.

## Functional requirements (bind future tier-3 work)

1. **FR1 — Multi-document ingest.** The processing entry point accepts more than one
   file in one request (a bundle), not only a single PDF.
2. **FR2 — Return processed data.** The HTTP (or CLI-equivalent) response body is the
   processed graph/evidence payload. The client does not need a second round-trip
   to "fetch the saved case" from the server.
3. **FR3 — Client-side persistence.** After the response, the client stores the
   payload locally so the user can see it again without the server holding it.
4. **FR4 — Server forgets.** After the response is sent (or on error), uploaded
   files and derived server artifacts for that request are deleted. No durable
   per-user case store. Existing `casemap.db` remains an **in-process / per-run**
   graph helper, not a product archive of user PDFs.
5. **FR5 — Honest failure.** If processing fails, still delete uploads; return an
   error, not a partial store on the server.

## Non-functional

- **NFR1 — HEART tier order.** Implementation of a web upload UI waits until tier 1
  is proven, unless the owner later dates an explicit skip-tier decision.
- **NFR2 — Cookie size.** Do not put graph JSON in cookies.

## Acceptance (when implementation is allowed)

A local process: upload ≥2 files → receive graph JSON → confirm the upload directory
is empty → reload the client from local storage and still see the graph. No FastAPI
implementation in this session; T1 of this folder is recording the constraint only.
