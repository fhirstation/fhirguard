import json
from pathlib import Path
from string import ascii_lowercase, digits

import requests
import typer
from rich import print
from rich.progress import track

from fhirguard_cli.constants import UCUM_API_URL

app = typer.Typer()

_PAGE_SIZE = 500


def get_ucum_results_for_character(
    character: str, page: int = 0, _results: list | None = None
):
    """
    Get a page of UCUM units of measure for a given character
    """
    if _results is None:
        _results = []

    fields = [
        "cs_code",
        "name",
        "category",
        "synonyms",
        "guidance",
        "source",
        "is_simple",
    ]

    response = requests.get(
        url=UCUM_API_URL,
        params={
            "terms": character,
            "maxList": _PAGE_SIZE,
            "offset": page * _PAGE_SIZE,
            "df": ",".join(fields),
        },
    )

    if response.status_code != requests.status_codes.codes.ok:
        print(f"ERROR: {response.status_code}")
        return []

    total_count, _codes, _, results = response.json()
    if len(results) >= _PAGE_SIZE:
        return get_ucum_results_for_character(
            character,
            page + 1,
            [zip(fields, data, strict=False) for data in [*_results, *results]],
        )

    assert len(results) == total_count
    return [dict(zip(fields, data, strict=False)) for data in [*_results, *results]]


@app.command()
def fetch(
    output: str = typer.Option(
        ...,
        help="Path to output file",
        exists=False,
        file_okay=True,
        dir_okay=False,
        writable=True,
        readable=False,
        resolve_path=True,
    ),
):
    """
    Fetch units of measure from the API for UCUM
    API Documentation: https://clinicaltables.nlm.nih.gov/apidoc/ucum/v3/doc.html
    """
    results = []
    characters = ascii_lowercase + digits

    for letter in track(characters, description="Fetching UCUM results..."):
        results += get_ucum_results_for_character(letter)

    print(f"Deduplicating query results... (total={len(results)})")
    deduplicated_results = []
    for result in results:
        if result not in deduplicated_results:
            deduplicated_results.append(result)

    print(f"Deduplicated to {len(deduplicated_results)} results")
    print("Writing results to file...")

    output_path = Path(output)
    output_path.write_text(
        json.dumps(
            sorted(deduplicated_results, key=lambda result: result["cs_code"]), indent=2
        )
    )
