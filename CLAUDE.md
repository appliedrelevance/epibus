# EPIBUS Development Guide

## Commands
- **Run all tests**: `python -m unittest discover epibus.tests`
- **Run single test**: `python -m epibus.tests.test_modbus_action_conditions`
- **Build frontend**: `cd frontend && npm run build`
- **Dev server**: `cd frontend && npm run start`
- **Lint Python**: Check configuration in pyproject.toml

## Code Style
- **Python**: 
  - Indentation: Tabs
  - Quotes: Double
  - Line length: 110
  - Naming: PascalCase (classes), snake_case (functions/variables)
  - Imports: stdlib → third-party → local
  - Error handling: Use EpinomyLogger for exceptions

- **TypeScript**: 
  - Indentation: 2 spaces
  - Quotes: Single
  - Components: Functional with TypeScript interfaces
  - Naming: PascalCase (components), camelCase (functions/variables)
  - Error handling: Use try/catch with state management

## Architecture
Refer to `/doc/Epibus Architecture.md` for detailed system design documentation.