import typer

from fhirguard_cli.commands.metadata import app as metadata_app
from fhirguard_cli.commands.package import app as package_app
from fhirguard_cli.commands.ucum import app as ucum_app

app = typer.Typer()
app.add_typer(ucum_app, name="ucum")
app.add_typer(metadata_app, name="metadata")
app.add_typer(package_app, name="package")

if __name__ == "__main__":
    app()
