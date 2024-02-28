import shutil

import typer

from fhirguard_cli.constants import CONFIG_DIRECTORY
from fhirguard_cli.util import download_simplifier_package

app = typer.Typer()


@app.command(name="pull")
def pull_package(
    package_name: str = typer.Argument(..., help="Name of the package to pull"),
):
    """Pull a package from SIMPLIFIER.NET"""
    download_simplifier_package(package_name)


@app.command(name="list")
def list_packages():
    """List all locally downloaded packages"""
    typer.echo("Local Packages:")
    package_dir = CONFIG_DIRECTORY / "packages"
    for file in package_dir.iterdir():
        typer.echo(file.name)


@app.command(name="delete")
def delete_package(
    package_name: str = typer.Argument(..., help="Name of the package to delete"),
):
    """Delete a package from the local cache"""
    package_dir = CONFIG_DIRECTORY / "packages" / package_name
    if package_dir.exists():
        typer.echo(f"Deleting package '{package_name}'")
        shutil.rmtree(package_dir)
    else:
        typer.echo(f"Package '{package_name}' does not exist")


@app.command(name="refresh")
def refresh_packages():
    """Refresh all locally downloaded packages"""
    typer.echo("Refreshing all packages")
    package_dir = CONFIG_DIRECTORY / "packages"
    for file in package_dir.iterdir():
        download_simplifier_package(file.name)
