from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_PS1 = (REPO_ROOT / "scripts" / "install.ps1").read_text(encoding="utf-8")
INSTALL_SH = (REPO_ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")


def test_windows_installer_accepts_a_validated_github_repository_slug() -> None:
    assert '[string]$Repository = "NousResearch/hermes-agent"' in INSTALL_PS1
    assert '$Repository -notmatch' in INSTALL_PS1
    assert 'https://github.com/$Repository.git' in INSTALL_PS1
    assert 'https://github.com/$Repository/archive/$Commit.zip' in INSTALL_PS1


def test_posix_installer_accepts_a_validated_github_repository_slug() -> None:
    assert 'REPOSITORY="NousResearch/hermes-agent"' in INSTALL_SH
    assert '--repository)' in INSTALL_SH
    assert 'https://github.com/${REPOSITORY}.git' in INSTALL_SH
