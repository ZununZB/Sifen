# Investigación: API UNO e infraestructura PKI (Actividad B)

## 1. API UNO (Universal Network Objects)

LibreOffice expone toda su funcionalidad interna (documentos, menús, diálogos,
formato) a través de **UNO**, un modelo de componentes independiente del
lenguaje. Para una extensión de Writer, las piezas relevantes son:

| Pieza UNO | Para qué la usamos en Sifen-Libre |
|---|---|
| `com.sun.star.task.Job` / `XDispatchProvider` + `XDispatch` | Registrar la entrada de menú "Firmar documento con e.firma..." y recibir el evento de clic (ver `src/core/extension_main.py`). |
| `com.sun.star.frame.Desktop` / `XComponentLoader` | Obtener el documento Writer activo sobre el que se va a firmar. |
| `com.sun.star.beans.XPropertySet` | Leer/escribir metadatos del documento (p. ej. guardar la referencia a la firma aplicada). |
| Diálogos UNO (`com.sun.star.awt.XDialog`) | Interfaz para que el usuario seleccione su `.cer`/`.key` y capture la contraseña (actividad E). |

LibreOffice permite implementar componentes UNO en **Python** (vía el
intérprete embebido `python-uno` / `pyuno`), lo cual evita tener que usar
C++ o Java y es consistente con el resto del stack de este proyecto
(`cryptography` para la parte de firma).

### Dos formas de probar la integración durante desarrollo

1. **Extensión real cargada en LibreOffice** (lo que hace
   `scripts/build_oxt.sh` + instalación manual) — es el camino de producción.
2. **Conexión por socket a una instancia de LibreOffice ya abierta**
   (`scripts/test_conexion_uno.py`) — mucho más rápido para iterar mientras
   se desarrolla, porque no requiere reinstalar la extensión en cada cambio.
   Es el método recomendado para validar que el entorno de cada integrante
   del equipo tiene `pyuno` disponible antes de escribir la UI (actividad E).

## 2. Infraestructura PKI / e.firma

El estándar de e.firma (antes FIEL) usado por el SAT en México se basa en:

- **Certificado público** (`.cer`): X.509, contiene la llave pública y los
  datos del titular. No requiere contraseña para leerse.
- **Llave privada** (`.key`): PKCS#8 cifrada. Requiere la **contraseña** del
  usuario para descifrarse antes de poder firmar con ella.
- El par `.cer`/`.key` corresponde a la misma llave pública/privada; antes de
  firmar hay que **validar que coinciden** (actividad F).

Para firmar, el estándar de facto en documentos de oficina es producir una
firma **CMS/PKCS#7** (lo mismo que usa Word) sobre un hash del contenido del
documento, que es lo que implementa `src/crypto/signer.py` (actividad G).

La librería `cryptography` (Python) cubre ambas necesidades sin dependencias
nativas adicionales:

- Carga y validación de certificados y llaves: `cryptography.x509`,
  `cryptography.hazmat.primitives.serialization`.
- Firma CMS/PKCS#7: `cryptography.hazmat.primitives.serialization.pkcs7`.

## 3. Conclusión para el diseño (alimenta la Actividad C)

- La lógica criptográfica (`src/crypto/`) **no depende de UNO** — se puede
  desarrollar y probar con `pytest` de forma aislada (como se hizo aquí).
- Solo la capa de integración (`src/core/`, `src/ui/`) depende de que
  LibreOffice esté instalado, porque necesita el módulo `uno`/`unohelper`
  que LibreOffice provee en su propio intérprete de Python.
- Esto confirma que separar "crypto" de "UI/integración UNO" (ver
  `docs/architecture.md`) es la división correcta: permite que el equipo
  avance la lógica de firma sin depender de tener LibreOffice instalado en
  cada máquina de desarrollo.
