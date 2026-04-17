---
name: git
description: Summarize today's repository work from local changes and git history, then create a commit and push the current branch. Use when the user wants a reusable git assistant flow such as "/git", "summarize and commit today's work", or "prepare a commit from today's changes and push it".
---

# Git Skill

Use this skill when the user wants Codex to package today's work into a clean git update.

## Workflow

1. Run `scripts/collect_git_context.sh` from the current repo root to gather:
   - current branch
   - local date used for "today"
   - `git status --short`
   - commits since local midnight
   - staged and unstaged diff stats
2. Read the output and summarize today's work in 2-5 short bullets before committing.
3. Inspect the worktree for unrelated changes.
4. Stage only the files relevant to today's requested work.
5. Write a concise commit message grounded in:
   - today's uncommitted changes
   - today's local commit history
   - the user's stated goal
6. Create a non-interactive commit.
7. Push the current branch to its configured remote when the user asked to push.

## Guardrails

- Do not stage unrelated files just to make the worktree clean.
- If the worktree contains mixed changes and the relevant subset is unclear, stop and ask the user which files should be included.
- Prefer `git status`, `git diff --stat`, `git diff --cached --stat`, and `git log --since=...` over free-form guesses.
- Prefer non-interactive git commands only.
- Never amend, reset, or force-push unless the user explicitly asks.
- If there are no staged or unstaged changes, still summarize today's commits and tell the user there is nothing new to commit.

## Commit Message Style

- Use one concise subject line.
- Keep it specific to user-visible or developer-visible changes.
- Good examples:
  - `refactor clarification state handling`
  - `add local skill loading and note retrieval tools`
  - `improve note dispatch and follow-up routing`

## Invocation Notes

- In Codex, invoke this skill explicitly as `$git`.
- If the client does not support slash commands, use `$git` instead of `/git`.

