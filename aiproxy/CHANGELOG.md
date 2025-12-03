# Changelog

## 0.3.0 — 2025-12-03

Added
- Per-user LaunchAgent installation flow (no root required).
- CLI flags: `--uninstall-service` and `--restart-service`.
- Modern `launchctl` usage: `bootstrap`, `enable`, and `kickstart` to reliably register, persist, and start the agent.
- Service documentation in `README.md` (install, restart, uninstall, status, and logs).

Changed
- Renamed plist template to `com.github.olafgeibig.tools.aiproxy.plist` to match the service label.
- Removed `UserName` key and switched from LaunchDaemon to per-user LaunchAgent.
- Aligned `StandardOutPath` and `StandardErrorPath` with `platformdirs.user_log_dir("aiproxy")` and substituted paths during install.
- Updated installer to write the plist to `~/Library/LaunchAgents` and manage the agent with `launchctl`.

Notes
- This release focuses on a simpler, non-root service setup using LaunchAgents.
- Previous release `0.2.0` used a root-installed LaunchDaemon with hard-coded `/var/log` paths; those are replaced by platformdirs-based user log locations.
