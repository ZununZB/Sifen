"""Punto de entrada UNO de la extensión Sifen-Libre.

Este componente se registra ante LibreOffice (vía META-INF/manifest.xml,
registry/Addons.xcu y registry/ProtocolHandler.xcu) y responde a la acción
de menú ``com.sifenlibre.writer.firma:SignDocument`` agregada en Writer.
Registro probado de punta a punta contra LibreOffice real (ver
``scripts/verificar_dispatch_uno.py``).

Alcance actual (Actividad D - configuración del proyecto base):
    Estructura lista y VERIFICADA: el .oxt se empaqueta, se instala
    (``unopkg``) y el dispatch del menú llega hasta este componente, que
    implementa ``com.sun.star.frame.XDispatchProvider``/``XDispatch`` sobre
    el servicio ``com.sun.star.frame.ProtocolHandler``.

Las actividades E (``src/ui/signing_dialog.py``) y G (``src/crypto/signer.py``)
ya están completas por separado. Pendiente (Actividad H - integración):
el método ``dispatch`` hoy solo deja un punto de extensión documentado;
ahí se debe llamar a ``src.ui.signing_dialog.show_signing_dialog``, pasar
el resultado a ``src.crypto.cert_loader.load_and_validate_credentials`` y
luego a ``src.crypto.signer.sign_cms`` sobre el contenido del documento
activo.
"""

from __future__ import annotations

try:
    import unohelper
    from com.sun.star.frame import XDispatchProvider, XDispatch
    from com.sun.star.lang import XServiceInfo

    _HAS_UNO = True
except ImportError:  # pragma: no cover - solo existe dentro de LibreOffice
    _HAS_UNO = False
    unohelper = None  # type: ignore

IMPLEMENTATION_NAME = "com.sifenlibre.writer.firma.SignDocumentJob"
# Debe ser "com.sun.star.frame.ProtocolHandler" (no "com.sun.star.task.Job")
# para que LibreOffice nos entregue el dispatch de la URL registrada en
# registry/ProtocolHandler.xcu. Se detectó este requisito probando el flujo
# completo contra una instancia real de LibreOffice (ver
# scripts/_scratch_dispatch_check.py): con "task.Job" el menú se mostraba
# pero el clic no llegaba a nuestro código.
SUPPORTED_SERVICE_NAMES = ("com.sun.star.frame.ProtocolHandler",)
DISPATCH_URL = "com.sifenlibre.writer.firma:SignDocument"


if _HAS_UNO:

    class SignDocumentDispatch(unohelper.Base, XDispatch):  # type: ignore[misc]
        """Maneja la orden de menú 'Firmar documento con e.firma...'."""

        def dispatch(self, url, args):  # noqa: D401 - firma impuesta por UNO
            # TODO(actividad H): llamar a src.ui.signing_dialog.show_signing_dialog,
            # cargar las credenciales con src.crypto.cert_loader y firmar el
            # documento activo con src.crypto.signer.sign_cms. E y G (las
            # piezas que esto va a conectar) ya están completas.
            raise NotImplementedError(
                "La integración UI <-> motor de firma (actividad H) todavía "
                "no está conectada aquí; src.ui.signing_dialog (actividad E) "
                "y src.crypto.signer (actividad G) ya están listos."
            )

        def addStatusListener(self, control, url):  # noqa: N802 - API UNO
            pass

        def removeStatusListener(self, control, url):  # noqa: N802 - API UNO
            pass

    class SignDocumentProvider(
        unohelper.Base, XDispatchProvider, XServiceInfo  # type: ignore[misc]
    ):
        """Resuelve la URL del menú al dispatcher de arriba."""

        def __init__(self, ctx):
            self.ctx = ctx

        def queryDispatch(self, url, target_frame_name, search_flags):  # noqa: N802
            if url.Main == DISPATCH_URL:
                return SignDocumentDispatch()
            return None

        def queryDispatches(self, requests):  # noqa: N802
            return [self.queryDispatch(r.FeatureURL, r.FrameName, r.SearchFlags) for r in requests]

        def getImplementationName(self):  # noqa: N802
            return IMPLEMENTATION_NAME

        def supportsService(self, service_name):  # noqa: N802
            return service_name in SUPPORTED_SERVICE_NAMES

        def getSupportedServiceNames(self):  # noqa: N802
            return SUPPORTED_SERVICE_NAMES

    def createInstance(ctx):  # noqa: N802 - requerido por el loader de UNO
        return SignDocumentProvider(ctx)

    g_ImplementationHelper = unohelper.ImplementationHelper()
    g_ImplementationHelper.addImplementation(
        createInstance, IMPLEMENTATION_NAME, SUPPORTED_SERVICE_NAMES
    )
