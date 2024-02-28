from typing import TypeVar, Literal
from fhirguard_core.resources import Resource, Element, fhirtypes

ResourceType = TypeVar("ResourceType", bound=Resource | Element)

OperationOutcomeSeverity = Literal["fatal", "error", "warning", "information"]