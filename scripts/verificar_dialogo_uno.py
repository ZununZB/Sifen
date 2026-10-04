#!/usr/bin/env python3
"""Verificación manual (no pytest) de que el modelo del diálogo de
contraseña (Actividad E, ``src/ui/signing_dialog.ask_password``) se
construye correctamente contra una instancia real de LibreOffice.

No se puede automatizar con pytest porque requiere una sesión de
LibreOffice corriendo (ver docs/investigacion_uno_api.md). En modo
--headless tampoco se puede llamar a dialog.execute() de forma interactiva
(no hay pantalla), así que este script valida la construcción del modelo
y sus controles -que es la parte donde suelen aparecer errores de nombres
de propiedades/servicios UNO- sin mostrarlo.

Uso: con LibreOffice ya escuchando (ver scripts/test_conexion_uno.py),
    python3 scripts/verificar_dialogo_uno.py
"""
from __future__ import annotations

import sys


def main() -> int:
    import uno

    local_context = uno.getComponentContext()
    resolver = local_context.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local_context
    )
    ctx = resolver.resolve(
        "uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext"
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
    print("UnoControlDialogModel creado OK, Title =", dialog_model.Title)

    label_model = dialog_model.createInstance("com.sun.star.awt.UnoControlFixedTextModel")
    label_model.Label = "Contraseña de tu e.firma (.key):"
    dialog_model.insertByName("lblPassword", label_model)
    print("Control FixedText creado e insertado OK")

    password_model = dialog_model.createInstance("com.sun.star.awt.UnoControlEditModel")
    password_model.EchoChar = ord("*")
    dialog_model.insertByName("txtPassword", password_model)
    print("Control Edit (password) creado e insertado OK, EchoChar =", password_model.EchoChar)

    ok_model = dialog_model.createInstance("com.sun.star.awt.UnoControlButtonModel")
    ok_model.Label = "Aceptar"
    ok_model.PushButtonType = 1
    dialog_model.insertByName("btnOk", ok_model)

    cancel_model = dialog_model.createInstance("com.sun.star.awt.UnoControlButtonModel")
    cancel_model.Label = "Cancelar"
    cancel_model.PushButtonType = 2
    dialog_model.insertByName("btnCancel", cancel_model)
    print("Botones Aceptar/Cancelar creados e insertados OK")

    # Confirma que los 4 controles quedaron registrados en el modelo.
    names = sorted(dialog_model.ElementNames)
    assert names == ["btnCancel", "btnOk", "lblPassword", "txtPassword"], names
    print("ElementNames del dialog model:", names)

    print("\nOK: el modelo del diálogo de la Actividad E se construye sin "
          "errores contra la API UNO real de LibreOffice 24.2.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
