# Sifen-Libre

Extensión nativa (.oxt) para **LibreOffice Writer** que permite firmar digitalmente
documentos oficiales y oficios usando archivos de e.firma (**.cer** / **.key** + contraseña),
sin depender de licencias ofimáticas privativas ni de plataformas web de terceros.

Proyecto de la materia *Innovación Tecnológica* (Ingeniería de Software, UACJ).

## Equipo

- Víctor Alejandro Rivera Ávila – 226920
- David Raúl Rodríguez Jiménez – 222934
- Jesús Francisco Barrón Huitrón – 180257
- Jesús Alejandro Cardoza Reza – 216024
- Ricardo Zunun Puente – 217024

## Estado del proyecto

Ver [`PROGRESS.md`](PROGRESS.md) para el avance contra la ruta crítica (PERT) y el
detalle de qué cubre cada módulo.

## Estructura

```
sifen-libre/
├── description.xml        # Metadatos de la extensión (.oxt)
├── META-INF/manifest.xml  # Manifiesto requerido por el administrador de extensiones
├── registry/Addons.xcu    # Registro del menú/botón dentro de Writer
├── src/
│   ├── core/               # Punto de entrada UNO de la extensión
│   ├── crypto/             # Carga/validación de certificados y motor de firma
│   └── ui/                 # Diálogo de firma (selector de .cer/.key + contraseña)
├── docs/                   # Investigación y diseño de arquitectura
├── scripts/                # Utilidades de desarrollo (pruebas de conexión UNO, build del .oxt)
└── tests/                  # Pruebas unitarias (pytest)
```

## Requisitos de desarrollo

```bash
pip install -r requirements.txt
```

Para probar la conexión con la API UNO se necesita LibreOffice instalado localmente
(ver `scripts/test_conexion_uno.py`).

## Pruebas

```bash
pytest tests/ -v
```

## Empaquetado

```bash
bash scripts/build_oxt.sh
```

Genera `dist/sifen-libre.oxt`, instalable desde el Administrador de Extensiones de
LibreOffice (Herramientas → Administrar extensiones → Agregar).
