from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_PS1 = (REPO_ROOT / "scripts" / "install.ps1").read_text(encoding="utf-8")
INSTALL_SH = (REPO_ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
DESKTOP_TEST_RUNNER = (
    REPO_ROOT / "apps" / "desktop" / "scripts" / "test-desktop.mjs"
).read_text(encoding="utf-8")


def test_windows_installer_accepts_a_validated_github_repository_slug() -> None:
    assert '[string]$Repository = "NousResearch/hermes-agent"' in INSTALL_PS1
    assert '$Repository -notmatch' in INSTALL_PS1
    assert 'https://github.com/$Repository.git' in INSTALL_PS1
    assert 'https://github.com/$Repository/archive/$Commit.zip' in INSTALL_PS1


def test_posix_installer_accepts_a_validated_github_repository_slug() -> None:
    assert 'REPOSITORY="NousResearch/hermes-agent"' in INSTALL_SH
    assert '--repository)' in INSTALL_SH
    assert 'https://github.com/${REPOSITORY}.git' in INSTALL_SH


def test_windows_installer_does_not_persist_isolated_desktop_environment() -> None:
    assert '$isIsolatedDesktopFreshInstall = $env:HERMES_DESKTOP_TEST_MODE -eq "fresh-install"' in INSTALL_PS1
    assert 'Skipping user PATH/HERMES_HOME persistence for isolated desktop fresh-install' in INSTALL_PS1


def test_windows_prerequisite_installers_do_not_persist_isolated_desktop_environment() -> None:
    assert '$changed -and -not (Test-IsolatedDesktopFreshInstall)' in INSTALL_PS1
    assert 'if (-not (Test-IsolatedDesktopFreshInstall)) {\n                [Environment]::SetEnvironmentVariable("HERMES_GIT_BASH_PATH"' in INSTALL_PS1
    assert '($userPathItems -notcontains $nodeDir) -and -not (Test-IsolatedDesktopFreshInstall)' in INSTALL_PS1


def test_desktop_fresh_install_confines_playwright_browsers_to_sandbox() -> None:
    assert "env.PLAYWRIGHT_BROWSERS_PATH = path.join(hermesHome, 'playwright-browsers')" in DESKTOP_TEST_RUNNER
