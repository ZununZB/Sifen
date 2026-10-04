#!/usr/bin/env python3
"""Verificación end-to-end del menú registrado (Actividad D + parte de la E)
contra una instancia real de LibreOffice con la extensión instalada.

Abre un documento Writer en blanco y dispara el dispatch de
``com.sifenlibre.writer.firma:SignDocument`` (la misma acción que ejecuta
el clic en "Archivo > Firmar documento con e.firma..."). Confirma que:

  1. El menú (``registry/Addons.xcu``) y el manejador de protocolo
     (``registry/ProtocolHandler.xcu``) están bien registrados — si no lo
     estuvieran, el dispatch simplemente no haría nada (fue justo el bug
     que este script encontró durante el desarrollo: faltaba
     ProtocolHandler.xcu).
  2. El componente Python (``src/core/extension_main.py``) carga y se
     ejecuta dentro de LibreOffice real, no solo en pruebas unitarias.
  3. El punto de integración con la UI/criptografía (actividad H) sigue
     correctamente pendiente: debe fallar con el ``NotImplementedError``
     documentado, no con un error de registro/carga.

Requiere:
  1) La extensión instalada: ``unopkg add --shared dist/sifen-libre.oxt``
     (ver ``scripts/build_oxt.sh``).
  2) LibreOffice escuchando en el socket (ver ``scripts/test_conexion_uno.py``).
"""
from __future__ import annotations

import sys


def main() -> int:
    import uno

    local_context = uno.getComponentContext()
    resolver = local_context.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local_context
    )
    try:
        ctx = resolver.resolve(
            "uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext"
        )
    except Exception as exc:
        print(f"No se pudo conectar a LibreOffice: {exc}", file=sys.stderr)
        return 1

    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)

    doc = desktop.loadComponentFromURL("private:factory/swriter", "_blank", 0, ())
    print("Documento Writer en blanco creado OK.")

    frame = doc.getCurrentController().getFrame()
    dispatch_helper = smgr.createInstanceWithContext(
        "com.sun.star.frame.DispatchHelper", ctx
    )

    exit_code = 0
    try:
        dispatch_helper.executeDispatch(
            frame, "com.sifenlibre.writer.firma:SignDocument", "", 0, ()
        )
        print(
            "FALLO: el dispatch no lanzó ningún error; eso significa que "
            "nadie lo está manejando (revisar Addons.xcu/ProtocolHandler.xcu)."
        )
        exit_code = 1
    except Exception as exc:
        if "NotImplementedError" in str(exc):
            print(
                "OK: el dispatch llegó hasta nuestro componente y se "
                "detuvo exactamente donde está documentado (pendiente de "
                f"las actividades E/H): {exc}"
            )
        else:
            print(f"FALLO inesperado: {type(exc).__name__}: {exc}", file=sys.stderr)
            exit_code = 1
    finally:
        doc.close(False)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
