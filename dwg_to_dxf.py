"""DWG-to-DXF converter using ODA File Converter CLI."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


class ODANotFoundError(RuntimeError):
    """Raised when the ODA File Converter binary cannot be located."""


class ConversionError(RuntimeError):
    """Raised when ODA conversion fails."""


def _find_oda_converter() -> str:
    """Resolve ODA binary via env var, PATH, or well-known install locations."""
    env_path = os.environ.get("ODA_CONVERTER")
    if env_path and Path(env_path).is_file():
        return env_path

    which = shutil.which("ODAFileConverter") or shutil.which("odafileconverter")
    if which:
        return which

    well_known = [
        "/usr/bin/ODAFileConverter",
        "/usr/local/bin/ODAFileConverter",
        "/opt/ODAFileConverter/ODAFileConverter",
        r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
        r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe",
    ]
    for path in well_known:
        if Path(path).is_file():
            return path

    raise ODANotFoundError(
        "ODA File Converter not found. Set the ODA_CONVERTER environment variable "
        "to the binary path, or install it and ensure it is on PATH."
    )


def is_dwg(path: str) -> bool:
    """Detect DWG by magic bytes and file extension."""
    p = Path(path)
    if p.suffix.lower() != ".dwg":
        return False
    try:
        with open(p, "rb") as f:
            magic = f.read(6)
        return magic[:2] == b"AC"
    except OSError:
        return False


def convert_dwg_to_dxf(dwg_path: str, output_dir: str, oda_version: str = "ACAD2018") -> str:
    """Convert a DWG file to DXF using ODA File Converter.

    Stages the input file in a temp directory (ODA requires a folder, not a
    single file path), runs ODA, then moves the resulting DXF to output_dir.

    Returns the path to the produced DXF file.
    """
    oda_bin = _find_oda_converter()
    dwg_path = Path(dwg_path).resolve()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as staging:
        staged = Path(staging) / dwg_path.name
        shutil.copy2(dwg_path, staged)

        result_dir = Path(staging) / "out"
        result_dir.mkdir()

        cmd = [
            oda_bin,
            str(staging),
            str(result_dir),
            oda_version,
            "DXF",
            "0",
            "1",
            "*.DWG",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise ConversionError(
                f"ODA conversion failed (exit {proc.returncode}): {proc.stderr.strip()}"
            )

        dxf_name = dwg_path.stem + ".dxf"
        produced = result_dir / dxf_name
        if not produced.exists():
            candidates = list(result_dir.glob("*.dxf"))
            if not candidates:
                raise ConversionError(
                    f"ODA ran successfully but produced no DXF files in {result_dir}"
                )
            produced = candidates[0]

        dest = output_dir / produced.name
        shutil.move(str(produced), dest)

    return str(dest)


def ensure_dxf(path: str, output_dir: str | None = None, oda_version: str = "ACAD2018") -> str:
    """Return a DXF path: pass DXF through unchanged, convert DWG on the fly.

    If output_dir is None and conversion is needed, the DXF is placed next to
    the source DWG.
    """
    if not is_dwg(path):
        return path

    if output_dir is None:
        output_dir = str(Path(path).parent)

    return convert_dwg_to_dxf(path, output_dir, oda_version)
