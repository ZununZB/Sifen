# Sifen-Libre

Extensión (.oxt) para LibreOffice Writer que firma digitalmente documentos con los archivos de la e.firma (`.cer`, `.key` y contraseña).

Proyecto de la materia Innovación Tecnológica (Ingeniería de Software, UACJ).

## Equipo

- Víctor Alejandro Rivera Ávila – 226920
- David Raúl Rodríguez Jiménez – 222934
- Jesús Francisco Barrón Huitrón – 180257
- Jesús Alejandro Cardoza Reza – 216024
- Ricardo Zunun Puente – 217024

## Cómo funciona

1. En Writer, abre el menú **SIFEN-Libre → Firmar Documento Digitalmente**.
2. Selecciona tu certificado `.cer`.
3. Selecciona tu llave privada `.key`.
4. Escribe la contraseña de la llave.
5. La extensión valida que la llave corresponda al certificado, firma el texto del documento con RSA-SHA256 y agrega al final un recuadro con los datos de la firma: firmante, RFC, número de serie, fecha, digest, cadena original y sello digital.

La contraseña se borra de la memoria al terminar.

## Requisitos

- LibreOffice con soporte para Python.
- OpenSSL. En Windows sirve el que viene con Git for Windows o una instalación de OpenSSL.

## Instalación

En LibreOffice: **Herramientas → Administrador de extensiones → Añadir** y elige el `.oxt`. Reinicia LibreOffice.

`sifen_libre_v1.oxt` es el paquete que corresponde al código actual. Los archivos `sifen_v2.oxt` a `sifen_v5.oxt` son versiones de prueba anteriores.

## Archivos

| Archivo | Para qué es |
|---|---|
| `sifen_main.py` | Código de la extensión: lectura del certificado, validación de la llave, firma y sello visual |
| `Addons.xcu` | Agrega el menú SIFEN-Libre en Writer |
| `description.xml` | Nombre, versión e identificador de la extensión |
| `META-INF/manifest.xml` | Lista los archivos que LibreOffice carga del `.oxt` |

## Generar el .oxt

Desde la carpeta del repo:

```bash
zip -r sifen_libre.oxt description.xml Addons.xcu sifen_main.py META-INF/manifest.xml
```
