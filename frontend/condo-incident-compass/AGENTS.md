<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.

## What Lovable manages

Rules outside this block are the project's own. Change the pieces below in
Lovable, not by hand. With the [Lovable MCP](https://mcp.lovable.dev)
connected, `send_message` asks Lovable to do it; otherwise ask the user to
use the editor.

- **Database.** Do not add or edit `supabase/migrations/` or `drizzle/`.
  Ask Lovable to change the schema.
- **Generated files.** Do not edit a file whose header says it is automatically
  generated.
- **AI gateway.** Keep model calls on Lovable's gateway, and keep
  `LOVABLE_API_KEY` out of browser code.
- **Connectors.** Lovable provides native connectors. `list_connectors` shows
  which are enabled; `add_connector` only returns the dashboard link. When a
  connector is enabled, calls go through the connector gateway and need
  `LOVABLE_API_KEY`. When Lovable does not provide one, users can bring their
  own key and store it in Secrets.
- **Secrets.** Lovable manages them. Do not put secret values in the repo.
<!-- LOVABLE:END -->

## Project rules

- Occurrence logic (queue filtering/sorting/pagination, message parsing, and detail-page rules: risk words, priority change, decisions, conclusion, history) lives in pure functions in `src/lib/ocorrencias.ts` with tests beside it; UI components only call them — keeps rules testable without rendering.
- Queue data is in-code mock data behind a tiny in-memory store (`src/lib/ocorrencias-store.ts`); swap that store for a real backend without touching components.
- `/fila` keeps tab, filters and page in URL search params so returning from a card restores the view.
- The public resident form `/c/$identificador` uses only `src/lib/chamado.ts` (validation, phone mask, protocol, condo name from slug) and must not import dashboard modules — the two areas stay separate.
- Seeded mock history uses a fixed past timestamp (not `Date.now()`) so server and browser render identical dates; new events use the real time and must sort after seeds.
