from fhirguard_core.filter import query_resource
from fhirguard_core.resources import CodeableConcept, Coding, Patient


def test_query_resource_empty_path():
    """"""
    patient = Patient.construct(id="123")

    result = query_resource(patient, "")

    assert result == [patient]


def test_query_resource_simple_path():
    """"""
    patient = Patient.construct(id="123", gender="male")

    id_ = query_resource(patient, "id")
    gender = query_resource(patient, "gender")

    assert id_ == ["123"]
    assert gender == ["male"]


def test_query_resource_nested_path():
    """"""
    patient = Patient.construct(
        id="123",
        maritalStatus=CodeableConcept.construct(
            coding=[Coding.construct(code="A", display="Annulled")], text="Annulled"
        ),
    )

    text = query_resource(patient, "maritalStatus.text")
    assert text == ["Annulled"]


def test_query_resource_multiple_results_simple_object():
    """ """
    patient = Patient.construct(
        id="123",
        maritalStatus={
            "coding": [
                {"code": "A", "display": "Annulled"},
                {"code": "D", "display": "Divorced"},
            ],
            "text": "Annulled or Divorced",
        },
    )

    text = query_resource(patient, "maritalStatus.coding.display")
    assert text == ["Annulled", "Divorced"]

    codings = query_resource(patient, "maritalStatus.coding")
    assert codings == [
        {"code": "A", "display": "Annulled"},
        {"code": "D", "display": "Divorced"},
    ]


def test_query_resource_multiple_results_pydantic_object():
    """ """
    patient = Patient.construct(
        id="123",
        maritalStatus=CodeableConcept.construct(
            coding=[
                Coding.construct(code="A", display="Annulled"),
                Coding.construct(code="D", display="Divorced"),
            ],
            text="Annulled or Divorced",
        ),
    )

    text = query_resource(patient, "maritalStatus.coding.display")
    assert text == ["Annulled", "Divorced"]

    codings = query_resource(patient, "maritalStatus.coding")
    assert codings == [
        {"code": "A", "display": "Annulled"},
        {"code": "D", "display": "Divorced"},
    ]
