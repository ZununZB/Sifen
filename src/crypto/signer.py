"""Motor de firma digital — Actividad G (WIP / avance parcial).

Produce una firma **CMS/PKCS#7 detached** (el mismo mecanismo que usa Word)
sobre el contenido de un documento, usando el certificado y la llave privada
ya validados por :mod:`src.crypto.cert_loader`.

Alcance cubierto en este avance:
    - Firmar un stream de bytes y obtener el blob CMS/PKCS#7 (``sign_cms``).
    - Extraer y confirmar el certificado embebido en un blob CMS ya firmado
      (``extract_signer_certificate``).
    - Validación criptográfica real RSA-SHA256 de la firma contra el
      documento (``sign_raw_digest`` / ``verify_raw_digest``).

Nota honesta sobre el alcance de este avance (no cubrir esto sería
pretender más de lo que hay): la versión de ``cryptography`` instalada
(ver ``requirements.txt``) puede *generar* CMS/PKCS#7 pero no trae una
función para *verificar* una firma CMS completa sin una dependencia extra
para parsear ASN.1 (p. ej. ``asn1crypto``). Por eso la verificación
criptográfica real de este avance se hace con ``verify_raw_digest``
(RSA-SHA256 directo, que es el mecanismo que efectivamente protege el CMS
por debajo) mientras que ``extract_signer_certificate`` confirma que el
certificado correcto quedó embebido en el blob CMS entregable. Dejar un
parser de CMS completo (para verificar el blob CMS de punta a punta) queda
documentado como pendiente del resto de la actividad G / actividad H.

Pendiente (resto de la actividad G y actividad H):
    - Embeber la firma dentro del propio ``.odt`` siguiendo el esquema de
      firmas de ODF (``META-INF/documentsignatures.xml``), en vez de
      dejarla como blob separado.
    - Verificación de punta a punta del blob CMS (requiere un parser ASN.1
      de CMS, p. ej. añadiendo ``asn1crypto`` como dependencia).
    - Integrar estas funciones con ``src/ui/signing_dialog.py`` y
      ``src/core/extension_main.py`` (actividad H).
"""
from __future__ import annotations

from dataclasses import dataclass

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
from cryptography.hazmat.primitives.serialization import pkcs7


class SigningError(Exception):
    """Error al firmar o verificar un documento."""


@dataclass(frozen=True)
class SignatureResult:
    """Resultado de firmar un documento: la firma CMS/PKCS#7 en DER."""

    cms_signature: bytes
    hash_algorithm_name: str = "SHA256"


def sign_cms(
    data: bytes,
    certificate: x509.Certificate,
    private_key: PrivateKeyTypes,
) -> SignatureResult:
    """Firma ``data`` (p. ej. el contenido del documento) y regresa una
    firma CMS/PKCS#7 *detached* en DER — el formato entregable, compatible
    con el flujo que ya conocen los usuarios de Word (actividad A).
    """
    try:
        options = [pkcs7.PKCS7Options.DetachedSignature]
        builder = (
            pkcs7.PKCS7SignatureBuilder()
            .set_data(data)
            .add_signer(certificate, private_key, hashes.SHA256())
        )
        cms_der = builder.sign(serialization.Encoding.DER, options)
    except Exception as exc:  # pragma: no cover - defensivo
        raise SigningError(f"No se pudo generar la firma CMS/PKCS#7: {exc}") from exc

    return SignatureResult(cms_signature=cms_der)


def extract_signer_certificate(cms_signature: bytes) -> x509.Certificate:
    """Extrae el certificado embebido en un blob CMS/PKCS#7 ya firmado.

    Sirve para confirmar que el certificado correcto quedó empaquetado
    dentro del entregable, sin necesitar un parser de CMS completo.
    """
    try:
        certificates = pkcs7.load_der_pkcs7_certificates(cms_signature)
    except Exception as exc:
        raise SigningError(f"No se pudo leer el blob CMS/PKCS#7: {exc}") from exc

    if not certificates:
        raise SigningError("El blob CMS/PKCS#7 no contiene ningún certificado.")
    return certificates[0]


def sign_raw_digest(data: bytes, private_key: PrivateKeyTypes) -> bytes:
    """Firma RSA-SHA256 (PKCS#1 v1.5) directa sobre ``data``.

    Es el mecanismo criptográfico real que protege al CMS por debajo; se
    expone aparte para poder verificar de punta a punta en esta etapa del
    proyecto (ver nota de alcance en el docstring del módulo).
    """
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise SigningError(
            "sign_raw_digest sólo soporta llaves RSA en este avance "
            f"(se recibió {type(private_key).__name__})."
        )
    return private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())


def verify_raw_digest(
    data: bytes, signature: bytes, certificate: x509.Certificate
) -> bool:
    """Verifica una firma generada por :func:`sign_raw_digest` contra
    ``certificate``. Regresa ``True``/``False`` en vez de solo lanzar, para
    que la UI (actividad E/H) pueda mostrar un check/cruz directamente.
    """
    public_key = certificate.public_key()
    if not isinstance(public_key, rsa.RSAPublicKey):
        raise SigningError(
            "verify_raw_digest sólo soporta certificados RSA en este avance."
        )
    try:
        public_key.verify(signature, data, padding.PKCS1v15(), hashes.SHA256())
        return True
    except InvalidSignature:
        return False
