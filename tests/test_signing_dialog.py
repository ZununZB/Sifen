"""Pruebas de la parte pura (sin UNO) del diálogo de firma - Actividad E.

La parte que sí depende de UNO (``pick_certificate_file``, ``ask_password``,
``show_signing_dialog``) no se puede probar con pytest porque necesita una
sesión interactiva de LibreOffice (ver nota en ``docs/architecture.md`` y
``scripts/test_conexion_uno.py`` para cómo probarla manualmente dentro de
la suite). Lo que sí es 100% Python puro -y por lo tanto 100% probable aquí-
es la validación de los datos capturados.
"""
from __future__ import annotations

from src.ui.signing_dialog import SigningRequest, validate_signing_request


def test_valid_request_has_no_errors(valid_credential_files):
    errors = validate_signing_request(
        str(valid_credential_files["cer_path"]),
        str(valid_credential_files["key_path"]),
        valid_credential_files["password"],
    )
    assert errors == []


def test_missing_certificate_path_reported():
    errors = validate_signing_request("", "/tmp/algo.key", "clave")
    assert any("certificado" in e.lower() for e in errors)


def test_wrong_certificate_extension_reported(tmp_path):
    fake_cert = tmp_path / "certificado.txt"
    fake_cert.write_text("no es un certificado")
    errors = validate_signing_request(str(fake_cert), "/tmp/algo.key", "clave")
    assert any(".cer" in e for e in errors)


def test_missing_certificate_file_reported(tmp_path):
    missing = tmp_path / "no_existe.cer"
    errors = validate_signing_request(str(missing), "/tmp/algo.key", "clave")
    assert any("no se encontró" in e.lower() for e in errors)


def test_missing_private_key_path_reported(valid_credential_files):
    errors = validate_signing_request(
        str(valid_credential_files["cer_path"]), "", "clave"
    )
    assert any("llave privada" in e.lower() for e in errors)


def test_missing_password_reported(valid_credential_files):
    errors = validate_signing_request(
        str(valid_credential_files["cer_path"]),
        str(valid_credential_files["key_path"]),
        "",
    )
    assert any("contraseña" in e.lower() for e in errors)


def test_signing_request_is_immutable(valid_credential_files):
    request = SigningRequest(
        certificate_path=str(valid_credential_files["cer_path"]),
        private_key_path=str(valid_credential_files["key_path"]),
        password=valid_credential_files["password"],
    )
    try:
        request.password = "otra"  # type: ignore[misc]
        assert False, "SigningRequest debería ser inmutable (frozen dataclass)"
    except AttributeError:
        pass
