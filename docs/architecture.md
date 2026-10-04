# Arquitectura de la extensión (Actividad C)

## Objetivo del diseño

Separar lo que **depende de LibreOffice** (solo se puede probar dentro de la
suite) de lo que **no depende de LibreOffice** (lógica de certificados y
firma, probable con `pytest` en cualquier máquina). Esto permite que el
equipo avance en paralelo y que la lógica criptográfica tenga cobertura de
pruebas real desde el día uno.

```
┌─────────────────────────────────────────────────────────────┐
│                      LibreOffice Writer                      │
│                                                                │
│   Menú "Firmar documento con e.firma..." (registry/Addons.xcu)│
│                         │                                     │
│                         ▼                                     │
│              src/core/extension_main.py                       │
│         (componente UNO: XDispatchProvider/XDispatch)         │
│                         │                                     │
│                         ▼                                     │
│                  src/ui/signing_dialog.py                     │
│        (diálogo: elegir .cer/.key, capturar contraseña)       │
│                         │                                     │
└─────────────────────────┼─────────────────────────────────────┘
                           │  bytes del documento + ruta .cer/.key + password
                           ▼
              ┌─────────────────────────────┐
              │        src/crypto/           │   ← sin dependencia de UNO,
              │  cert_loader.py  signer.py    │     100% cubierto por pytest
              └─────────────────────────────┘
```

## Módulos

### `src/core/` — integración con LibreOffice (depende de UNO)

- `extension_main.py`: punto de entrada que registra el componente UNO y
  conecta la acción de menú con la UI. **Actividad D** (estructura) ya
  está lista; la lógica del `dispatch()` se completa en la **actividad H**
  (integración interfaz + criptografía).

### `src/ui/` — interfaz gráfica (depende de UNO)

- `signing_dialog.py` (**actividad E, completa en este avance**): selector
  de archivos estándar de LibreOffice (filtrado a `.cer` y `.key`) + un
  diálogo propio con un campo de contraseña enmascarado
  (`UnoControlEditModel.EchoChar`), replicando el flujo ya conocido de
  Word (requisito de la **actividad A**). La validación de los datos
  capturados (`validate_signing_request`) es Python puro y tiene pruebas
  unitarias; la construcción del modelo del diálogo se validó aparte
  contra una instancia real de LibreOffice
  (`scripts/verificar_dialogo_uno.py`), porque ejecutar un diálogo modal
  interactivo no se puede automatizar con pytest (necesita una sesión de
  LibreOffice con interfaz).

### `src/crypto/` — núcleo criptográfico (independiente de UNO)

- `cert_loader.py` (**actividad F, completa**): carga `.cer`/`.key`, valida
  vigencia del certificado y que la llave privada corresponda al
  certificado.
- `signer.py` (**actividad G, completa**): produce una firma CMS/PKCS#7
  *detached* sobre el contenido del documento (`sign_cms`), permite
  confirmar el certificado embebido en el blob (`extract_signer_certificate`)
  y agrega una verificación criptográfica real RSA-SHA256 de punta a punta
  (`sign_raw_digest` / `verify_raw_digest`). Ver la nota de alcance en el
  docstring del módulo: verificar el blob CMS completo (más allá del
  certificado embebido) queda para una siguiente iteración porque requiere
  un parser ASN.1 de CMS que hoy no es parte de las dependencias del
  proyecto.

### Registro ante LibreOffice (actividad D)

- `registry/Addons.xcu` agrega la entrada de menú.
- `registry/ProtocolHandler.xcu` conecta esa entrada con nuestro componente
  Python (`extension_main.SignDocumentProvider`, que implementa
  `com.sun.star.frame.ProtocolHandler`). **Este archivo se agregó después
  de encontrar, probando contra LibreOffice real
  (`scripts/verificar_dispatch_uno.py`), que sin él el menú aparecía pero
  el clic no llegaba a ningún lado** — buen ejemplo de por qué vale la
  pena probar la integración de punta a punta y no solo cada módulo por
  separado.

## Por qué esta separación

1. **Testeable sin LibreOffice instalado**: la parte de más riesgo técnico
   (manejo correcto de criptografía) tiene pruebas unitarias desde ya.
2. **Permite trabajo en paralelo**: un integrante puede seguir la actividad E
   (UI) mientras otro continúa la G (firma) sin pisarse, porque el contrato
   entre capas es explícito (funciones puras que reciben/retornan `bytes`,
   sin estado compartido).
3. **Acota el riesgo de la API UNO**: solo dos módulos (`core`, `ui`)
   requieren el intérprete de LibreOffice; si hay bloqueos de entorno (ver
   `docs/investigacion_uno_api.md`), no frenan el resto del equipo.
