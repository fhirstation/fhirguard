from typing import Literal, TypeVar

from fhirguard_core.resources import Element, Resource

ResourceType = TypeVar("ResourceType", bound=Resource | Element)

OperationOutcomeSeverity = Literal["fatal", "error", "warning", "information"]
