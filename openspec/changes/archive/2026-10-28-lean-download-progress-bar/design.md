# Design: Lean 4 Download Progress Bar

## Context

During `npx mathtrace` installation, the installer provisions the pinned Lean 4 toolchain by executing `lib/bootstrap.py` via Node's subprocess runner. In `mathtrace/toolchain.py`, `urllib.request.urlopen` retrieves the ~742 MB distribution ZIP in 1 MB chunks without writing any status to the terminal. Node's `exec` helper in `npm/lib/prerequisites.cjs` buffers stderr by default. Together, these cause 60-120 seconds of silence where the terminal appears completely frozen on:
`-> Provisioning Lean 4 verification engine (v4.30.0)...`

## Goals / Non-Goals

**Goals:**
- Provide a responsive, real-time download progress bar in `mathtrace/toolchain.py` displaying percentage, transferred MB / total MB, transfer rate (MB/s), and elapsed/ETA time.
- Stream stderr live from the Python provisioning process to the user's terminal while maintaining isolated JSON stdout communication for the Node installer IPC.
- Ensure the progress presentation is visually appealing, responsive, and robust across interactive TTYs, Windows cmd/PowerShell, and non-interactive CI environments.
- Maintain zero new external npm or pip dependencies.

**Non-Goals:**
- Cross-project global caching (explicitly discarded to preserve strict mathematical isolation and prevent local tampering).
- Altering the official GitHub release URL, checksum verification, or archive extraction invariants.

## Decisions

### Decision 1: Progress rendering to stderr via Python standard library
- **Choice**: Compute download metrics in Python's download loop and write formatted progress lines to `sys.stderr` using `\r` (carriage return).
- **Rationale**: Keeps `sys.stdout` clean for JSON payload serialization (`print(json.dumps(result))`), which Node parses. Stderr is standard for CLI diagnostic and progress output.
- **Alternatives considered**:
  - Node-side download: Moving the download entirely to Node.js would duplicate URL signing, platform detection, and digest checking logic already verified in `mathtrace/toolchain.py`.
  - External libraries (`tqdm`, `rich`): Rejected to preserve zero-dependency distribution.

### Decision 2: Rate calculation and redraw throttling
- **Choice**: Throttle progress bar redraws to at most 5-10 updates per second (interval >= 0.1s).
- **Rationale**: Unthrottled redraws on high-speed connections can saturate terminal buffers and increase CPU usage during network I/O.
- **Format**:
  ```text
  [████████████████████░░░░░░░░░░░░░░░░░░] 52% (385.8 MB / 741.9 MB) 14.2 MB/s [00:25]
  ```
  Fallback for non-TTY / CI: Emit periodic status lines without `\r` (e.g. at 25%, 50%, 75%, 100%).

### Decision 3: Subprocess stderr inheritance in Node installer
- **Choice**: Pass `stdio: ['pipe', 'pipe', 'inherit']` (or equivalent live stderr streaming) in `npm/lib/install.cjs` when invoking `lib/bootstrap.py` for toolchain provisioning.
- **Rationale**: Ensures progress updates reach the user's terminal instantly without being buffered until process termination, while `stdout` remains safely captured as `'pipe'` for JSON parsing.

## Risks / Trade-offs

- **[Risk] Terminal width overflow in narrow windows** → **Mitigation**: Constrain the bar graphic to 24 characters and limit total line width to < 76 characters, ensuring it fits cleanly on standard 80-column terminals.
- **[Risk] Missing `Content-Length` header from GitHub CDN** → **Mitigation**: If `Content-Length` is missing or invalid, display an indeterminate downloaded megabytes counter (`X.X MB downloaded [Y MB/s]`) instead of crashing or showing invalid percentages.
- **[Risk] Windows terminal encoding differences** → **Mitigation**: Use standard ASCII-compatible or UTF-8 safe block characters (`#` / `=` or standard unicode blocks with ASCII fallback) that render reliably across Windows PowerShell and cmd.exe.
