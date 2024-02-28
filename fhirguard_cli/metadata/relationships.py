from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, List, Tuple

import typer

from fhirguard_cli import log
from fhirguard_cli.metadata.discovery import AvailableResources
from fhirguard_core.resources import CodeSystem, ValueSet, fhirtypes
from fhirguard_core.types import ResourceType


class RelationshipMatcher(ABC, Generic[ResourceType]):
    def __init__(
        self,
        resources: AvailableResources,
        package_id: str,
        target_packages: List[str],
        reference_packages: List[str],
    ):
        self._resources = resources
        self._package_id = package_id
        self._target_packages = target_packages
        self._reference_packages = reference_packages

    @abstractmethod
    def match(self, resource: ResourceType):
        raise NotImplementedError

    def _find_codesystem(self, url: str):
        """Find a CodeSystem by URI"""

        # Check the target package first
        for codesystem in self._resources.filter_codesystems(
            package_id=self._package_id, url=url
        ):
            log.debug(
                f"Found CodeSystem '{codesystem.id}' with URL '{url}' in package '{self._package_id}'"
            )
            return codesystem

        # Check the other target packages second
        for id_ in self._target_packages:
            if id_ == self._package_id:
                continue

            for codesystem in self._resources.filter_codesystems(
                package_id=id_, url=url
            ):
                log.debug(
                    f"Found CodeSystem '{codesystem.id}' with URL '{url}' in package '{id_}'"
                )
                return codesystem

        # Check the reference packages
        for id_ in self._reference_packages:
            for codesystem in self._resources.filter_codesystems(
                package_id=id_, url=url
            ):
                log.debug(
                    f"Found CodeSystem '{codesystem.id}' with URL '{url}' in reference package '{id_}'"
                )
                return codesystem

        log.warn(f"CodeSystem with URL '[blue]{url}[/blue]' could not be identified")
        return None

    def _find_valueset(self, url: str):
        """Find a ValueSet by URI"""

        # Check the target package first
        for valueset in self._resources.filter_valuesets(
            package_id=self._package_id, url=url
        ):
            log.debug(
                f"Found ValueSet '{valueset.id}' with URL '{url}' in package '{self._package_id}'"
            )
            return valueset

        # Check the other target packages second
        for id_ in self._target_packages:
            if id_ == self._package_id:
                continue

            for valueset in self._resources.filter_valuesets(package_id=id_, url=url):
                log.debug(
                    f"Found ValueSet '{valueset.id}' with URL '{url}' in package '{id_}'"
                )
                return valueset

        # Check the reference packages
        for id_ in self._reference_packages:
            for valueset in self._resources.filter_valuesets(package_id=id_, url=url):
                log.debug(
                    f"Found ValueSet '{valueset.id}' with URL '{url}' in reference package '{id_}'"
                )
                return valueset

        log.warn(f"ValueSet with URL '[blue]{url}[/blue]' could not be identified")
        return None


class CodeSystemRelationshipMatcher(RelationshipMatcher[CodeSystem]):
    @dataclass
    class Relationship:
        resource: CodeSystem
        concepts: List[fhirtypes.CodeSystemConceptType]
        properties: List[fhirtypes.CodeSystemPropertyType]
        valueset: ValueSetRelationshipMatcher.Relationship | None

        def dict(self):
            return {
                "resource": self.resource.dict(),
                "concepts": self.concepts,
                "properties": self.properties,
            }

    def match(self, resource: CodeSystem):
        relationship = self.Relationship(
            resource=resource, concepts=[], properties=[], valueset=None
        )

        if resource.supplements:
            base_codesystem = self._find_codesystem(resource.supplements)
            if not base_codesystem:
                log.error(
                    f"CodeSystem '{resource.id}' has a supplement that could not be found"
                )
                log.print_json(resource.dict())
                raise typer.Exit(1)

            result = self.match(base_codesystem)
            relationship.concepts += result.concepts
            relationship.properties += result.properties

        if resource.concept:
            relationship.concepts += self._flatten_concepts(resource.concept)

        if resource.property:
            relationship.properties += resource.property

        if resource.valueSet:
            matcher = ValueSetRelationshipMatcher(
                self._resources,
                self._package_id,
                self._target_packages,
                self._reference_packages,
            )

            if valueset := self._find_valueset(resource.valueSet):
                relationship.valueset = matcher.match(valueset)

        return relationship

    def _flatten_concepts(
        self, concepts: List[fhirtypes.CodeSystemConceptType]
    ) -> List[fhirtypes.CodeSystemConceptType]:
        """
        Flatten the CodeSystem concepts
        """
        _concepts = []

        for concept in concepts:
            _concepts.append(concept)

            if children := concept.get("concept"):
                _concepts += self._flatten_concepts(children)

        return _concepts


class ValueSetRelationshipMatcher(RelationshipMatcher[ValueSet]):
    @dataclass
    class Relationship:
        resource: ValueSet
        codesystems: List[CodeSystem]
        concepts: List[fhirtypes.CodeSystemConceptType]
        includes: List[fhirtypes.ValueSetComposeIncludeType]
        contains: List[fhirtypes.ValueSetExpansionContainsType]

        def dict(self):
            return {
                "resource": self.resource.dict(),
                "codesystems": [cs.dict() for cs in self.codesystems],
                "concepts": self.concepts,
                "includes": self.includes,
                "contains": self.contains,
            }

    def match(self, resource: ValueSet):
        relationship = ValueSetRelationshipMatcher.Relationship(
            resource=resource, codesystems=[], concepts=[], includes=[], contains=[]
        )

        if resource.compose:
            includes, codesystems, concepts, contains = self._match_compose(
                resource.compose
            )
            relationship.codesystems += codesystems
            relationship.concepts += concepts
            relationship.includes += includes
            relationship.contains += contains

        if resource.expansion:
            codesystems, contains = self._match_expansion(resource.expansion)
            relationship.codesystems += codesystems
            relationship.contains += contains

        if not resource.compose and not resource.expansion:
            log.error(f"ValueSet '{resource.id}' has no compose or expansion")
            log.print_json(resource.dict())
            raise typer.Exit(1)

        return self._deduplicate_relationship(relationship)

    def _match_compose(self, compose: fhirtypes.ValueSetComposeType):
        """
        Match resources in a ValueSet's compose
        See http://hl7.org/fhir/R4B/valueset-definitions.html#ValueSet.compose
        """
        _codesystems: List[CodeSystem] = []
        _concepts: List[fhirtypes.CodeSystemConceptType] = []
        _includes: List[fhirtypes.ValueSetComposeIncludeType] = []
        _contains: List[fhirtypes.ValueSetExpansionContainsType] = []

        if includes := compose.get("include"):
            result = self._match_include(includes)
            _includes += result[0]
            _codesystems += result[1]
            _concepts += result[2]
            _contains += result[3]

        return _includes, _codesystems, _concepts, _contains

    def _match_include(self, includes: fhirtypes.ValueSetComposeIncludeType):
        """
        Match resources in a ValueSet's compose include
        See http://hl7.org/fhir/R4B/valueset-definitions.html
        """
        _codesystems: List[CodeSystem] = []
        _concepts: List[fhirtypes.CodeSystemConceptType] = []
        _includes: List[fhirtypes.ValueSetComposeIncludeType] = []
        _contains: List[fhirtypes.ValueSetExpansionContainsType] = []

        for include in includes:
            if include.get("system"):
                result = self._get_codesystem_related_resources(include)
                _includes += result[0]
                _codesystems += result[1]
                _concepts += result[2]

            if concepts := include.get("concept"):
                _concepts += concepts

            if value_set_urls := include.get("valueSet"):
                for url in value_set_urls:
                    for valueset in self._resources.filter_valuesets(
                        package_id=self._package_id, url=url
                    ):
                        results = self.match(valueset)
                        _codesystems += results.codesystems
                        _concepts += results.concepts
                        _includes += results.includes
                        _contains += results.contains

        return _includes, _codesystems, _concepts, _contains

    def _get_codesystem_related_resources(
        self, include: fhirtypes.ValueSetComposeIncludeType
    ):
        system: str = include["system"]

        _includes: List[fhirtypes.ValueSetComposeIncludeType] = []
        _codesystems: List[CodeSystem] = []
        _concepts: List[fhirtypes.CodeSystemConceptType] = []

        SUPPORTED_CODESYSTEMS = [
            "http://snomed.info/sct",
            "http://loinc.org",
            "https://dmd.nhs.uk",
            "urn:iso:std:iso:3166",
            "urn:iso:std:iso:3166:-2",
            "urn:ietf:bcp:47",
            "http://unitsofmeasure.org",
            "urn:ietf:rfc:3986",
            "urn:ietf:bcp:13",
            "urn:iso:std:iso:4217",
        ]

        if system in SUPPORTED_CODESYSTEMS:
            _includes.append(include)

        elif codesystem := self._find_codesystem(system):
            if (version := include.get("version")) and version != codesystem.version:
                log.warn(
                    f"Version mismatch for CodeSystem '{codesystem.id}' with system '{system}'"
                )

            if include.get("supplements"):
                log.warn("Supplements are not yet supported")

            if (concepts := include.get("concept")) and codesystem.concept:
                for concept in concepts:
                    _concepts += [
                        {**c, "system": system}
                        for c in self._filter_concepts_to_valueset(
                            codesystem.concept, concept
                        )
                    ]

            elif codesystem.concept:
                _concepts += [{**c, "system": system} for c in codesystem.concept]

            _codesystems.append(codesystem)

        return _includes, _codesystems, _concepts

    def _filter_concepts_to_valueset(
        self,
        codesystem_concepts: List[fhirtypes.CodeSystemConceptType],
        valueset_concept: fhirtypes.ValueSetComposeIncludeConceptType,
        _children: bool = False,
    ) -> List[fhirtypes.CodeSystemConceptType]:
        """
        Filters the given list of code system concepts based on the provided value set concept.
        """
        _concepts: List[fhirtypes.CodeSystemConceptType] = []

        for concept in codesystem_concepts:
            if concept.get("code") == valueset_concept.get("code") or _children:
                childless_concept: fhirtypes.CodeSystemConceptType = concept.copy()  # type: ignore
                children = childless_concept.pop("concept", None)

                _concepts.append(childless_concept)

                if children := concept.get("concept"):
                    _concepts += self._filter_concepts_to_valueset(
                        children, valueset_concept, True
                    )

        return _concepts

    def _match_expansion(
        self, expansion: fhirtypes.ValueSetExpansionType
    ) -> Tuple[List[CodeSystem], List[fhirtypes.ValueSetExpansionContainsType]]:
        """
        Match resources in a ValueSet's expansion
        """
        _codesystems: List[CodeSystem] = []

        if (total := expansion.get("total")) and total == 0:
            log.print_json(expansion)
            raise typer.Exit(0)

        for parameter in expansion.get("parameter", []):
            name = parameter.get("name")

            if name == "version":
                if not (versionUri := parameter.get("valueUri")):
                    continue

                if "snomed.info" in versionUri:
                    continue

                uri, _ = versionUri.split("|")
                if codesystem := self._find_codesystem(uri):
                    _codesystems.append(codesystem)

        return _codesystems, self._flatten_contains(expansion.get("contains", []))

    def _flatten_contains(self, contains: fhirtypes.ValueSetExpansionContainsType):
        """
        Flatten the ValueSet expansion contains
        """

        _contains = []

        for contain in contains:
            if not contain.get("abstract", False):
                _contains.append(contain)

            _contains += self._flatten_contains(contain.get("contains", []))

        return _contains

    @staticmethod
    def _deduplicate_relationship(relationship: Relationship) -> Relationship:
        """
        Remove duplicate resources from a relationship
        """
        deduped_relationship = ValueSetRelationshipMatcher.Relationship(
            resource=relationship.resource,
            codesystems=[],
            concepts=[],
            includes=[],
            contains=[],
        )

        for codesystem in relationship.codesystems:
            if codesystem not in deduped_relationship.codesystems:
                deduped_relationship.codesystems.append(codesystem)

        for concept in relationship.concepts:
            if concept not in deduped_relationship.concepts:
                deduped_relationship.concepts.append(concept)

        for include in relationship.includes:
            if include not in deduped_relationship.includes:
                deduped_relationship.includes.append(include)

        for contain in relationship.contains:
            if contain not in deduped_relationship.contains:
                deduped_relationship.contains.append(contain)

        return deduped_relationship
