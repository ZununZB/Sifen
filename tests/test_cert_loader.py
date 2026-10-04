from __future__ import annotations

import pytest

from src.crypto import cert_loader


def test_load_certificate_der(valid_credential_files):
    cert = cert_loader.load_certificate(valid_credential_files["cer_path"])
    assert cert.serial_number == valid_credential_files["certificate"].serial_number


def test_load_private_key_with_correct_password(valid_credential_files):
    key = cert_loader.load_private_key(
        valid_credential_files["key_path"], valid_credential_files["password"]
    )
    assert key.key_size == 2048


def test_load_private_key_with_wrong_password_raises(valid_credential_files):
    with pytest.raises(cert_loader.InvalidPasswordError):
        cert_loader.load_private_key(
            valid_credential_files["key_path"], "contraseña-incorrecta"
        )


def test_validate_certificate_is_current_ok(valid_credential_files):
    cert_loader.validate_certificate_is_current(valid_credential_files["certificate"])


def test_validate_expired_certificate_raises(expired_credential_files):
    with pytest.raises(cert_loader.CertificateExpiredError):
        cert_loader.validate_certificate_is_current(
            expired_credential_files["certificate"]
        )


def test_key_matches_certificate_ok(valid_credential_files):
    cert_loader.validate_key_matches_certificate(
        valid_credential_files["certificate"], valid_credential_files["private_key"]
    )


def test_key_mismatch_raises(valid_credential_files, mismatched_key_file):
    other_key = cert_loader.load_private_key(
        mismatched_key_file["key_path"], mismatched_key_file["password"]
    )
    with pytest.raises(cert_loader.KeyCertificateMismatchError):
        cert_loader.validate_key_matches_certificate(
            valid_credential_files["certificate"], other_key
        )


def test_load_and_validate_credentials_end_to_end(valid_credential_files):
    pair = cert_loader.load_and_validate_credentials(
        valid_credential_files["cer_path"],
        valid_credential_files["key_path"],
        valid_credential_files["password"],
    )
    assert pair.subject_common_name == "PRUEBA RICARDO ZUNUN"


def test_load_and_validate_credentials_rejects_expired(
    expired_credential_files, valid_credential_files
):
    # Certificado vencido + llave válida de OTRO fixture: debe fallar por
    # vigencia antes de siquiera comparar la llave.
    with pytest.raises(cert_loader.CertificateExpiredError):
        cert_loader.load_and_validate_credentials(
            expired_credential_files["cer_path"],
            valid_credential_files["key_path"],
            valid_credential_files["password"],
        )
