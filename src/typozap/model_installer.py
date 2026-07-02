"""Téléchargement reprenable et vérifié du modèle officiel Ministral."""

import hashlib
import shutil
from pathlib import Path

import requests


MODEL_URL = (
    "https://huggingface.co/mistralai/Ministral-3-3B-Instruct-2512-GGUF/resolve/main/"
    "Ministral-3-3B-Instruct-2512-Q4_K_M.gguf"
)
MODEL_SHA256 = "9ed150d4367e68df0ac8e1540f6ddc65b42d0ee26378329d1ecbca60f93fc5f8"
MODEL_SIZE = 2_147_023_008


class ModelInstallError(RuntimeError):
    pass


def sha256_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_model(destination, progress=None):
    """Télécharge avec reprise, contrôle d'espace et vérification SHA-256."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    # Un modèle déjà présent est vérifié avant tout accès réseau.
    if destination.exists():
        if destination.stat().st_size == MODEL_SIZE and sha256_file(destination) == MODEL_SHA256:
            if progress:
                progress(MODEL_SIZE, MODEL_SIZE)
            return destination
        try:
            destination.unlink()
        except OSError as exc:
            raise ModelInstallError(f"Impossible de remplacer le modèle invalide : {exc}") from exc

    partial = destination.with_suffix(destination.suffix + ".part")
    existing = partial.stat().st_size if partial.exists() else 0

    if shutil.disk_usage(destination.parent).free < (MODEL_SIZE - existing) + 300_000_000:
        raise ModelInstallError("Espace disque insuffisant (environ 2,5 Go libres requis).")

    headers = {"Range": f"bytes={existing}-"} if existing else {}
    try:
        response = requests.get(MODEL_URL, headers=headers, stream=True, timeout=(10, 120))
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ModelInstallError(f"Téléchargement impossible : {exc}") from exc

    # Si le serveur ignore Range, il faut repartir de zéro.
    append = existing > 0 and response.status_code == 206
    if not append:
        existing = 0
    downloaded = existing
    try:
        with open(partial, "ab" if append else "wb") as stream:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                stream.write(chunk)
                downloaded += len(chunk)
                if downloaded > MODEL_SIZE:
                    raise ModelInstallError("Le serveur a envoyé un fichier de taille inattendue.")
                if progress:
                    progress(downloaded, MODEL_SIZE)
    except requests.RequestException as exc:
        raise ModelInstallError(f"Téléchargement interrompu : {exc}") from exc
    except OSError as exc:
        raise ModelInstallError(f"Écriture du modèle impossible : {exc}") from exc

    if downloaded != MODEL_SIZE or sha256_file(partial) != MODEL_SHA256:
        raise ModelInstallError("Le modèle téléchargé est incomplet ou corrompu.")
    partial.replace(destination)
    return destination
