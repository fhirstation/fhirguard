import hashlib
import json
from pathlib import Path
from shutil import rmtree
from typing import Dict, List, Literal
from uuid import uuid4

import rich.progress
import typer
from pydantic import BaseModel

from fhirguard_cli import log
from fhirguard_cli.log import console
from fhirguard_cli.metadata.discovery import AvailableResources
from fhirguard_cli.metadata.relationships import (
    CodeSystemRelationshipMatcher,
    ValueSetRelationshipMatcher,
)

app = typer.Typer()


class ValueSetDefinitionAllowedValue(BaseModel):
    code: str
    type: List[Literal["concept", "include", "contains"]]
    system: str | None
    display: str | None
    description: str | None
    filter: List[dict] | None


class ValueSetDefinition(BaseModel):
    name: str
    resource_id: str
    resource_url: str
    compose: dict | None
    description: str | None
    related_codesystems: List[dict]
    allowed_values: List[ValueSetDefinitionAllowedValue]

    @property
    def hash(self):
        return hashlib.sha256(self.model_dump_json().encode("utf-8")).hexdigest()[:16]


class CodeSystemDefinition(BaseModel):
    name: str
    resource_id: str
    resource_url: str
    filter: List[dict] | None
    concepts: List[dict]
    properties: List[dict]
    valueset: ValueSetDefinition | None

    @property
    def hash(self):
        return hashlib.sha256(self.model_dump_json().encode("utf-8")).hexdigest()[:16]


class Definition(BaseModel):
    valuesets: List[ValueSetDefinition]
    codesystems: List[CodeSystemDefinition]

    def add_valueset(self, relationship: ValueSetRelationshipMatcher.Relationship):
        self.valuesets.append(self._convert_valueset(relationship))

    def _convert_valueset(self, relationship: ValueSetRelationshipMatcher.Relationship):
        valueset_definition = ValueSetDefinition(
            name=relationship.resource.name,
            resource_id=relationship.resource.id or relationship.resource.name,
            resource_url=relationship.resource.url,
            compose=relationship.resource.compose,
            description=relationship.resource.description,
            related_codesystems=[],
            allowed_values=[],
        )

        for concept in relationship.concepts:
            value = ValueSetDefinitionAllowedValue(
                type=["concept"],
                code=concept["code"],
                display=concept.get("display"),
                description=concept.get("definition"),
                filter=None,
                system=concept.get("system"),
            )

            if value not in valueset_definition.allowed_values:
                valueset_definition.allowed_values.append(value)

        for include in relationship.includes:
            value = ValueSetDefinitionAllowedValue(
                type=["include"],
                code=include["system"],
                system=include["system"],
                display=include["system"],
                description=include.get("version"),
                filter=include.get("filter"),
            )
            if value not in valueset_definition.allowed_values:
                valueset_definition.allowed_values.append(value)

        for contains in relationship.contains:
            value = ValueSetDefinitionAllowedValue(
                type=["contains"],
                code=contains["code"],
                system=contains.get("system"),
                description=None,
                filter=None,
                display=contains.get("display"),
            )
            if value not in valueset_definition.allowed_values:
                valueset_definition.allowed_values.append(value)

        for codesystem in relationship.codesystems:
            valueset_definition.related_codesystems.append(
                {"id": codesystem.id, "url": codesystem.url}
            )

        return self._deduplicate_valueset(valueset_definition)

    @staticmethod
    def _deduplicate_valueset(definition: ValueSetDefinition) -> ValueSetDefinition:
        allowed_values: Dict[str, ValueSetDefinitionAllowedValue] = {}

        for value in definition.allowed_values:
            assert value.code is not None
            key = f"{value.code}::{value.system}"

            if key not in allowed_values:
                allowed_values[key] = value
                continue

            existing_value = allowed_values[key]

            value_fields = {
                k: v
                for k, v in value.model_dump().items()
                if v is not None and k != "type"
            }
            existing_fields = {
                k: v
                for k, v in existing_value.model_dump().items()
                if v is not None and k in value_fields
            }

            # If all fields match - merge the two objects
            if all(
                value_fields.get(k) == existing_fields.get(k) for k in existing_fields
            ):
                fields = {**existing_fields, **value_fields}
                allowed_values[key] = ValueSetDefinitionAllowedValue(
                    code=value.code,
                    type=list({*existing_value.type, *value.type}),
                    system=fields.get("system"),
                    display=fields.get("display"),
                    description=fields.get("description"),
                    filter=fields.get("filter"),
                )
                continue

            if all(
                [
                    value.type == ["include"],
                    existing_value.type == ["include"],
                    value.system == existing_value.system,
                    value.filter is not None,
                ]
            ):
                if not existing_value.filter:
                    existing_value.filter = []

                existing_value.filter.extend(value.filter or [])
                continue

            log.warn(
                f"Duplicate ValueSet definitions in '[blue]{definition.name}[/blue]' for code '[blue]{value.code}[/blue]'"
            )
            allowed_values[uuid4().hex] = value

        definition.allowed_values = list(allowed_values.values())
        return definition

    def add_codesystem(self, relationship: CodeSystemRelationshipMatcher.Relationship):
        resource_filter = relationship.resource.filter

        codesystem_definition = CodeSystemDefinition(
            name=relationship.resource.name,
            resource_id=relationship.resource.id or relationship.resource.name,
            resource_url=relationship.resource.url,
            filter=list(resource_filter) if resource_filter else None,
            concepts=list(relationship.concepts),
            properties=list(relationship.properties),
            valueset=self._convert_valueset(relationship.valueset)
            if relationship.valueset
            else None,
        )
        self.codesystems.append(codesystem_definition)

    def write(self, output_path: Path):
        """"""
        with rich.progress.Progress(
            rich.progress.SpinnerColumn(),
            rich.progress.TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console,
        ) as progress:
            task = progress.add_task("Writing Definition to Disk", total=1)
            manifest = {
                "valuesets": {"name": {}, "id": {}},
                "codesystems": {"name": {}, "id": {}},
            }

            if not output_path.exists():
                output_path.mkdir(parents=True)
            else:
                rmtree(output_path)
                output_path.mkdir()

            valueset_path = output_path / "valuesets"
            if not valueset_path.exists():
                valueset_path.mkdir()

            codesystem_path = output_path / "codesystems"
            if not codesystem_path.exists():
                codesystem_path.mkdir()

            for valueset in self.valuesets:
                valueset_file = valueset_path / f"{valueset.hash}.json"
                valueset_file.write_text(valueset.model_dump_json(indent=2))

                manifest["valuesets"]["name"][valueset.name] = valueset.hash
                manifest["valuesets"]["id"][valueset.resource_id] = valueset.hash

            for codesystem in self.codesystems:
                codesystem_file = codesystem_path / f"{codesystem.hash}.json"
                codesystem_file.write_text(codesystem.model_dump_json(indent=2))

                manifest["codesystems"]["name"][codesystem.name] = codesystem.hash
                manifest["codesystems"]["id"][codesystem.resource_id] = codesystem.hash

            manifest_file = output_path / "manifest.json"
            manifest_file.write_text(json.dumps(manifest, indent=2))

            progress.remove_task(task)

    @staticmethod
    def create():
        return Definition(valuesets=[], codesystems=[])


class DefinitionFactory:
    """"""

    def __init__(
        self,
        resources: AvailableResources,
        target_packages: List[str],
        reference_packages: List[str],
    ):
        self._resources = resources
        self._target_packages = target_packages
        self._reference_packages = reference_packages

    def generate(self):
        """"""
        definition = Definition.create()

        with rich.progress.Progress(
            rich.progress.SpinnerColumn(),
            rich.progress.TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console,
        ) as progress:
            task = progress.add_task("Generating CodeSystem Definitions", total=1)
            for relationship in self._match_codesystems():
                definition.add_codesystem(relationship)

            progress.remove_task(task)
            log.success(
                f"Generated {len(definition.codesystems)} CodeSystem Definitions"
            )

            task = progress.add_task("Generating ValueSet Definitions", total=None)
            for relationship in self._match_valuesets():
                definition.add_valueset(relationship)

            progress.remove_task(task)
            log.success(f"Generated {len(definition.valuesets)} ValueSet Definitions")

        return definition

    def _match_valuesets(self):
        """"""
        for package in self._target_packages:
            matcher = ValueSetRelationshipMatcher(
                self._resources,
                package,
                self._target_packages,
                self._reference_packages,
            )

            for resource in self._resources.filter_valuesets(package_id=package):
                yield matcher.match(resource)

    def _match_codesystems(self):
        for package in self._target_packages:
            matcher = CodeSystemRelationshipMatcher(
                self._resources,
                package,
                self._target_packages,
                self._reference_packages,
            )

            for resource in self._resources.filter_codesystems(package_id=package):
                yield matcher.match(resource)


@app.command()
def generate(
    packages: List[str] = typer.Argument(
        ..., help="SIMPLIFIER.NET Package to generate metadata for"
    ),
    reference: List[str] = typer.Option(
        [], help="SIMPLIFIER.NET Packages to use as references"
    ),
    output: Path = typer.Option(..., help="Output path for the definition"),
):
    """"""
    log.info("Discovering resources, this may take a moment...")
    resources = AvailableResources(packages=[*packages, *reference])

    log.success("Loaded all target and reference packages")
    log.print(resources.table)

    factory = DefinitionFactory(
        resources, target_packages=packages, reference_packages=reference
    )
    definition = factory.generate()

    definition.write(output)
