import pytest

from controllers.auth import validate_credentials


def test_accepts_admin_admin(monkeypatch):
    monkeypatch.delenv("APP_USER", raising=False)
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    assert validate_credentials("admin", "admin")


@pytest.mark.parametrize("user,password", [("admin", "x"), ("x", "admin"), ("", ""), ("admin", ""), ("", "admin"), ("ADMIN", "admin")])
def test_rejects_wrong_or_empty(user, password, monkeypatch):
    monkeypatch.delenv("APP_USER", raising=False)
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    assert not validate_credentials(user, password)


def test_environment_overrides_defaults(monkeypatch):
    monkeypatch.setenv("APP_USER", "pablo")
    monkeypatch.setenv("APP_PASSWORD", "secreto")
    assert validate_credentials("pablo", "secreto")
    assert not validate_credentials("admin", "admin")


def test_non_ascii_credentials_do_not_crash(monkeypatch):
    monkeypatch.delenv("APP_USER", raising=False)
    assert not validate_credentials("añdmin", "contraseña")
