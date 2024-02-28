import pycountry

from fhirguard.validators.validator import Validator
from fhirguard_core.resources import Coding


class CodingValidator(Validator[Coding]):
    def validate(
        self,
        path: str,
        resource: Coding | dict,
        valueset: str | None = None,
        codesystem: str | None = None,
    ) -> bool:
        if resource is None:
            self._add_issue(
                severity="error",
                code="code-invalid",
                diagnostics="Coding resource is missing or null",
                location=[path],
            )
            return False

        if not resource:
            self._add_issue(
                severity="error",
                code="code-invalid",
                diagnostics="Coding resource is empty",
                location=[path],
            )
            return False

        if not isinstance(resource, Coding) and not isinstance(resource, dict):
            self._add_issue(
                severity="error",
                code="code-invalid",
                diagnostics="Coding resource is not a valid FHIR Coding resource",
                location=[path],
            )
            return False

        if not isinstance(resource, Coding):
            resource = Coding.parse_obj(resource)

        if all([valueset, codesystem]):
            raise ValueError("Cannot specify both valueset and codesystem")

        if valueset:
            return self._validate_valueset(path, resource, valueset)

        return False

    def _validate_valueset(self, path: str, resource: Coding, valueset: str) -> bool:
        definition = self.metadata.get_valueset(valueset)

        if not definition:
            raise ValueError(f"Valueset not found: {valueset}")

        if resource.system and resource.system != definition["resource_url"]:
            self._add_issue(
                severity="error",
                code="code-invalid",
                diagnostics=f"Coding system '{resource.system}' does not match the expected system, expected: '{definition['resource_url']}'",
                location=[f"{path}.system"],
            )

        if all(
            value["system"] == "urn:ietf:bcp:47"
            for value in definition["allowed_values"]
        ):
            return self._validate_languages(path, resource, definition["resource_url"])

        matching_values = [
            value
            for value in definition["allowed_values"]
            if value["code"] == resource.code
        ]

        if not matching_values:
            display_matching_values = [
                value
                for value in definition["allowed_values"]
                if value["display"] == resource.display
            ]

            if len(display_matching_values) == 1:
                matching_value = display_matching_values[0]
                self._add_issue(
                    severity="warning",
                    code="code-invalid",
                    diagnostics=f"Coding resource code '{resource.code}' not found in valueset '{valueset}'. Did you mean '{matching_value['code']}'?",
                    location=[f"{path}.code"],
                )
                return False

            self._add_issue(
                severity="error",
                code="code-invalid",
                diagnostics=f"Coding resource code '{resource.code}' not found in valueset '{valueset}'",
                location=[f"{path}.code"],
            )
            return False

        if len(matching_values) > 1:
            raise NotImplementedError("Multiple matching values found")

        allowed_value = matching_values[0]

        if not resource.display:
            self._add_issue(
                severity="warning",
                code="code-invalid",
                diagnostics=f"Coding resource does not have a defined display, expected: '{allowed_value['display']}'",
                location=[f"{path}.display"],
            )

        if not resource.system:
            self._add_issue(
                severity="warning",
                code="code-invalid",
                diagnostics=f"Coding resource does not have a defined system, expected: '{definition['resource_url']}'",
                location=[f"{path}.system"],
            )

        if resource.display and allowed_value["display"] != resource.display:
            self._add_issue(
                severity="error",
                code="code-invalid",
                diagnostics=f"Coding resource display '{resource.display}' does not match the expected display, expected: '{allowed_value['display']}'",
                location=[f"{path}.display"],
            )

        return False

    def _validate_languages(self, path: str, resource: Coding, valueset: str) -> bool:
        """ """

        country_by_code = pycountry.languages.get(alpha_2=resource.code)
        country_by_display = pycountry.languages.get(name=resource.display)

        if not any([country_by_code, country_by_display]):
            self._add_issue(
                severity="error",
                code="code-invalid",
                diagnostics=f"Coding resource code '{resource.code}' not found in valueset '{valueset}'",
                location=[f"{path}.code"],
            )
            return False

        if country_by_code and not country_by_display:
            self._add_issue(
                severity="error",
                code="code-invalid",
                diagnostics=f"Coding resource display '{resource.display}' does not match the expected display, expected: '{country_by_code.name}'",
                location=[f"{path}.display"],
            )
            return False

        if country_by_display and not country_by_code:
            self._add_issue(
                severity="error",
                code="code-invalid",
                diagnostics=f"Coding resource code '{resource.code}' does not match the expected code, expected: '{country_by_display.alpha_2}'",
                location=[f"{path}.code"],
            )
            return False

        return True
