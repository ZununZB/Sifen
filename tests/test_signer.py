from __future__ import annotations

from src.crypto import signer


def test_sign_cms_produces_der_bytes(valid_credential_files):
    document_bytes = b"contenido de prueba del documento Writer"
    result = signer.sign_cms(
        document_bytes,
        valid_credential_files["certificate"],
        valid_credential_files["private_key"],
    )
    assert isinstance(result.cms_signature, bytes)
    assert len(result.cms_signature) > 0
    assert result.hash_algorithm_name == "SHA256"


def test_extract_signer_certificate_matches_original(valid_credential_files):
    document_bytes = b"contenido de prueba del documento Writer"
    result = signer.sign_cms(
        document_bytes,
        valid_credential_files["certificate"],
        valid_credential_files["private_key"],
    )
    embedded_cert = signer.extract_signer_certificate(result.cms_signature)
    assert embedded_cert.serial_number == valid_credential_files["certificate"].serial_number


def test_sign_and_verify_raw_digest_roundtrip(valid_credential_files):
    document_bytes = b"contenido de prueba del documento Writer"
    signature = signer.sign_raw_digest(
        document_bytes, valid_credential_files["private_key"]
    )
    assert signer.verify_raw_digest(
        document_bytes, signature, valid_credential_files["certificate"]
    )


def test_verify_raw_digest_rejects_tampered_document(valid_credential_files):
    original = b"contenido de prueba del documento Writer"
    tampered = b"contenido MODIFICADO del documento Writer"

    signature = signer.sign_raw_digest(original, valid_credential_files["private_key"])

    assert not signer.verify_raw_digest(
        tampered, signature, valid_credential_files["certificate"]
    )


def test_verify_raw_digest_rejects_wrong_certificate(
    valid_credential_files, mismatched_key_file
):
    from src.crypto import cert_loader

    document_bytes = b"contenido de prueba del documento Writer"
    signature = signer.sign_raw_digest(
        document_bytes, valid_credential_files["private_key"]
    )

    other_key = cert_loader.load_private_key(
        mismatched_key_file["key_path"], mismatched_key_file["password"]
    )
    wrong_signature = signer.sign_raw_digest(document_bytes, other_key)

    # La firma hecha con OTRA llave no debe validar contra el certificado
    # original.
    assert not signer.verify_raw_digest(
        document_bytes, wrong_signature, valid_credential_files["certificate"]
    )
