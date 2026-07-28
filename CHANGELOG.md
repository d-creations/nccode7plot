# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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
