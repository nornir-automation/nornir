from __future__ import annotations

import shutil
import subprocess  # noqa: S404
import sys
import tempfile
from pathlib import Path

IMPORT_CHECK = """
import pathlib
import sys

import nornir
from nornir import InitNornir

module_path = pathlib.Path(nornir.__file__).resolve()
environment = pathlib.Path(sys.prefix).resolve()
if environment not in module_path.parents:
    raise SystemExit(f"Imported nornir from outside {environment}: {module_path}")
if InitNornir.__name__ != "InitNornir":
    raise SystemExit("InitNornir is not importable from the built wheel")
"""


def find_built_wheel(dist_directory: Path) -> Path:
    wheels = sorted(dist_directory.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"Expected exactly one wheel in {dist_directory}, found {len(wheels)}")
    return wheels[0]


def find_environment_python(environment: Path) -> Path:
    candidates = (
        environment / "bin" / "python",
        environment / "Scripts" / "python.exe",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError(f"Unable to find Python in virtual environment {environment}")


def run(command: tuple[str, ...], *, cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)  # noqa: S603


def main() -> None:
    repository = Path(__file__).resolve().parents[1]
    wheel = find_built_wheel(repository / "dist")
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required to verify the built wheel")

    with tempfile.TemporaryDirectory(prefix="nornir-wheel-test-") as temporary:
        temporary_directory = Path(temporary)
        environment = temporary_directory / "venv"
        run((uv, "venv", str(environment)), cwd=repository)
        python = find_environment_python(environment)
        run(
            (uv, "pip", "install", "--python", str(python), str(wheel)),
            cwd=repository,
        )

        outside_checkout = temporary_directory / "outside-checkout"
        outside_checkout.mkdir()
        run((str(python), "-I", "-c", IMPORT_CHECK), cwd=outside_checkout)

    sys.stdout.write(f"Verified isolated import from {wheel.name}\n")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        sys.stderr.write(f"Wheel importability check failed: {exc}\n")
        raise SystemExit(1) from exc
