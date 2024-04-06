# FHIRGuard

FHIRGuard is a Python library that validates FHIR resources using SIMPLIFIER.NET packages.

## Development Setup

### Install

This project uses the `asdf` package manager to manage runtime dependencies. See [asdf-vm.com](https://asdf-vm.com/guide/getting-started.html) for installation instructions.

```bash
# Install Runtime Dependencies
asdf plugin add python
asdf plugin add poetry
asdf install

# Install Python packages
poetry install
```

### Running Linting & Tests

Linting and formatting is performed using ruff. 

```bash
poetry run ruff format --diff
poetry run ruff check
```

Tests are run using Pytest.

```bash
poetry run pytest
```

### Build Project

The `poetry build` command will output a wheel and source in the `dist` directory. This can be installed using pip, and will expose the fhirguard, fhirguard_cli and fhirguard_core packages.

```bash
poetry build
```

## Credits

© Copyright HL7® logo, FHIR® logo and the flaming fire are registered trademarks owned by [Health Level Seven International](https://www.hl7.org/legal/trademarks.cfm).
