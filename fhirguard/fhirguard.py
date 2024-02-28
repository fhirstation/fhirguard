from pathlib import Path
from typing import Dict, Generic, List, Self

from fhirguard.metadata import Metadata
from fhirguard.validators.code import CodeValidator
from fhirguard.validators.coding import CodingValidator
from fhirguard_core.filter import query_resource
from fhirguard_core.resources import CodeableConcept, Coding, OperationOutcomeIssue
from fhirguard_core.types import ResourceType


class ValidatorStrategy(Generic[ResourceType]):
    def __init__(self, metadata: Metadata, resource: ResourceType):
        """"""
        self._metadata = metadata
        self._resource = resource
        self._issues: Dict[str, List[OperationOutcomeIssue]] = {}

    def code(
        self,
        path: str,
        valueset: str | None = None,
        codesystem: str | None = None,
        required: bool = False,
    ) -> Self:
        """"""
        if not (resources := query_resource(self._resource, path)):
            if required:
                if path not in self._issues:
                    self._issues[path] = []

                self._issues[path].append(
                    OperationOutcomeIssue.construct(
                        severity="error",
                        code="code-invalid",
                        diagnostics="Code resource is missing or null",
                        location=[path],
                    )
                )

            return self

        validator = CodeValidator(self._metadata)

        for index, resource in enumerate(resources):
            assert isinstance(resource, str)

            child_path = f"{path}[{index}]" if len(resources) > 1 else path
            validator.validate(
                child_path, resource, valueset=valueset, codesystem=codesystem
            )

        if not validator.is_valid:
            if path not in self.issues:
                self._issues[path] = []

            self._issues[path].extend(validator.issues)

        return self

    def coding(
        self,
        path: str,
        valueset: str | None = None,
        codesystem: str | None = None,
        required: bool = False,
    ) -> Self:
        """"""
        if not (resources := query_resource(self._resource, path)):
            if required:
                if path not in self._issues:
                    self._issues[path] = []

                self._issues[path].append(
                    OperationOutcomeIssue.construct(
                        severity="error",
                        code="code-invalid",
                        diagnostics="Coding resource is missing or null",
                    )
                )

            return self

        for index, resource in enumerate(resources):
            coding_resource = resource

            if isinstance(coding_resource, dict):
                coding_resource = Coding.parse_obj(coding_resource)

            assert isinstance(coding_resource, Coding)

            child_path = f"{path}[{index}]" if len(resources) > 1 else path

            validator = CodingValidator(self._metadata)
            result = validator.validate(
                child_path, coding_resource, valueset, codesystem
            )

            if result is False:
                if path not in self._issues:
                    self._issues[path] = []

                self._issues[path].extend(validator.issues)

        return self

    def codeable_concept(
        self,
        path: str,
        valueset: str | None = None,
        codesystem: str | None = None,
        required: bool = False,
    ) -> Self:
        """"""
        if not (resources := query_resource(self._resource, path)):
            if required:
                if path not in self._issues:
                    self._issues[path] = []

                self._issues[path].append(
                    OperationOutcomeIssue.construct(
                        severity="error",
                        code="code-invalid",
                        diagnostics="CodeableConcept resource is missing or null",
                    )
                )

            return self

        for resource_index, resource in enumerate(resources):
            concept = resource

            if isinstance(concept, dict):
                concept = CodeableConcept.parse_obj(resource)

            assert isinstance(concept, CodeableConcept)

            for coding_index, coding in enumerate(concept.coding):
                child_path = (
                    f"{path}[{resource_index}].coding[{coding_index}]"
                    if len(resources) > 1
                    else f"{path}.coding[{coding_index}]"
                )

                validator = CodingValidator(self._metadata)
                result = validator.validate(child_path, coding, valueset, codesystem)

                if result is False:
                    if path not in self._issues:
                        self._issues[path] = []

                    self._issues[path].extend(validator.issues)

        return self

    @property
    def issues(self) -> List[OperationOutcomeIssue]:
        return [issue for issues in self._issues.values() for issue in issues]

    @property
    def is_valid(self) -> bool:
        """Return True if the resource is valid, otherwise False."""
        invalid_severities = {"error", "fatal"}
        return all(issue.severity not in invalid_severities for issue in self.issues)

    @property
    def has_warnings(self) -> bool:
        """Return True if the resource has warnings, otherwise False."""
        return any(issue.severity == "warning" for issue in self.issues)


class FHIRGuard:
    """FHIRGuard is a class that provides a set of methods to validate FHIR resources."""

    def __init__(self, *metadata_paths: str | Path):
        """Initialize a new FHIRGuard instance."""
        self._metadata = Metadata(metadata_paths)

    def validator(self, resource: ResourceType) -> ValidatorStrategy:
        """Return a new instance of the Validator class."""
        return ValidatorStrategy(self._metadata, resource)
