from typing import Generic, List
from fhirguard_core.types import ResourceType, OperationOutcomeSeverity
from fhirguard.metadata import Metadata
from abc import ABC, abstractmethod
from fhirguard_core.resources import OperationOutcomeIssue

class Validator(ABC, Generic[ResourceType]):
    def __init__(self, metadata: Metadata):
        self.metadata = metadata
        self.issues: List[OperationOutcomeIssue] = []

    @abstractmethod
    def validate(self, path: str, _resource: ResourceType | dict | str) -> bool:
        raise NotImplementedError()
    
    def _add_issue(
        self,
        severity: OperationOutcomeSeverity,
        code: str,
        diagnostics: str,
        location: List[str] = []
    ):
        self.issues.append(OperationOutcomeIssue.construct(
            severity=severity,
            code=code,
            diagnostics=diagnostics,
            location=location
        ))

    def _filter_issues(self, severity: OperationOutcomeSeverity):
        return [issue for issue in self.issues if issue.severity == severity]

    @property
    def is_valid(self) -> bool:
        return len(self.issues) == 0