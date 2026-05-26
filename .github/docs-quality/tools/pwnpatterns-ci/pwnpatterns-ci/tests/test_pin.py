from pathlib import Path

from pwnpatterns_ci.pin import read_platform_ref, verify_pin


def test_read_platform_ref(tmp_path: Path) -> None:
    ref = tmp_path / "platform.ref"
    ref.write_text("a" * 40 + "\n", encoding="utf-8")
    assert read_platform_ref(ref) == "a" * 40


def test_verify_pin_mismatch(tmp_path: Path) -> None:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    sha_a = "a" * 40
    sha_b = "b" * 40
    (tmp_path / ".github" / "platform.ref").write_text(sha_a + "\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows" / "docs-quality.yml").write_text(
        f"uses: ocd-nl/pwnpatterns-ci/.github/workflows/docs-quality.yml@{sha_b}\n",
        encoding="utf-8",
    )
    errors = verify_pin(tmp_path)
    assert any("platform.ref" in e for e in errors)
