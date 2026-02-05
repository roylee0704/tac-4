# Chore: Switch to subscription-based execution for Claude Code

## Chore Description
Currently, the ADW system requires `ANTHROPIC_API_KEY` to run `claude -p` in programmatic mode, billing per token via the Anthropic API. However, `claude -p` also works with a logged-in Claude subscription (Max plan), using subscription tokens instead of API billing. This chore switches the ADW system to use the subscription-based auth by default (inheriting the parent environment), while making `ANTHROPIC_API_KEY` optional for users who still want API-key-based execution.

The key changes are:
1. Remove `ANTHROPIC_API_KEY` from required env var checks across all entry points.
2. Change `get_claude_env()` in `agent.py` to inherit the full parent environment (`env=None` behavior) instead of constructing a restricted env dict, so Claude Code can access its subscription auth config.
3. Update `.env.sample` and documentation to reflect that `ANTHROPIC_API_KEY` is now optional.
4. Update `health_check.py` to not require `ANTHROPIC_API_KEY` and always run the Claude Code connectivity test.

## Relevant Files
Use these files to resolve the chore:

- `adws/agent.py` — Contains `get_claude_env()` which builds a restricted env dict that explicitly passes `ANTHROPIC_API_KEY`. Also contains `prompt_claude_code()` which consumes the env. This is the core file that needs to change.
- `adws/adw_plan_build.py` — Contains `check_env_vars()` that requires `ANTHROPIC_API_KEY` and exits if missing. Needs to remove it from the required list.
- `adws/health_check.py` — Contains `check_env_vars()` that lists `ANTHROPIC_API_KEY` as required, and `run_health_check()` that skips the Claude Code test when the API key is absent. Both need updating.
- `.env.sample` — Documents `ANTHROPIC_API_KEY` as required for programmatic mode. Needs to be updated to mark it optional.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: Update `get_claude_env()` in `adws/agent.py` to inherit parent environment

- Change `get_claude_env()` (line 84) to return `None` instead of a restricted dict. When `subprocess.run` receives `env=None`, it inherits the full parent environment — this allows Claude Code to find its subscription auth config files (typically at `~/.claude/`).
- However, we still need to support the case where a user *does* set `ANTHROPIC_API_KEY` — in that case `claude -p` will automatically use it. No special handling needed since it will be inherited from the parent env.
- Update `prompt_claude_code()` (line 156): change `env = get_claude_env()` to `env = None` or call the updated function. The subprocess call at line 188 should pass `env=None` to inherit the full parent environment.
- Remove `get_claude_env()` entirely since it is no longer needed — passing `env=None` achieves the goal. If `ANTHROPIC_API_KEY` is set in the parent process (via `load_dotenv()` or shell export), it will be inherited automatically. If `GITHUB_PAT` is set, it's already in the parent env too.
- Remove the import/usage of `get_claude_env` within `prompt_claude_code()`.

### Step 2: Update `check_env_vars()` in `adws/adw_plan_build.py`

- Remove `"ANTHROPIC_API_KEY"` from the `required_vars` list at line 63.
- Keep `"CLAUDE_CODE_PATH"` in the required list (it already has a fallback default of `"claude"` elsewhere, but keeping it as a check is fine).
- Optionally: if the only remaining required var is `CLAUDE_CODE_PATH`, and it has a sensible default, consider whether the check is still needed. Since `CLAUDE_CODE_PATH` defaults to `"claude"` in `agent.py`, we can remove it from the required list too, leaving `required_vars` empty. In that case, `check_env_vars()` can remain but will simply never error (safe no-op), or be removed entirely. The simpler approach: just remove `"ANTHROPIC_API_KEY"` from the list.

### Step 3: Update `check_env_vars()` in `adws/health_check.py`

- Move `"ANTHROPIC_API_KEY"` from `required_vars` dict (line 64) to `optional_vars` dict (line 69).
- Update its description to: `"(Optional) Anthropic API Key - uses Claude subscription if not set"`

### Step 4: Update `run_health_check()` in `adws/health_check.py` to always test Claude Code

- Remove the `if os.getenv("ANTHROPIC_API_KEY"):` conditional guard at line 295 that currently skips the Claude Code test.
- Always run `check_claude_code()` regardless of whether the API key is present. The test itself (`claude -p "What is 2+2?"`) will work with either subscription auth or API key auth.
- Remove the `else` branch (lines 302-306) that creates a skipped CheckResult.

### Step 5: Update `.env.sample` to mark `ANTHROPIC_API_KEY` as optional

- Change the comment from `# Anthropic Configuration to run Claude Code in programmatic mode` to `# Anthropic Configuration (Optional) - if not set, Claude Code uses your subscription auth (claude login)`.
- This makes it clear to new users that the API key is optional.

### Step 6: Run validation commands

- Run the server tests to ensure no regressions.
- Manually verify `claude -p "What is 2+2?"` works without `ANTHROPIC_API_KEY` set (relies on subscription auth).

## Validation Commands
Execute every command to validate the chore is complete with zero regressions.

- `cd app/server && uv run pytest` - Run server tests to validate the chore is complete with zero regressions
- `cd adws && python -c "from agent import prompt_claude_code; print('import ok')"` - Verify agent.py still imports cleanly after removing `get_claude_env`
- `cd adws && python -c "from adw_plan_build import check_env_vars; print('import ok')"` - Verify adw_plan_build.py imports cleanly
- `cd adws && python -c "from health_check import check_env_vars; print('import ok')"` - Verify health_check.py imports cleanly

## Notes
- `claude -p` automatically detects auth: if `ANTHROPIC_API_KEY` is in the environment, it uses the API; otherwise, it falls back to the logged-in subscription session. No code changes are needed in the CLI invocation itself.
- Users who prefer API-key billing can still set `ANTHROPIC_API_KEY` in their `.env` — it will be inherited by the subprocess and `claude -p` will use it automatically.
- The `--dangerously-skip-permissions` flag works with both auth methods.
- This change means the local machine must have an active `claude` login session (via `claude login` or equivalent) for subscription mode to work. This is a reasonable assumption for a developer workstation.
