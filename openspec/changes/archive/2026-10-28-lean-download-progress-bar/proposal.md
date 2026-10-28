# Proposal: Lean 4 Download Progress Bar

## Why

During `npx mathtrace` installation, provisioning the official Lean 4 toolchain requires downloading a ~742 MB archive (`lean-4.30.0-windows.zip` / `lean-4.30.0-linux.zip`) from GitHub Releases. Because the download currently executes through a synchronous unstreamed subprocess with no real-time byte or rate counters, the terminal appears stalled or frozen on `-> Provisioning Lean 4 verification engine (v4.30.0)...` for 1-2 minutes. Adding an interactive, real-time download progress bar with byte counts, percentage, speed, and ETA eliminates the perceived stall while keeping installation hermetic and self-contained.

## What Changes

- Add real-time streaming download progress reporting in `mathtrace/toolchain.py` during official Lean distribution archive downloads.
- Stream progress updates (bytes transferred, total size, percentage, transfer speed, and elapsed/ETA metrics) directly to stderr without buffering or waiting for subprocess termination.
- Update `npm/lib/install.cjs` and `npm/lib/prerequisites.cjs` to ensure child process stderr flows interactively to the terminal during toolchain provisioning without corrupting JSON IPC on stdout.
- Preserve zero external npm/pip dependencies by rendering the terminal progress bar using standard ANSI carriage returns and Python standard library capabilities.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `project-installation`: Enhance the `Visible provisioning progress` scenario under `Self-contained installation payload` to require continuous, interactive download progress indicators (transferred bytes, total bytes, transfer rate) rather than a single static pre-download message.

## Impact

- **Runtime & CLI**: `mathtrace/toolchain.py` (download loop and progress formatting), `npm/lib/install.cjs`, and `npm/lib/bootstrap.py`.
- **User Experience**: Terminal displays a dynamic, responsive progress bar showing download progress of the 742 MB Lean 4 archive.
- **Dependencies**: Zero new runtime dependencies; relies purely on standard library and ANSI terminal controls.
