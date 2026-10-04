"""Fixtures compartidos: genera certificados/llaves de PRUEBA autofirmados.

Importante: nada de esto son credenciales reales de e.firma. Se generan en
memoria en cada corrida de pytest (no se versionan en el repo) únicamente
para poder probar `src/crypto` sin depender de un certificado real del SAT.
"""
from __future__ import annotations

import datetime as dt

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

TEST_PASSWORD = "clave-de-prueba-123"


def _build_self_signed(
    *, common_name: str, days_valid: int = 365, not_before_offset_days: int = 0
):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, common_name)]
    )
    now = dt.datetime.now(dt.timezone.utc)
    not_before = now + dt.timedelta(days=not_before_offset_days)
    not_after = not_before + dt.timedelta(days=days_valid)

    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .sign(private_key, hashes.SHA256())
    )
    return certificate, private_key


@pytest.fixture
def valid_credential_files(tmp_path):
    """Certificado y llave válidos y correspondientes entre sí."""
    certificate, private_key = _build_self_signed(common_name="PRUEBA RICARDO ZUNUN")

    cer_path = tmp_path / "prueba.cer"
    key_path = tmp_path / "prueba.key"

    cer_path.write_bytes(certificate.public_bytes(serialization.Encoding.DER))
    key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(
                TEST_PASSWORD.encode("utf-8")
            ),
        )
    )
    return {
        "cer_path": cer_path,
        "key_path": key_path,
        "password": TEST_PASSWORD,
        "certificate": certificate,
        "private_key": private_key,
    }


@pytest.fixture
def expired_credential_files(tmp_path):
    """Certificado vencido (válido hace un año, por 30 días)."""
    certificate, private_key = _build_self_signed(
        common_name="PRUEBA VENCIDA",
        days_valid=30,
        not_before_offset_days=-400,
    )
    cer_path = tmp_path / "vencido.cer"
    cer_path.write_bytes(certificate.public_bytes(serialization.Encoding.DER))
    return {"cer_path": cer_path, "certificate": certificate}


@pytest.fixture
def mismatched_key_file(tmp_path):
    """Llave privada de OTRO par, para probar la detección de 'no coincide'."""
    _, other_private_key = _build_self_signed(common_name="OTRA LLAVE")
    key_path = tmp_path / "otra.key"
    key_path.write_bytes(
        other_private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(
                TEST_PASSWORD.encode("utf-8")
            ),
        )
    )
    return {"key_path": key_path, "password": TEST_PASSWORD}
