from typing import List, Dict
from pathlib import Path
from fhirguard_core.resources import Coding, CodeableConcept, OperationOutcomeIssue

from typing import Any, List, Generic, Self
from fhirguard.metadata import Metadata
from fhirguard_core.types import ResourceType
from fhirguard.validators.coding import CodingValidator
from fhirguard.validators.code import CodeValidator
from fhirguard_core.filter import query_resource

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
        required: bool = False   
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
                        location=[path]
                    )
                )

            return self
        
        validator = CodeValidator(self._metadata)    

        for index, resource in enumerate(resources):
            assert isinstance(resource, str)

            child_path = f"{path}[{index}]" if len(resources) > 1 else path
            validator.validate(child_path, resource, valueset=valueset, codesystem=codesystem)

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
        required: bool = False
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
            if isinstance(resource, dict):
                resource = Coding.parse_obj(resource)
            
            assert isinstance(resource, Coding)

            child_path = f"{path}[{index}]" if len(resources) > 1 else path

            validator = CodingValidator(self._metadata)
            result = validator.validate(child_path, resource, valueset, codesystem)
            
            if result is False:
                if path not in self._issues:
                    self._issues[path] = []
                
                self._issues[path].extend(validator.issues)


        return self

    def codeable_concept(self, path: str, valueset: str | None = None, codesystem: str | None = None, required: bool = False) -> Self:
        """"""
        if not (resources := query_resource(self._resource, path)):
            if required:
                if path not in self._issues:
                    self._issues[path] = []

                self._issues[path].append(
                    OperationOutcomeIssue.construct(
                        severity="error",
                        code="code-invalid",
                        diagnostics="CodeableConcept resource is missing or null"
                    )
                )

            return self

        for resource_index, resource in enumerate(resources):
            if isinstance(resource, dict):
                resource = CodeableConcept.parse_obj(resource)

            assert isinstance(resource, CodeableConcept)

            for coding_index, coding in enumerate(resource.coding):
                child_path = f"{path}[{resource_index}].coding[{coding_index}]" if len(resources) > 1 else f"{path}.coding[{coding_index}]"

                validator = CodingValidator(self._metadata)
                result = validator.validate(child_path, coding, valueset, codesystem)

                if result is False:
                    if path not in self._issues:
                        self._issues[path] = []
                    
                    self._issues[path].extend(validator.issues)

        return self

    @property
    def issues(self) -> List[OperationOutcomeIssue]:
        return [
            issue for issues in self._issues.values()
            for issue in issues
        ]

    @property
    def is_valid(self) -> bool:
        return len([
            issue for issue in self.issues
            if issue.severity in ["error", "fatal"]            
        ]) == 0

    @property
    def has_warnings(self) -> bool:
        return len([issue for issue in self.issues if issue.severity in ["warning"]]) > 0

class FHIRGuard:
    """FHIRGuard is a class that provides a set of methods to validate FHIR resources."""

    def __init__(self, *metadata_paths: str | Path):
        """Initialize a new FHIRGuard instance."""
        self._metadata = Metadata(metadata_paths)

    def validator(self, resource: ResourceType) -> ValidatorStrategy:
        """Return a new instance of the Validator class."""
        return ValidatorStrategy(self._metadata, resource)
