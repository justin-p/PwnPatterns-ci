from pathlib import Path

from docs_dev.manifest import load_manifest


def test_load_manifest():
    manifest_path = (
        Path(__file__).resolve().parents[3] / "config" / "manifest.env"
    )
    m = load_manifest(manifest_path)
    assert m.vale_version == "3.9.1"
    assert m.typos_version == "1.29.0"
    assert "harper-dictionary" in m.harper_user_dict
