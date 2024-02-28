import pytest

from fhirguard.fhirguard import FHIRGuard
from fhirguard_core.resources import (
    BackboneElement,
    CodeableConcept,
    Coding,
    OperationOutcomeIssue,
    Patient,
)


@pytest.fixture()
def guard():
    return FHIRGuard("test_data/definitions/hl7.fhir.r4.core")


def test_patient_happy(guard: FHIRGuard):
    resource = Patient.construct(
        id="123",
        active=True,
        name=[{"family": "Simpson", "given": ["Homer"]}],
        gender="male",
        maritalStatus=Coding.construct(
            system="http://hl7.org/fhir/ValueSet/marital-status",
            code="M",
            display="Married",
        ),
        contact=BackboneElement.construct(
            name={
                "family": "Simpson",
                "given": ["Marge"],
            },
            gender="female",
            relationship=Coding.construct(
                system="http://hl7.org/fhir/ValueSet/patient-contactrelationship",
                code="N",
                display="Next-of-Kin",
            ),
        ),
        communication=BackboneElement.construct(
            language=CodeableConcept.construct(
                coding=[
                    Coding.construct(
                        system="http://hl7.org/fhir/ValueSet/all-languages",
                        code="en",
                        display="English",
                    )
                ],
                text="English",
            )
        ),
        link=[
            BackboneElement.construct(
                other={"reference": "Patient/1234"}, type="seealso"
            )
        ],
    )

    validator = (
        guard.validator(resource)
        .code("gender", valueset="AdministrativeGender")
        .coding("maritalStatus", valueset="marital-status")
        .code("contact.gender", valueset="AdministrativeGender")
        .coding("contact.relationship", valueset="PatientContactRelationship")
        .codeable_concept("communication.language", valueset="AllLanguages")
        .code("link.type", valueset="LinkType")
    )

    assert validator.is_valid is True
    assert validator.issues == []


def test_patient_validation(guard: FHIRGuard):
    resource = Patient.construct(
        id="123",
        active=True,
        name=[{"family": "Simpson", "given": ["Homer"]}],
        gender="goose",
        maritalStatus=Coding.construct(
            system="http://hl7.org/fhir/ValueSet/marriage-status",
            code="Married",
            display="Married",
        ),
        contact=BackboneElement.construct(
            name={
                "family": "Simpson",
                "given": ["Marge"],
            },
            gender="attackhelicopter",
            relationship=Coding.construct(
                system="http://hl7.org/fhir/ValueSet/patient-relationship",
                code="N",
                display="Partner",
            ),
        ),
        communication=BackboneElement.construct(
            language=CodeableConcept.construct(
                coding=[
                    Coding.construct(
                        system="http://hl7.org/fhir/ValueSet/languages",
                        code="eng",
                        display="English",
                    )
                ],
                text="English",
            )
        ),
        link=[
            BackboneElement.construct(
                other={"reference": "Patient/1234"}, type="seealsothisone"
            ),
            BackboneElement.construct(
                other={"reference": "Patient/1234"}, type="thisonetoo"
            ),
        ],
    )

    validator = (
        guard.validator(resource)
        .code("gender", valueset="AdministrativeGender")
        .coding("maritalStatus", valueset="marital-status")
        .code("contact.gender", valueset="AdministrativeGender")
        .coding("contact.relationship", valueset="PatientContactRelationship")
        .codeable_concept("communication.language", valueset="AllLanguages")
        .code("link.type", valueset="LinkType")
    )

    assert validator.is_valid is False
    assert validator.issues == [
        OperationOutcomeIssue.construct(
            code="code-invalid",
            diagnostics="Code 'goose' not found in valueset 'AdministrativeGender'",
            location=["gender"],
            severity="error",
        ),
        OperationOutcomeIssue.construct(
            code="code-invalid",
            diagnostics="Coding system 'http://hl7.org/fhir/ValueSet/marriage-status' does not match the expected system, expected: 'http://hl7.org/fhir/ValueSet/marital-status'",
            location=["maritalStatus.system"],
            severity="error",
        ),
        OperationOutcomeIssue.construct(
            code="code-invalid",
            diagnostics="Coding resource code 'Married' not found in valueset 'marital-status'. Did you mean 'M'?",
            location=["maritalStatus.code"],
            severity="warning",
        ),
        OperationOutcomeIssue.construct(
            code="code-invalid",
            diagnostics="Code 'attackhelicopter' not found in valueset 'AdministrativeGender'",
            location=["contact.gender"],
            severity="error",
        ),
        OperationOutcomeIssue.construct(
            code="code-invalid",
            diagnostics="Coding system 'http://hl7.org/fhir/ValueSet/patient-relationship' does not match the expected system, expected: 'http://hl7.org/fhir/ValueSet/patient-contactrelationship'",
            location=["contact.relationship.system"],
            severity="error",
        ),
        OperationOutcomeIssue.construct(
            code="code-invalid",
            diagnostics="Coding resource display 'Partner' does not match the expected display, expected: 'Next-of-Kin'",
            location=["contact.relationship.display"],
            severity="error",
        ),
        OperationOutcomeIssue.construct(
            code="code-invalid",
            diagnostics="Coding system 'http://hl7.org/fhir/ValueSet/languages' does not match the expected system, expected: 'http://hl7.org/fhir/ValueSet/all-languages'",
            location=["communication.language.coding[0].system"],
            severity="error",
        ),
        OperationOutcomeIssue.construct(
            code="code-invalid",
            diagnostics="Coding resource code 'eng' does not match the expected code, expected: 'en'",
            location=["communication.language.coding[0].code"],
            severity="error",
        ),
        OperationOutcomeIssue.construct(
            code="code-invalid",
            diagnostics="Code 'seealsothisone' not found in valueset 'LinkType'",
            location=["link.type[0]"],
            severity="error",
        ),
        OperationOutcomeIssue.construct(
            code="code-invalid",
            diagnostics="Code 'thisonetoo' not found in valueset 'LinkType'",
            location=["link.type[1]"],
            severity="error",
        ),
    ]
