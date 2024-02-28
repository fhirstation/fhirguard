import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from pydantic import BaseModel, Field
from rich.table import Table

from fhirguard_cli.util import get_package_path
from fhirguard_core.resources import (
    CodeSystem,
    CompartmentDefinition,
    ConceptMap,
    NamingSystem,
    OperationDefinition,
    Resource,
    SearchParameter,
    StructureDefinition,
    StructureMap,
    ValueSet,
)


class PackageResources(BaseModel):
    """A collection of resources from a FHIR package"""

    id: str
    code_systems: Dict[str, CodeSystem] = Field(..., alias="CodeSystem")
    value_sets: Dict[str, ValueSet] = Field(..., alias="ValueSet")
    concept_maps: Dict[str, ConceptMap] = Field(..., alias="ConceptMap")
    search_parameters: Dict[str, SearchParameter] = Field(..., alias="SearchParameter")
    structure_definitions: Dict[str, StructureDefinition] = Field(
        ..., alias="StructureDefinition"
    )
    operation_definitions: Dict[str, OperationDefinition] = Field(
        ..., alias="OperationDefinition"
    )
    compartment_definitions: Dict[str, CompartmentDefinition] = Field(
        ..., alias="CompartmentDefinition"
    )
    naming_systems: Dict[str, NamingSystem] = Field(..., alias="NamingSystem")
    structure_maps: Dict[str, StructureMap] = Field(..., alias="StructureMap")


class PackageResourcesFactory:
    """Factory for building PackageResources instances from a package"""

    def build(self, package: str) -> PackageResources:
        """Build a PackageResources instance"""
        package_path = get_package_path(package)
        package_id, resources = self._discover(package_path)
        return PackageResources.model_construct(**{"id": package_id, **resources})

    def _discover(
        self, package_path: Path
    ) -> Tuple[str, Dict[str, Dict[str, Resource]]]:
        """Discover relevant resources in a package"""
        package_json = json.loads((package_path / "package/package.json").read_text())
        package_id = f"{package_json['name']}@{package_json['version']}"

        resources = {
            "CodeSystem": {},
            "ValueSet": {},
            "ConceptMap": {},
            "SearchParameter": {},
            "StructureDefinition": {},
            "OperationDefinition": {},
            "CompartmentDefinition": {},
            "NamingSystem": {},
            "StructureMap": {},
        }

        for path in package_path.glob("**/*.json"):
            if resource := self._load_resource(path):
                resource_name = getattr(resource, "name", None)

                if "example" in path.name:
                    continue

                assert (
                    resource_name is not None
                ), f"Resource [cyan]{path.name}[/cyan] does not have a name"
                resources[resource.resource_type][resource_name] = resource

        return package_id, resources

    @staticmethod
    def _load_resource(path: Path) -> Resource | None:  # noqa
        """Load a resource from a path"""
        data = json.loads(path.read_text())
        match data.get("resourceType"):
            case "CodeSystem":
                return CodeSystem.construct(**data)

            case "ValueSet":
                return ValueSet.construct(**data)

            case "ConceptMap":
                return ConceptMap.construct(**data)

            case "SearchParameter":
                return SearchParameter.construct(**data)

            case "StructureDefinition":
                return StructureDefinition.construct(**data)

            case "OperationDefinition":
                return OperationDefinition.construct(**data)

            case "CompartmentDefinition":
                return CompartmentDefinition.construct(**data)

            case "NamingSystem":
                return NamingSystem.construct(**data)

            case "StructureMap":
                return StructureMap.construct(**data)


class AvailableResources:
    """A collection of all available resources from multiple packages"""

    def __init__(self, packages: List[str]):
        self._packages: Dict[str, PackageResources] = {}
        self._load_packages(packages)

    def _load_packages(self, packages: List[str]):
        """Load all packages into memory"""
        factory = PackageResourcesFactory()
        for package in packages:
            package_resources = factory.build(package)
            self._packages[package] = package_resources

    def filter_codesystems(
        self,
        package_id: str | None = None,
        resource_id: str | None = None,
        url: str | None = None,
        value_set: str | None = None,
    ) -> Iterable[CodeSystem]:
        """Filter CodeSystems by package, resource ID, URL, or value set"""
        for package in self._packages.values():
            if package_id is not None and package_id != package.id:
                continue

            for codesystem in package.code_systems.values():
                if resource_id is not None and resource_id != codesystem.id:
                    continue

                if url is not None and url != codesystem.url:
                    continue

                if value_set is not None and value_set not in codesystem.valueSet:
                    continue

                yield codesystem

    def filter_valuesets(
        self,
        package_id: str | None = None,
        resource_id: str | None = None,
        url: str | None = None,
    ) -> Iterable[ValueSet]:
        """Filter ValueSets by package, resource ID, or URL"""
        for package in self._packages.values():
            if package_id is not None and package_id != package.id:
                continue

            for valueset in package.value_sets.values():
                if resource_id is not None and resource_id != valueset.id:
                    continue

                if url is not None and url != valueset.url:
                    continue

                yield valueset

    @property
    def table(self):
        """Print stats about the loaded resources"""
        table = Table()
        table.add_column("Resource", justify="left", style="cyan")

        table_data = {
            "CodeSystem": {},
            "ValueSet": {},
            "ConceptMap": {},
            "SearchParameter": {},
            "StructureDefinition": {},
            "OperationDefinition": {},
            "CompartmentDefinition": {},
            "NamingSystem": {},
            "StructureMap": {},
        }

        for package_id, package in self._packages.items():
            table.add_column(package_id, justify="right", style="magenta")

            table_data["CodeSystem"][package_id] = len(package.code_systems.keys())
            table_data["ValueSet"][package_id] = len(package.value_sets.keys())
            table_data["ConceptMap"][package_id] = len(package.concept_maps.keys())
            table_data["SearchParameter"][package_id] = len(
                package.search_parameters.keys()
            )
            table_data["StructureDefinition"][package_id] = len(
                package.structure_definitions.keys()
            )
            table_data["OperationDefinition"][package_id] = len(
                package.operation_definitions.keys()
            )
            table_data["CompartmentDefinition"][package_id] = len(
                package.compartment_definitions.keys()
            )
            table_data["NamingSystem"][package_id] = len(package.naming_systems.keys())
            table_data["StructureMap"][package_id] = len(package.structure_maps.keys())

        for resource_type, package_counts in table_data.items():
            table.add_row(
                resource_type,
                *[str(package_counts.get(package, 0)) for package in self._packages],
            )

        return table
