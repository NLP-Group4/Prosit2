# Chat System Behavior (Current State)

This document describes how the Interius chat currently behaves across the frontend, interface routing layer, mock pipeline UI, persistence, and attachment/context handling.

It is intended as a pre-push reference so the team can see what is implemented, what is session-only, and what still needs wiring to the real orchestrator.

## Scope

This covers the current behavior in:

- `frontend/src/pages/ChatPage.jsx`
- `frontend/src/pages/ChatPage.css`
- `frontend/src/lib/interface.js`
- `frontend/src/lib/threadFileContext.js`
- `backend/app/agent/interface.py`
- `backend/app/api/routes/generate.py`
- Supabase tables `threads`, `messages`, and `message_attachments`

## High-Level Architecture

The chat currently has two runtime lanes:

1. Interface / conversation lane (lightweight)
2. Build / generation lane (mock pipeline UI for now)

### Interface lane

The frontend sends each user prompt to:

- `POST /api/v1/generate/interface`

The backend `InterfaceAgent` decides whether the prompt should:

- be answered directly in chat (`should_trigger_pipeline=false`)
- trigger the generation pipeline (`should_trigger_pipeline=true`)

### Build lane (current frontend behavior)

When `should_trigger_pipeline=true`, the frontend:

- shows the interface acknowledgment message (assistant reply)
- then runs the existing mock pipeline UI (thought process + generated files + deploy/test actions)

The real orchestrator pipeline is not yet wired into the frontend build flow. The backend interface route is live and working; the frontend build path still uses mock generation visuals/output.

## Message Types and Rendering

Current persisted chat message roles:

- `user`
- `assistant`
- `agent`

### Meaning

- `user`: human prompts
- `assistant`: interface agent conversational reply / routing acknowledgment
- `agent`: pipeline result message (rendered as the build card)

### Rendering behavior

- `assistant` messages render as normal assistant chat bubbles.
- `agent` messages render as the richer generation/pipeline card.
- If an `assistant` acknowledgment is immediately followed by an `agent` pipeline result, the UI groups them visually to avoid a double-avatar feel and suppress duplicate narrative text.

## Thread Behavior

### Thread creation

- A new thread is created when the user sends a message and no active thread exists.
- Initial title is generated from the first prompt.

### Active thread persistence

The selected thread is persisted in:

- `localStorage` key: `interius_active_thread`

This supports reload returning to the same thread.

### Thread loading UX

When switching threads or reloading:

- the chat shows a loading state (`Loading thread…`)
- it no longer flashes the chat home/empty state first

### Thread rename (manual)

Sidebar thread titles can be renamed inline:

- hover thread row
- click rename icon
- `Enter` to save
- `Esc` to cancel

### Thread rename (automatic on first real build request)

If a thread starts with small talk (e.g., `hello`) and later receives its first build-triggering prompt:

- the thread title is auto-renamed from that first build request

This only happens once per thread (before any prior `agent` build result exists), so follow-up prompts like file retrieval requests do not keep changing the title.

## Login / Navigation Behavior

Authenticated navigation behavior was improved to avoid shaky browser-back transitions:

- login navigation uses `replace`, not push
- authenticated users visiting `/` are redirected to `/chat`

This prevents the browser back button from frequently landing on the marketing homepage during an active session.

## Interface Agent Behavior

Backend file:

- `backend/app/agent/interface.py`

### Role

The interface agent acts as:

- conversational assistant (for non-build prompts)
- intent router (for build prompts)

### Output shape

The interface route returns an `InterfaceDecision` with:

- `intent`
- `should_trigger_pipeline`
- `assistant_reply`
- `pipeline_prompt` (for build triggers)

### Fallback behavior

If the interface agent route fails (backend route exception):

- backend returns a safe pipeline fallback decision

If the frontend cannot reach the interface route (backend down):

- frontend falls back to mock pipeline path

### Identity / tone

The agent is instructed to speak as Interius, but:

- it should not prefix responses with `Interius:`
- any label-like `Interius:` prefix is stripped before sending to UI

## Build vs Conversation Flow

### Non-build prompt (`should_trigger_pipeline=false`)

Frontend behavior:

1. user message is shown and persisted
2. interface route returns direct reply
3. assistant reply is shown and persisted
4. no pipeline UI runs

### Build prompt (`should_trigger_pipeline=true`)

Frontend behavior:

1. user message is shown and persisted
2. interface route returns acknowledgment + routing decision
3. assistant acknowledgment is shown and persisted
4. mock pipeline card is shown and runs
5. final `agent` pipeline result is persisted

## Chat Persistence Model

### Supabase (long-term persistence)

Persisted:

- `threads`
- `messages`
- `message_attachments` (metadata only)

Not persisted yet:

- parsed attachment contents
- transient pipeline streaming steps/thought-process state

### Local browser persistence

#### `localStorage`

- `interius_active_thread` (active thread selection)

#### `sessionStorage` (temporary)

Used for interface/build context helpers only.

1. Interface conversation context cache (per thread)
2. Thread file context cache (per thread, includes parsed text when available)

## Attachment Handling (Current Design)

This is intentionally split into:

1. Attachment metadata (persistent)
2. Attachment content (ephemeral/session-local)

### Why

This keeps the UX honest and lightweight:

- the app can show historical attachments after reload
- Interius does not pretend it still has file contents if the session cache is gone

## `message_attachments` (metadata-only persistence)

Supabase table:

- `message_attachments`

Stored fields include:

- `thread_id`
- `message_id`
- `user_id`
- `original_name`
- `mime_type`
- `size_bytes`
- `created_at`

This supports:

- showing attachment chips after reload/thread reopen
- informing the interface agent that a file existed (metadata awareness)

It does not store raw file content.

## Thread File Context Cache (Session-Local)

Frontend file:

- `frontend/src/lib/threadFileContext.js`

This stores temporary, per-thread file context in `sessionStorage`.

### What is stored

Per file (session-local):

- file metadata (name/type/size)
- `has_text_content`
- `text_excerpt` (capped)
- `text_content` (capped, for future build handoff)

### TTL / lifecycle

TTL is currently:

- `30 minutes`

It is also cleared on:

- logout
- thread delete

It will also disappear when the browser tab/window session ends (normal `sessionStorage` behavior).

### Important nuance

- A same-tab page refresh usually keeps `sessionStorage`
- Closing the tab/window ends the session and removes the parsed file content cache

## File Parsing Behavior (Current)

### Text-like files (works now)

The frontend parses text-like files in-browser and stores capped text in the thread file context cache.

Examples:

- `.txt`
- `.md`
- `.json`
- `.csv`
- `.py`
- `.js`
- `.ts`
- `.sql`
- etc.

### PDF files (partially works now)

PDF parsing is implemented client-side using `pdfjs-dist` and works when the PDF has an embedded/selectable text layer.

Supported now:

- text-based PDFs
- mixed PDFs (text + graphics), text portions can be extracted

Not fully supported yet:

- scanned/image-only PDFs (no text layer)
- OCR is not implemented

When PDF text extraction fails or no text exists:

- Interius still knows the PDF metadata
- Interius may ask the user to re-upload or paste the relevant section if content is needed

## Interface Agent Context Inputs (Current)

The interface route now receives three inputs from the frontend:

1. `prompt`
2. `recent_messages` (conversation context)
3. `attachment_summaries` (lightweight file context only)

### Attachment summaries contain

- filename
- mime type
- size
- `has_text_content`
- short excerpt (when available)

The interface agent does not receive full raw file contents.

## Orchestrator Build Context (Current vs Planned)

### Current state

When a build is triggered, the frontend can already retrieve thread file context from:

- `getThreadBuildContextFiles(threadId)`

This includes capped `text_content` for files parsed in the current session.

However, this is only a placeholder hook right now. The real orchestrator request payload is not yet wired to consume these files in the frontend flow.

### Planned

On real orchestrator wiring, build requests should receive:

- `pipeline_prompt`
- `thread_context_files`
  - filename
  - mime type
  - size
  - `has_text_content`
  - `text_content` (when available)

This keeps the interface agent lightweight while allowing the orchestrator to use richer file context.

## Honest UX Rules (Implemented Direction)

The current direction is intentionally honest:

- if content exists in the current session cache, Interius can use it
- if only metadata exists (e.g., after a new session), Interius should say so and ask for re-upload/paste if needed

This avoids pretending the system still has file contents when it only has metadata.

## Attachment-Only Sends

If a user sends attachments without text:

- a placeholder user message is shown: `Attached context files.`
- files are recorded in thread file context and metadata persistence
- the interface agent responds acknowledging that files were attached as thread context

This allows a later build prompt to reuse the attached context (if still in session).

## Current UX Improvements Already in Place (Chat)

Not exhaustive, but relevant to behavior:

- thread switch/reload no longer flashes chat home
- user message wrapping fixed (no forced weird line breaks on short text)
- composer height resets after send
- thought process panel auto-closes after completion
- build acknowledgment + pipeline card duplicate message/avatar behavior reduced
- assistant avatars use the Interius mini mark

## Known Limitations (Current)

1. Real orchestrator integration is not yet wired in the frontend build path (mock pipeline still used)
2. Parsed file content is session-local only (by design for now)
3. PDF OCR is not implemented (image/scanned PDFs remain metadata-only)
4. Attachment content is not persisted to Supabase storage yet
5. Streaming thought-process state is UI simulation only (historical agent messages are reconstructed as completed)

## Recommended Next Steps

### High impact / low risk

1. Wire `thread_context_files` into the real orchestrator build payload
2. Add an explicit UI indicator per attachment:
   - `Parsed text available`
   - `Metadata only`
3. Add PDF OCR fallback (optional, later) for scanned PDFs

### Medium term

1. Add interface action types:
   - `chat`
   - `build`
   - `artifact_retrieval`
   - later `partial_pipeline` / `resume`
2. Add orchestrator execution plan support (`skip_stages`, reuse prior artifacts)

## Supabase Schema Notes (Delta Already Applied)

Current chat implementation assumes:

- `messages.role` allows `assistant`
- `message_attachments` table exists with RLS policies

If the app shows warnings about missing `message_attachments`, it usually means the SQL delta was not applied in the current Supabase project.

## Quick Manual Test Checklist

### Conversation routing

1. Send `hello`
2. Expect direct assistant reply (no pipeline card)

### Build routing

1. Send a build prompt
2. Expect assistant acknowledgment
3. Expect mock pipeline card after acknowledgment

### Text file context (same session)

1. Attach `.txt` file with useful content
2. Send a follow-up asking about the file
3. Expect more context-aware response

### Metadata-only behavior (after new session / TTL expiry)

1. Attach file and send
2. Reload in a new session (or wait for TTL / close tab)
3. Reopen thread
4. Attachment chips should still appear (metadata)
5. Ask Interius to use/read the file
6. Expect honest clarification / re-upload request if content is unavailable

### PDF behavior

1. Attach a text-based PDF
2. Ask a question based on it
3. If PDF has a real text layer, context may work in-session
4. If it is scanned/image-only, expect metadata-only fallback behavior

