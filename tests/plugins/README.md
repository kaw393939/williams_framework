# Plugin & Prompt Test Utilities

## Stub Plugin (`tests.plugins.stubs`)
- `make_stub_plugin()` returns a deterministic plugin with identity `tests.stub.plugin`.
- Each hook (`on_load`, `before_store`) records calls in `plugin.history` and returns a `HookResult` namedtuple-like dataclass with `plugin_id`, `event`, and a payload dictionary.
- `on_load` echoes the provided context and annotates it with `status="ok"`.
- `before_store` returns a copy of the content with `"stubbed"` appended to the `tags` list while leaving the original input untouched.

Use this stub to satisfy future lifecycle tests without depending on real plugin implementations.

## Prompt Snapshots (`tests.plugins.prompts`)
- `load_prompt_snapshot(name)` loads prompt text from `tests/fixtures/prompts/{name}.prompt`, computes a SHA-256 checksum, and caches the result for repeated calls.
- Returns a `PromptSnapshot` dataclass including `name`, `content`, `checksum`, and the underlying `path`.
- Missing snapshot names raise `FileNotFoundError` with the resolved path for debugging.

Available snapshots:
- `summarize` → deterministic multi-line prompt used by presentation and pipeline tests.
