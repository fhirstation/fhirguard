from typing import List

from fhirguard_core.resources import Element, Resource


def query_resource(
    resource: Resource | Element, path: str
) -> List[Resource | Element | str]:
    """Query a resource using a FHIRPath pattern"""

    if not path:
        return [resource]

    labels = path.split(".")

    return _recursive_query(labels, resource)


def _recursive_query(
    labels: list[str], resource: Resource | Element
) -> List[Resource | Element | str]:
    """"""
    if not labels:
        return [resource]

    label = labels.pop(0)

    child_resource = getattr(resource, label, None)

    if not child_resource and isinstance(resource, dict):
        child_resource = resource.get(label, None)

    if not child_resource:
        return []

    if isinstance(child_resource, list):
        results = []
        for item in child_resource:
            results.extend(_recursive_query(labels.copy(), item))

        return results

    if len(labels) == 0:
        return [child_resource]

    return _recursive_query(labels, child_resource)
