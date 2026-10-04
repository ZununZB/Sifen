#!/usr/bin/env python3
"""Prueba de conexión a la API UNO (Actividad B).

Valida que se puede controlar una instancia de LibreOffice ya abierta desde
Python vía el puente UNO, sin necesidad de instalar la extensión como .oxt.
Es la forma más rápida de confirmar que el entorno de un integrante del
equipo tiene todo lo necesario antes de empezar a programar sobre la API UNO.

Uso:
    1) Arrancar LibreOffice escuchando en un socket:

       soffice --headless --accept="socket,host=localhost,port=2002;urp;" &

    2) Correr este script:

       python3 scripts/test_conexion_uno.py

Requiere que `python3` sea el intérprete empaquetado con LibreOffice (o que
tenga el paquete `python3-uno` / `pyuno` instalado), ya que el módulo `uno`
no está disponible vía pip.
"""
from __future__ import annotations

import sys


def main() -> int:
    try:
        import uno  # type: ignore
        from com.sun.star.beans import PropertyValue  # type: ignore
    except ImportError:
        print(
            "No se encontró el módulo 'uno'. Este script debe ejecutarse con "
            "el intérprete de Python de LibreOffice (pyuno), no con un "
            "Python genérico. Ver docstring para instrucciones.",
            file=sys.stderr,
        )
        return 1

    local_context = uno.getComponentContext()
    resolver = local_context.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local_context
    )

    try:
        context = resolver.resolve(
            "uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext"
        )
    except Exception as exc:  # pragma: no cover - requiere LibreOffice corriendo
        print(f"No se pudo conectar a LibreOffice: {exc}", file=sys.stderr)
        print(
            "¿Arrancaste LibreOffice con --accept=\"socket,host=localhost,"
            'port=2002;urp;"? Ver docstring.',
            file=sys.stderr,
        )
        return 1

    smgr = context.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", context)

    open_documents = sum(1 for _ in desktop.Components)

    print("Conexión UNO establecida correctamente.")
    print(f"Documentos abiertos: {open_documents}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
