import json
from pathlib import Path
from typing import Any, Dict, Iterable, Literal


class Metadata:
    def __init__(self, paths: Iterable[Path | str]):
        self.paths = [Path(path) for path in paths]
        self.manifests: Dict[str, Dict[str, Any]] = self._load_manifests()
        self._cache = {}

    def _load_manifests(self):
        """Load the manifest file from the metadata directory."""
        manifests = {}

        for path in self.paths:
            manifest_path = path / "manifest.json"
            if not manifest_path.exists():
                raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

            manifests[str(path)] = json.loads(manifest_path.read_text())

        return manifests

    def get_codesystem(self, id_or_name: str) -> dict | None:
        if not (file_path := self._get_resource_path(id_or_name, "codesystems")):
            return None

        if file_path in self._cache:
            return self._cache[file_path]

        codesystem = json.loads(file_path.read_text())
        self._cache[file_path] = codesystem

        return codesystem

    def get_valueset(self, id_or_name: str) -> dict | None:
        if not (file_path := self._get_resource_path(id_or_name, "valuesets")):
            return None

        if file_path in self._cache:
            return self._cache[str(file_path)]

        valueset = json.loads(file_path.read_text())
        self._cache[str(file_path)] = valueset

        return valueset

    def _get_resource_path(
        self, id_or_name: str, resource_type: Literal["codesystems", "valuesets"]
    ) -> Path | None:
        """Get the file hash for a CodeSystem by ID or name"""

        for path, manifest in self.manifests.items():
            if id_or_name in manifest[resource_type]["id"]:
                file_hash = manifest[resource_type]["id"][id_or_name]
                return Path(path) / resource_type / f"{file_hash}.json"

            if id_or_name in manifest[resource_type]["name"]:
                file_hash = manifest[resource_type]["name"][id_or_name]
                return Path(path) / resource_type / f"{file_hash}.json"

        if "http" in id_or_name:
            resource_id = id_or_name.split("/")[-1]
            return self._get_resource_path(resource_id, resource_type)

        return None
