"""Diálogo de firma — Actividad E (interfaz gráfica y menú dedicado).

Replica el flujo ya conocido de la función "Firmar" de Word (requisito de
la actividad A): el usuario elige su certificado (``.cer``), su llave
privada (``.key``) y captura la contraseña de la e.firma, en tres pasos:

    1. :func:`pick_certificate_file` — selector de archivos estándar de
       LibreOffice, filtrado a ``.cer``.
    2. :func:`pick_private_key_file` — mismo selector, filtrado a ``.key``.
    3. :func:`ask_password` — diálogo propio con un campo enmascarado
       (``EchoChar``), porque el FilePicker estándar no captura texto.

:func:`show_signing_dialog` orquesta los tres pasos y valida la selección
con :func:`validate_signing_request` antes de regresar un
:class:`SigningRequest` listo para pasar a ``src.crypto`` (eso ya es la
actividad H: integrar esta UI con la lógica criptográfica).

Diseño: la validación de entradas (:func:`validate_signing_request`) es
Python puro, sin UNO, a propósito, para poder probarla con pytest igual que
``src/crypto`` (ver ``docs/architecture.md``). Las funciones que sí
necesitan UNO (``pick_*``, ``ask_password``, ``show_signing_dialog``)
reciben el contexto (``ctx``) como parámetro en vez de importarlo global,
para no romper la importación del módulo fuera de LibreOffice.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SigningRequest:
    """Datos que la UI recolecta del usuario antes de firmar."""

    certificate_path: str
    private_key_path: str
    password: str


def validate_signing_request(
    certificate_path: str, private_key_path: str, password: str
) -> list[str]:
    """Valida lo que el usuario capturó en el diálogo *antes* de intentar
    cargar los archivos con ``src.crypto.cert_loader`` (esa carga ya hace
    su propia validación criptográfica; esto es solo la validación de forma
    que le corresponde a la UI, p. ej. para no mandar una ruta vacía).

    Regresa una lista de mensajes de error (vacía si todo está bien), para
    que el diálogo pueda mostrarlos sin tener que lanzar excepciones por
    cada campo.
    """
    errors: list[str] = []

    if not certificate_path:
        errors.append("Selecciona tu certificado (.cer).")
    elif not Path(certificate_path).suffix.lower() == ".cer":
        errors.append("El certificado debe tener extensión .cer.")
    elif not Path(certificate_path).is_file():
        errors.append(f"No se encontró el archivo de certificado: {certificate_path}")

    if not private_key_path:
        errors.append("Selecciona tu llave privada (.key).")
    elif not Path(private_key_path).suffix.lower() == ".key":
        errors.append("La llave privada debe tener extensión .key.")
    elif not Path(private_key_path).is_file():
        errors.append(f"No se encontró el archivo de llave privada: {private_key_path}")

    if not password:
        errors.append("Captura la contraseña de tu e.firma.")

    return errors


# --------------------------------------------------------------------------
# A partir de aquí, todo requiere la API UNO (solo corre dentro de
# LibreOffice). Se importa dentro de cada función -no a nivel de módulo- para
# que el resto del archivo siga siendo importable/probable fuera de la
# suite (ver docs/architecture.md).
# --------------------------------------------------------------------------


def pick_certificate_file(ctx) -> str | None:
    """Abre el selector de archivos estándar filtrado a certificados
    ``.cer``. Regresa la ruta elegida, o ``None`` si el usuario cancela.
    """
    return _pick_file(ctx, title="Selecciona tu certificado (.cer)", filter_name="*.cer")


def pick_private_key_file(ctx) -> str | None:
    """Abre el selector de archivos estándar filtrado a llaves ``.key``.
    Regresa la ruta elegida, o ``None`` si el usuario cancela.
    """
    return _pick_file(ctx, title="Selecciona tu llave privada (.key)", filter_name="*.key")


def _pick_file(ctx, *, title: str, filter_name: str) -> str | None:
    import uno
    from com.sun.star.ui.dialogs.ExecutableDialogResults import OK as DIALOG_OK

    smgr = ctx.ServiceManager
    file_picker = smgr.createInstanceWithContext(
        "com.sun.star.ui.dialogs.FilePicker", ctx
    )
    file_picker.setTitle(title)
    file_picker.appendFilter(filter_name, filter_name)
    file_picker.setCurrentFilter(filter_name)

    if file_picker.execute() != DIALOG_OK:
        return None

    urls = file_picker.getSelectedFiles()
    if not urls:
        return None
    # Los FilePicker de UNO regresan file:// URLs; el resto del código
    # (cert_loader, Path) trabaja con rutas de sistema normales.
    return uno.fileUrlToSystemPath(urls[0])


def ask_password(ctx, *, parent_peer=None) -> str | None:
    """Diálogo propio con un solo campo de contraseña (enmascarado) y los
    botones Aceptar/Cancelar. Regresa la contraseña capturada, o ``None``
    si el usuario cancela.

    Se construye a mano (``UnoControlDialogModel``) en vez de usar el
    selector de archivos porque FilePicker no soporta captura de texto.
    """
    from com.sun.star.awt import WindowDescriptor
    from com.sun.star.awt.WindowClass import MODALTOP
    from com.sun.star.awt.VclWindowPeerAttribute import (
        OK,
        CANCEL,
        CLIPCHILDREN,
    )

    smgr = ctx.ServiceManager

    dialog_model = smgr.createInstanceWithContext(
        "com.sun.star.awt.UnoControlDialogModel", ctx
    )
    dialog_model.PositionX = 100
    dialog_model.PositionY = 100
    dialog_model.Width = 180
    dialog_model.Height = 60
    dialog_model.Title = "Contraseña de la e.firma"

    label_model = dialog_model.createInstance("com.sun.star.awt.UnoControlFixedTextModel")
    label_model.PositionX = 10
    label_model.PositionY = 10
    label_model.Width = 160
    label_model.Height = 12
    label_model.Label = "Contraseña de tu e.firma (.key):"
    dialog_model.insertByName("lblPassword", label_model)

    password_model = dialog_model.createInstance("com.sun.star.awt.UnoControlEditModel")
    password_model.PositionX = 10
    password_model.PositionY = 24
    password_model.Width = 160
    password_model.Height = 14
    password_model.EchoChar = ord("*")
    dialog_model.insertByName("txtPassword", password_model)

    ok_model = dialog_model.createInstance("com.sun.star.awt.UnoControlButtonModel")
    ok_model.PositionX = 40
    ok_model.PositionY = 42
    ok_model.Width = 50
    ok_model.Height = 14
    ok_model.Label = "Aceptar"
    ok_model.PushButtonType = 1  # OK
    dialog_model.insertByName("btnOk", ok_model)

    cancel_model = dialog_model.createInstance("com.sun.star.awt.UnoControlButtonModel")
    cancel_model.PositionX = 100
    cancel_model.PositionY = 42
    cancel_model.Width = 50
    cancel_model.Height = 14
    cancel_model.Label = "Cancelar"
    cancel_model.PushButtonType = 2  # CANCEL
    dialog_model.insertByName("btnCancel", cancel_model)

    dialog = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", ctx)
    dialog.setModel(dialog_model)

    toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    dialog.setVisible(False)
    dialog.createPeer(toolkit, parent_peer)

    result = dialog.execute()
    password = None
    if result == 1:  # 1 == OK, ver PushButtonType de btnOk
        password = dialog.getControl("txtPassword").getModel().Text
    dialog.dispose()

    return password or None


def show_signing_dialog(ctx) -> "SigningRequest | None":
    """Orquesta los tres pasos (certificado, llave, contraseña), valida con
    :func:`validate_signing_request` y regresa un :class:`SigningRequest`
    listo para la actividad H, o ``None`` si el usuario cancela en
    cualquier paso.
    """
    certificate_path = pick_certificate_file(ctx)
    if certificate_path is None:
        return None

    private_key_path = pick_private_key_file(ctx)
    if private_key_path is None:
        return None

    password = ask_password(ctx)
    if password is None:
        return None

    errors = validate_signing_request(certificate_path, private_key_path, password)
    if errors:
        # La actividad H decide cómo mostrar estos errores en la UI
        # (p. ej. un MessageBox); aquí se exponen como excepción para no
        # tomar esa decisión de presentación por adelantado.
        raise ValueError("; ".join(errors))

    return SigningRequest(
        certificate_path=certificate_path,
        private_key_path=private_key_path,
        password=password,
    )
