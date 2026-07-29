# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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
