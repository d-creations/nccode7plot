# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Added CGI segment `geometry`, `traversal`, and `sourceCode` metadata for rapid, linear, clockwise-arc, and counterclockwise-arc motions.

### Fixed
- Fixed configured G0 movements with nonzero duration being returned as normal linear-feed segments.

---

## [0.1.3] - 2026-08-11

### Fixed
- Fixed FANUC `M99` failing to terminate program execution, which could incorrectly execute later blocks such as unreachable `#3000` alarms.
- Fixed Siemens `M30` failing to terminate execution before subsequent program blocks.

### Added
- Added `FANUC_STAR_x-D_y-R_z_R.M.S` and `FANUC_STAR_x-D_y-D_z_R.M.S` controls for STAR two-channel programs using `.M` for the main channel and `.S` for the secondary channel.
- Added separate G96/G97 speed-mode handlers for FANUC Turn, FANUC Mill, and Siemens controls.
- Added configurable `g96_reference_axis` machine settings and Siemens `SCC[axis]` runtime reference-axis selection.
- Added Siemens G93 inverse-time feed and G961/G962/G971/G972/G973 constant-cutting-speed variants.
- Added FANUC Turn and STAR `G50 S...` maximum spindle-speed clamps.
- Added Siemens `G25` minimum, `G26` maximum, and indexed spindle-speed limits.
- Added Siemens `LIMS` spindle-speed limiting independently of persistent G25/G26 limits.

### Changed
- Constant-cutting-speed timing now derives effective RPM from cutting speed and the configured or programmed reference-axis diameter.
- Feed-per-revolution timing now applies controller-specific minimum and maximum spindle-speed limits.
- Siemens G96/G97 variants now select or preserve G94/G95 feed modes according to Siemens semantics.

### Fixed
- Fixed G96 cutting speed being interpreted directly as RPM during machining-time calculation.
- Fixed Siemens speed modes incorrectly reusing the FANUC Turn handler.
- Fixed Siemens `SCC[...]`, `LIMS=...`, and indexed spindle-limit parsing.
- Fixed G973 incorrectly inheriting an active `LIMS` clamp.

---

## [0.1.2] - 2026-07-29

### Added
- Added FANUC custom macro alarm support for `#3000 = n (ALARM MESSAGE)` across all FANUC machine controls.
- Added a dedicated Siemens user alarm handler for `SETAL(<alarm_no>[,"Alarm text"])` commands.
- Added structured alarm details to `state.extra["alarms"]`, including the alarm code, message, and source line.

### Changed
- FANUC `#3000` and Siemens `SETAL` user alarms now stop NC code execution and propagate through the existing structured error path.
- Siemens `SETAL` alarm handling is separated from the general Siemens built-in command handler.

### Fixed
- Preserved FANUC parenthesized alarm messages while continuing to discard ordinary FANUC comments.
- Added Siemens `SETAL` alarm-number validation and explicit errors for malformed syntax while allowing configured alarm numbers outside the standard user-alarm range.

---

## [0.1.1] - 2026-07-28

### Added
- Added machine-specific NC program lexers selected through `lexer_name` in the machine configuration.
- Added a language frontend that composes the configured lexer and command parser for each machine control.
- Added source-aware lexer statements that retain original line and column information.
- Added a lexer registry for integrating additional controller dialects without changing the execution engine.

### Changed
- Moved program splitting and comment processing out of `NCExecutionEngine` and the command parser interface into machine-specific lexers.
- Updated config-driven controls to construct their parser and lexer frontend from `machines.json`.
- Corrected the Siemens syntax-highlighting comment rule to use semicolon comments.

### Fixed
- Fixed Siemens lines beginning with `;` being split and executed as NC commands.
- Fixed Siemens inline comments while preserving semicolons inside quoted strings and `SETAL(...);message` alarm text.
- Fixed nested FANUC parenthesis comments and prevented semicolons inside comments or quoted strings from splitting commands.
- Fixed `POCKET4` depth calculation: `DP=0` with `DPR>0` now correctly uses the relative depth instead of silently producing zero depth.
- Fixed `POCKET4` ignoring the `MID` parameter; the cycle now steps down by `MID` per pass and mills concentric circles at each depth level.

---

## [0.1.0] - 2026-06-24

### Changed
- Improved Siemens 840DI control (`SIEMENS_840DI`) handling and simulation accuracy.

---

## [0.0.1] - initial release

### Added
- Initial release of `ncplot7py`.
- FANUC and Siemens-style NC program parsing and simulation.
- Toolpath segment generation for plotting.
- Single-channel and multi-channel machine configuration support.
- CGI adapter (`scripts/cgiserver.cgi`) for NC-Edit7 frontend integration.
