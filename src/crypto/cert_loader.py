"""Carga y validación de certificados e.firma (Actividad F).

Maneja el par de archivos que entrega el SAT:

- ``.cer``: certificado público X.509 (DER o PEM).
- ``.key``: llave privada cifrada con contraseña (PKCS#8, DER o PEM).

y valida que:

1. El certificado no esté vencido.
2. La contraseña realmente descifre la llave privada.
3. La llave privada corresponda al certificado (mismo par de llaves).
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes


class CertificateError(Exception):
    """Error al cargar o validar un certificado/llave privada."""


class CertificateExpiredError(CertificateError):
    """El certificado está fuera de su periodo de vigencia."""


class InvalidPasswordError(CertificateError):
    """La contraseña no corresponde a la llave privada."""


class KeyCertificateMismatchError(CertificateError):
    """La llave privada no corresponde al certificado."""


@dataclass(frozen=True)
class CredentialPair:
    """Certificado + llave privada ya cargados y validados entre sí."""

    certificate: x509.Certificate
    private_key: PrivateKeyTypes

    @property
    def subject_common_name(self) -> str | None:
        attrs = self.certificate.subject.get_attributes_for_oid(
            x509.oid.NameOID.COMMON_NAME
        )
        return attrs[0].value if attrs else None

    @property
    def not_valid_after(self) -> _dt.datetime:
        # cryptography >= 42 expone la versión UTC-aware recomendada.
        getter = getattr(
            self.certificate, "not_valid_after_utc", None
        )
        return getter if getter is not None else self.certificate.not_valid_after


def load_certificate(path: str | Path) -> x509.Certificate:
    """Carga un certificado ``.cer`` en formato DER o PEM."""
    data = Path(path).read_bytes()
    try:
        return x509.load_der_x509_certificate(data)
    except ValueError:
        pass
    try:
        return x509.load_pem_x509_certificate(data)
    except ValueError as exc:
        raise CertificateError(
            f"No se pudo leer '{path}' como certificado X.509 (ni DER ni PEM)."
        ) from exc


def load_private_key(path: str | Path, password: str) -> PrivateKeyTypes:
    """Carga una llave privada ``.key`` cifrada con ``password``."""
    data = Path(path).read_bytes()
    password_bytes = password.encode("utf-8") if password else None

    loaders = (
        serialization.load_der_private_key,
        serialization.load_pem_private_key,
    )
    last_error: Exception | None = None
    for loader in loaders:
        try:
            return loader(data, password=password_bytes)
        except (ValueError, TypeError) as exc:
            message = str(exc).lower()
            # Un error de contraseña significa que el loader SÍ reconoció el
            # formato (DER o PEM) y llegó a intentar descifrar: es la causa
            # real, no hace falta seguir probando el otro formato.
            if "password" in message or "decrypt" in message:
                raise InvalidPasswordError(
                    f"La contraseña proporcionada no pudo descifrar '{path}'."
                ) from exc
            last_error = exc
            continue

    message = str(last_error) if last_error else "formato no reconocido"
    raise CertificateError(
        f"No se pudo leer '{path}' como llave privada (ni DER ni PEM): {message}"
    ) from last_error


def validate_certificate_is_current(
    certificate: x509.Certificate, *, reference_time: _dt.datetime | None = None
) -> None:
    """Lanza :class:`CertificateExpiredError` si el certificado no está vigente."""
    now = reference_time or _dt.datetime.now(_dt.timezone.utc)

    # getattr(obj, name, default) evaluaría `default` de forma anticipada, lo
    # cual dispararía el warning de deprecación de las propiedades "naive"
    # aunque exista la versión *_utc; por eso se usa hasattr en su lugar.
    not_before = (
        certificate.not_valid_before_utc
        if hasattr(certificate, "not_valid_before_utc")
        else certificate.not_valid_before
    )
    not_after = (
        certificate.not_valid_after_utc
        if hasattr(certificate, "not_valid_after_utc")
        else certificate.not_valid_after
    )

    if now < not_before:
        raise CertificateExpiredError(
            f"El certificado todavía no es válido (vigencia desde {not_before})."
        )
    if now > not_after:
        raise CertificateExpiredError(
            f"El certificado venció el {not_after}."
        )


def _public_numbers(key) -> tuple:
    """Extrae los parámetros públicos de una llave (RSA o EC) para comparar."""
    public_key = key.public_key() if hasattr(key, "public_key") else key
    if isinstance(public_key, rsa.RSAPublicKey) or hasattr(public_key, "public_numbers"):
        numbers = public_key.public_numbers()
        return (type(numbers).__name__, repr(numbers))
    # Fallback genérico: comparar la representación serializada en DER.
    der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return ("der", der)


def validate_key_matches_certificate(
    certificate: x509.Certificate, private_key: PrivateKeyTypes
) -> None:
    """Lanza :class:`KeyCertificateMismatchError` si la llave y el certificado
    no son del mismo par."""
    cert_public = _public_numbers(certificate.public_key())
    key_public = _public_numbers(private_key)
    if cert_public != key_public:
        raise KeyCertificateMismatchError(
            "La llave privada no corresponde a la llave pública del certificado."
        )


def load_and_validate_credentials(
    certificate_path: str | Path,
    private_key_path: str | Path,
    password: str,
    *,
    reference_time: _dt.datetime | None = None,
) -> CredentialPair:
    """Carga certificado + llave y corre todas las validaciones de la
    actividad F en un solo paso. Pensada para ser llamada directamente desde
    la UI (actividad E/H)."""
    certificate = load_certificate(certificate_path)
    validate_certificate_is_current(certificate, reference_time=reference_time)

    private_key = load_private_key(private_key_path, password)
    validate_key_matches_certificate(certificate, private_key)

    return CredentialPair(certificate=certificate, private_key=private_key)
