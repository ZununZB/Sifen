# Avance contra la ruta crítica (PERT)

Ruta crítica de `Red PERT y Tablas.xlsx`: **A → B → C → F → G → H → I → J → L → M**
(60 días hábiles esperados en total, del 24 de agosto al 13 de noviembre).

Este avance cubre **A, B, C, D, F, E y G** (día esperado acumulado: **34 de 60**,
D y E no son parte de la ruta crítica pero son infraestructura necesaria para
poder escribir cualquier código real). Queda pendiente **H** (integración
interfaz + criptografía), que depende de E y G — ambas ya entregadas aquí.

| Act. | Descripción | Día acum. (ruta crítica) | Estado | Dónde está |
|---|---|---:|---|---|
| A | Análisis de requisitos y flujo de Word | 5 | ✅ Cubierto (ver Fase 1 + replica el flujo "Firmar documento" en el menú) | `registry/Addons.xcu` |
| B | Análisis de API UNO e infraestructura PKI | 11 | ✅ Completo, con conexión UNO real probada | `docs/investigacion_uno_api.md`, `scripts/test_conexion_uno.py` |
| C | Diseño de arquitectura de la extensión | 14 | ✅ Completo | `docs/architecture.md` |
| D | Configuración del proyecto base (.oxt) | — (no crítica, holgura 7) | ✅ Completo, instalado y registrado en LibreOffice real | `description.xml`, `META-INF/`, `registry/`, `scripts/build_oxt.sh` |
| F | Lectura y validación de .cer/.key | 22 | ✅ Completo, con pruebas unitarias | `src/crypto/cert_loader.py`, `tests/test_cert_loader.py` |
| E | Interfaz gráfica y menú dedicado | — (no crítica) | ✅ Completo (selector de archivos + diálogo de contraseña), modelo de diálogo validado contra LibreOffice real | `src/ui/signing_dialog.py`, `scripts/verificar_dialogo_uno.py` |
| G | Motor de firma digital | 34 | ✅ Completo (firma CMS/PKCS#7 + verificación RSA-SHA256), con pruebas unitarias | `src/crypto/signer.py`, `tests/test_signer.py` |
| H | Integración interfaz + lógica criptográfica | 39 | ⏳ Pendiente (siguiente avance) | `src/core/extension_main.py::dispatch` (ya tiene el TODO marcado) |
| I | Pruebas unitarias y control de calidad | 44 | ⏳ Pendiente | — |
| J | Auditorías de seguridad informática | 51 | ⏳ Pendiente | — |
| K | Documentación y manuales de usuario | — | ⏳ Pendiente (no crítica) | — |
| L | Despliegue en repositorio y portal web | 54 | ⏳ Pendiente | — |
| M | Campaña de concientización institucional | 60 | ⏳ Pendiente | — |

## Qué quedó realmente verificado (no solo escrito)

No todo quedó en "se ve bien a simple vista": lo siguiente se probó contra
una instancia real de LibreOffice 24.2 corriendo en este entorno, no solo
revisado a ojo:

1. **21 pruebas unitarias en verde** (`pytest tests/ -v`) cubriendo
   `cert_loader`, `signer` y la parte pura de `signing_dialog`, con
   certificados/llaves de prueba autofirmados generados en cada corrida
   (nunca credenciales reales).
2. **El `.oxt` se empaqueta y se instala sin errores** (`unopkg add --shared
   dist/sifen-libre.oxt` → `is registered: yes` para el menú, el manejador
   de protocolo y el componente Python).
3. **El modelo del diálogo de contraseña (actividad E) se construye sin
   errores** contra la API UNO real (`scripts/verificar_dialogo_uno.py`).
4. **El flujo de menú funciona de punta a punta dentro de LibreOffice**:
   se abrió un documento Writer real, se disparó el dispatch del menú
   "Firmar documento con e.firma..." y llegó hasta nuestro componente
   (`scripts/verificar_dispatch_uno.py`). Esto encontró y corrigió un bug
   real durante el desarrollo: faltaba `registry/ProtocolHandler.xcu` — sin
   él, el menú aparecía pero el clic no llegaba a ningún lado.

## Qué falta a propósito (actividad H en adelante)

- `src/core/extension_main.py::dispatch` tiene un `NotImplementedError`
  documentado: ahí se debe llamar a `signing_dialog.show_signing_dialog`,
  pasar el resultado a `cert_loader.load_and_validate_credentials` y luego
  a `signer.sign_cms` sobre el contenido del documento activo.
- `signer.py` deja la firma CMS como blob independiente; falta embeberla en
  el propio `.odt` siguiendo el esquema de firmas de ODF
  (`META-INF/documentsignatures.xml`).
- La verificación de punta a punta del blob CMS completo (más allá de
  `extract_signer_certificate`) requiere agregar un parser ASN.1 de CMS
  (p. ej. `asn1crypto`) — documentado como nota de alcance en
  `src/crypto/signer.py`.
