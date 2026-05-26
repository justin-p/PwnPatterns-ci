from tests.manifest_fixtures import load_platform_manifest, platform_manifest_env_path


def test_load_manifest() -> None:
    m = load_platform_manifest()
    assert platform_manifest_env_path().is_file()
    assert m.vale_version
    assert m.typos_version
    assert m.lychee_version
    assert "harper-dictionary" in m.harper_user_dict
