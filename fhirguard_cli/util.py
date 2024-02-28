import shutil
import subprocess
import tarfile
from io import BytesIO
from pathlib import Path

import requests
import typer
from rich import print
from rich.progress import track

from fhirguard_cli.constants import CONFIG_DIRECTORY, SIMPLIFIER_REGISTRY


def get_tarball_url(package: str) -> str:
    """Get the tarball URL for a package from the SIMPLIFIER.NET package registry"""
    command = [
        "npm",
        "--registry",
        SIMPLIFIER_REGISTRY,
        "view",
        package,
        "dist.tarball",
    ]
    print(f"Running command: '{' '.join(command)}'")

    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0:
        print(f"Error downloading package '{package}'")
        print("npm output:")
        print(result.stdout)
        print(result.stderr)
        raise typer.Exit(code=1)

    return result.stdout.decode("utf-8").strip()


def download_file(url: str) -> bytes:
    """Download a file from a URL with a progress bar"""
    response = requests.get(url, stream=True)
    data = b""
    for chunk in track(
        response.iter_content(chunk_size=16384),
        description=f"Downloading file from '{url}'",
        total=int(response.headers.get("content-length", 0)) / 16384,
    ):
        data += chunk

    if response.status_code != requests.status_codes.codes.ok:
        print(f"Error downloading file from '{url}'")
        print(f"HTTP status code: {response.status_code}")
        raise typer.Exit(code=1)

    return data


def extract_tarball(data: bytes, extract_path: Path) -> None:
    """Extract a tarball to a directory"""
    print(f"Extracting tarball to '{extract_path}'")
    if extract_path.exists():
        print(f"Directory '{extract_path}' already exists, replacing contents...")
        shutil.rmtree(extract_path)

    extract_path.mkdir(parents=True, exist_ok=True)

    package_file = tarfile.open(fileobj=BytesIO(data), mode="r:gz")
    package_file.extractall(path=extract_path)
    package_file.close()


def download_simplifier_package(package: str) -> Path:
    """Download a SIMPLIFIER.NET package from the SIMPLIFIER.NET package registry"""
    print(f"Downloading SIMPLIFIER.NET package '{package}'")

    tarball_url = get_tarball_url(package)
    data = download_file(tarball_url)

    extract_path = CONFIG_DIRECTORY / "packages" / package
    extract_tarball(data, extract_path)

    return extract_path


def get_package_path(package: str) -> Path:
    """Get the path to a package"""
    package_path = CONFIG_DIRECTORY / "packages" / package
    if not package_path.exists():
        print(
            f"Package '{package}' does not exist. Use fhirguard package pull {package} to download it."
        )
        raise typer.Exit(code=1)

    return package_path
