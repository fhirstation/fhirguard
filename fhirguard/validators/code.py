from fhirguard.validators.validator import Validator


class CodeValidator(Validator):
    def validate(
        self,
        path: str,
        code: str,
        valueset: str | None = None,
        codesystem: str | None = None,
    ) -> bool:
        if not code:
            self._add_issue(
                severity="error",
                code="code-invalid",
                diagnostics="Code is missing, null or empty",
                location=[path],
            )
            return False

        if not isinstance(code, str):
            self._add_issue(
                severity="error",
                code="code-invalid",
                diagnostics="Code must be a valid string",
                location=[path],
            )
            return False

        if all([valueset, codesystem]):
            raise ValueError("Cannot specify both valueset and codesystem")

        if valueset:
            return self._validate_valueset(path, code, valueset)

        return False

    def _validate_valueset(self, path: str, code: str, valueset: str) -> bool:
        definition = self.metadata.get_valueset(valueset)

        if not definition:
            raise ValueError(f"Valueset not found: {valueset}")

        matching_values = [
            value for value in definition["allowed_values"] if value["code"] == code
        ]

        if not matching_values:
            self._add_issue(
                severity="error",
                code="code-invalid",
                diagnostics=f"Code '{code}' not found in valueset '{valueset}'",
                location=[path],
            )
            return False

        if len(matching_values) > 1:
            raise NotImplementedError("Multiple matching values found")

        return len(matching_values) == 1
