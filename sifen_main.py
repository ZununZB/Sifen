import os
import re
import sys
import base64
import hashlib
import datetime
import subprocess
import shutil
import tempfile
import traceback
import uno
import unohelper
from com.sun.star.task import XJobExecutor


class MotorCriptograficoSifen:
    """Módulo crypto: Validación de certificados X.509 (.cer/.key) y firma RSA-SHA256."""

    def __init__(self):
        self.openssl_bin = self._localizar_openssl()

    def _localizar_openssl(self):
        ruta = shutil.which("openssl")
        if ruta:
            return ruta

        rutas_windows = [
            r"C:\Program Files\Git\usr\bin\openssl.exe",
            r"C:\Program Files\Git\mingw64\bin\openssl.exe",
            r"C:\Program Files\OpenSSL-Win64\bin\openssl.exe",
            r"C:\Program Files (x86)\OpenSSL-Win32\bin\openssl.exe",
            r"C:\Program Files\LibreOffice\program\openssl.exe",
        ]
        for candidato in rutas_windows:
            if os.path.isfile(candidato):
                return candidato
        return None

    def _ejecutar_openssl(self, args, input_bytes=None):
        if not self.openssl_bin:
            raise RuntimeError(
                "No se encontró openssl.exe en el sistema. Instala Git for Windows o OpenSSL."
            )

        startupinfo = None
        creationflags = 0
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = subprocess.CREATE_NO_WINDOW

        proc = subprocess.run(
            [self.openssl_bin] + args,
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
            creationflags=creationflags,
        )
        return proc.returncode, proc.stdout, proc.stderr

    def leer_certificado(self, ruta_cer):
        for fmt in ("DER", "PEM"):
            rc, out, _ = self._ejecutar_openssl(
                ["x509", "-inform", fmt, "-in", ruta_cer, "-noout", "-subject", "-serial", "-dates", "-modulus"]
            )
            if rc == 0:
                texto = out.decode("utf-8", errors="replace")
                return self._parsear_datos_certificado(texto, fmt)

        raise ValueError("El archivo .cer no tiene un formato X.509 válido (DER/PEM).")

    def _parsear_datos_certificado(self, salida_openssl, formato):
        datos = {
            "formato": formato,
            "titular": "No identificado",
            "rfc": "No identificado",
            "serie": "No identificado",
            "valido_desde": "",
            "valido_hasta": "",
            "modulus": "",
        }

        for linea in salida_openssl.splitlines():
            linea = linea.strip()
            if linea.startswith("subject="):
                m_cn = re.search(r"CN\s*=\s*([^,/]+)", linea)
                if m_cn:
                    datos["titular"] = m_cn.group(1).strip()
                m_rfc = re.search(r"([A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3})", linea)
                if m_rfc:
                    datos["rfc"] = m_rfc.group(1)
            elif linea.startswith("serial="):
                raw_serial = linea.split("=", 1)[1].strip()
                try:
                    if len(raw_serial) == 40:
                        datos["serie"] = bytes.fromhex(raw_serial).decode("ascii")
                    else:
                        datos["serie"] = raw_serial
                except Exception:
                    datos["serie"] = raw_serial
            elif linea.startswith("notBefore="):
                datos["valido_desde"] = linea.split("=", 1)[1].strip()
            elif linea.startswith("notAfter="):
                datos["valido_hasta"] = linea.split("=", 1)[1].strip()
            elif linea.startswith("Modulus="):
                datos["modulus"] = linea.split("=", 1)[1].strip()

        return datos

    def validar_llave_y_firmar(self, ruta_key, password_bytes, datos_cert, contenido_bytes):
        formato_key = None
        modulus_key = None
        pem_key = None

        for fmt in ("DER", "PEM"):
            rc, out, _ = self._ejecutar_openssl(
                ["pkcs8", "-inform", fmt, "-in", ruta_key, "-passin", "stdin"],
                input_bytes=password_bytes + b"\n",
            )
            if rc == 0:
                formato_key = fmt
                pem_key = out
                rc_mod, out_mod, _ = self._ejecutar_openssl(
                    ["rsa", "-noout", "-modulus"],
                    input_bytes=pem_key,
                )
                if rc_mod == 0:
                    modulus_key = out_mod.decode("utf-8", errors="replace").strip().replace("Modulus=", "")
                break

        if not formato_key or not pem_key:
            raise ValueError("Contraseña incorrecta o archivo .key dañado.")

        try:
            if datos_cert["modulus"] and modulus_key and datos_cert["modulus"] != modulus_key:
                raise ValueError("El archivo .key NO corresponde al certificado .cer seleccionado.")

            digest_sha256 = hashlib.sha256(contenido_bytes).hexdigest()
            firma_binaria = self._firmar_con_borrado_seguro(pem_key, contenido_bytes)
            sello_b64 = base64.b64encode(firma_binaria).decode("ascii")
            return digest_sha256, sello_b64
        finally:
            pem_mut = bytearray(pem_key)
            for i in range(len(pem_mut)):
                pem_mut[i] = 0

    def _firmar_con_borrado_seguro(self, pem_key_bytes, contenido_bytes):
        with tempfile.NamedTemporaryFile(delete=False) as tmp_doc:
            tmp_doc.write(contenido_bytes)
            tmp_doc_path = tmp_doc.name

        with tempfile.NamedTemporaryFile(delete=False) as tmp_k:
            tmp_k.write(pem_key_bytes)
            tmp_k_path = tmp_k.name

        try:
            rc, sig, err = self._ejecutar_openssl(
                ["dgst", "-sha256", "-sign", tmp_k_path, tmp_doc_path]
            )
            if rc != 0:
                raise RuntimeError(f"Error OpenSSL al firmar: {err.decode('utf-8', errors='replace')}")
            return sig
        finally:
            if os.path.exists(tmp_doc_path):
                os.remove(tmp_doc_path)
            if os.path.exists(tmp_k_path):
                size = os.path.getsize(tmp_k_path)
                with open(tmp_k_path, "wb") as f:
                    f.write(b"\x00" * size)
                os.remove(tmp_k_path)


class SifenExtension(unohelper.Base, XJobExecutor):
    """Controlador principal UI + Core + Crypto de Sifen-Libre."""

    def __init__(self, ctx):
        self.ctx = ctx

    def trigger(self, args):
        desktop = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self.ctx
        )
        model = desktop.getCurrentComponent()

        if not model or not hasattr(model, "Text"):
            return

        text = model.Text
        password_buf = None

        try:
            # 1. Seleccionar certificado .cer
            ruta_cer = self.seleccionar_archivo("Certificado Digital X.509 (.cer)", "*.cer")
            if not ruta_cer:
                return

            # 2. Seleccionar llave privada .key
            ruta_key = self.seleccionar_archivo("Clave Privada PKCS#8 (.key)", "*.key")
            if not ruta_key:
                return

            # 3. Capturar contraseña
            password_str = self.pedir_contrasena()
            if not password_str:
                return

            password_buf = bytearray(password_str.encode("utf-8"))
            del password_str

            # 4. Leer contenido actual del documento
            contenido_doc = text.getString().strip()
            if not contenido_doc:
                contenido_doc = "DOCUMENTO OFICIAL SIN TEXTO PREVIO"

            # 5. Ejecutar validación PKI y firmado digital
            motor = MotorCriptograficoSifen()
            datos_cert = motor.leer_certificado(ruta_cer)
            digest_sha256, sello_digital = motor.validar_llave_y_firmar(
                ruta_key,
                bytes(password_buf),
                datos_cert,
                contenido_doc.encode("utf-8"),
            )

            # 6. Estampar recuadro visual protegido al final del documento
            fecha_firma = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            cadena_original = (
                f"||1.0|{fecha_firma}|{datos_cert['rfc']}|{datos_cert['titular']}|"
                f"{datos_cert['serie']}|{digest_sha256}||"
            )

            self.insertar_sello_visual(
                model,
                datos_cert,
                fecha_firma,
                digest_sha256,
                cadena_original,
                sello_digital,
            )

            self.mostrar_alerta(
                "SIFEN-Libre — Firma Exitosa",
                f"Documento firmado correctamente.\n\nFirmante: {datos_cert['titular']}\nRFC: {datos_cert['rfc']}",
            )

        except Exception as e:
            detalle_error = traceback.format_exc()
            cursor_err = text.createTextCursor()
            cursor_err.gotoEnd(False)
            text.insertString(cursor_err, f"\n[ERROR SIFEN-Libre]: {str(e)}\n", False)
            self.mostrar_alerta("SIFEN-Libre — Error", f"{str(e)}\n\nDetalle:\n{detalle_error[:400]}")
        finally:
            if password_buf is not None:
                for i in range(len(password_buf)):
                    password_buf[i] = 0

    def insertar_sello_visual(self, model, datos_cert, fecha_firma, digest_sha256, cadena_original, sello_digital):
        """
        Inserta un recuadro visual estilizado (TextTable) con bordes institucionales
        y protección contra edición.
        """
        text = model.Text
        cursor = text.createTextCursor()
        cursor.gotoEnd(False)

        text.insertString(cursor, "\n", False)
        cursor.gotoEnd(False)

        tabla = model.createInstance("com.sun.star.text.TextTable")
        tabla.initialize(2, 1)
        text.insertTextContent(cursor, tabla, False)

        # Celda A1: Encabezado
        celda_titulo = tabla.getCellByName("A1")
        celda_titulo.BackColor = 0x1B396A
        celda_titulo.setString("  FIRMADO DIGITALMENTE CON FIRMA ELECTRÓNICA AVANZADA — SIFEN-LIBRE")

        cursor_a1 = celda_titulo.createTextCursor()
        cursor_a1.gotoStart(False)
        cursor_a1.gotoEnd(True)
        cursor_a1.CharColor = 0xFFFFFF
        cursor_a1.CharWeight = 150.0
        cursor_a1.CharHeight = 9.5
        cursor_a1.CharFontName = "Liberation Sans"

        # Celda A2: Cuerpo con datos y sello Base64
        celda_cuerpo = tabla.getCellByName("A2")
        celda_cuerpo.BackColor = 0xF4F6F9

        sello_formateado = "\n".join(
            sello_digital[i:i+72] for i in range(0, len(sello_digital), 72)
        )

        contenido_visual = (
            f"Firmante / Titular: {datos_cert['titular']}\n"
            f"Identificador RFC:  {datos_cert['rfc']}\n"
            f"No. de Certificado: {datos_cert['serie']}\n"
            f"Vigencia:           {datos_cert['valido_desde']}  al  {datos_cert['valido_hasta']}\n"
            f"Fecha de Firmado:   {fecha_firma}\n"
            f"Huella SHA-256:     {digest_sha256}\n"
            f"------------------------------------------------------------------------\n"
            f"Cadena Original:\n{cadena_original}\n"
            f"------------------------------------------------------------------------\n"
            f"Sello Digital (RSA-SHA256):\n{sello_formateado}"
        )
        celda_cuerpo.setString(contenido_visual)

        cursor_a2 = celda_cuerpo.createTextCursor()
        cursor_a2.gotoStart(False)
        cursor_a2.gotoEnd(True)
        cursor_a2.CharColor = 0x1A1A1A
        cursor_a2.CharHeight = 8.0
        cursor_a2.CharFontName = "Liberation Mono"

        borde = uno.createUnoStruct("com.sun.star.table.BorderLine2")
        borde.Color = 0x1B396A
        borde.OuterLineWidth = 35

        for celda in (celda_titulo, celda_cuerpo):
            celda.TopBorder = borde
            celda.BottomBorder = borde
            celda.LeftBorder = borde
            celda.RightBorder = borde
            celda.TopBorderDistance = 120
            celda.BottomBorderDistance = 120
            celda.LeftBorderDistance = 150
            celda.RightBorderDistance = 150
            celda.IsProtected = True

    def seleccionar_archivo(self, titulo, filtro):
        file_picker = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.ui.dialogs.FilePicker", self.ctx
        )
        file_picker.appendFilter(titulo, filtro)
        file_picker.setTitle(f"SIFEN-Libre - Selecciona tu {titulo}")

        if file_picker.execute() == 1:
            archivos = file_picker.getFiles()
            return uno.fileUrlToSystemPath(archivos[0])
        return None

    def pedir_contrasena(self):
        smgr = self.ctx.ServiceManager
        dialog_model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", self.ctx)

        dialog_model.PositionX = 100
        dialog_model.PositionY = 100
        dialog_model.Width = 170
        dialog_model.Height = 75
        dialog_model.Title = "SIFEN-Libre - Autenticación PKI"

        label_model = dialog_model.createInstance("com.sun.star.awt.UnoControlFixedTextModel")
        label_model.PositionX = 8
        label_model.PositionY = 10
        label_model.Width = 154
        label_model.Height = 14
        label_model.Label = "Ingresa la contraseña de tu clave privada (.key):"
        dialog_model.insertByName("Label", label_model)

        edit_model = dialog_model.createInstance("com.sun.star.awt.UnoControlEditModel")
        edit_model.PositionX = 8
        edit_model.PositionY = 26
        edit_model.Width = 154
        edit_model.Height = 14
        edit_model.EchoChar = ord("*")
        dialog_model.insertByName("Edit", edit_model)

        btn_ok = dialog_model.createInstance("com.sun.star.awt.UnoControlButtonModel")
        btn_ok.PositionX = 35
        btn_ok.PositionY = 50
        btn_ok.Width = 45
        btn_ok.Height = 15
        btn_ok.Label = "Firmar"
        btn_ok.PushButtonType = 1
        btn_ok.DefaultButton = True
        dialog_model.insertByName("BtnOK", btn_ok)

        btn_cancel = dialog_model.createInstance("com.sun.star.awt.UnoControlButtonModel")
        btn_cancel.PositionX = 90
        btn_cancel.PositionY = 50
        btn_cancel.Width = 45
        btn_cancel.Height = 15
        btn_cancel.Label = "Cancelar"
        btn_cancel.PushButtonType = 2
        dialog_model.insertByName("BtnCancel", btn_cancel)

        dialog = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", self.ctx)
        dialog.setModel(dialog_model)
        toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", self.ctx)
        dialog.createPeer(toolkit, None)

        result = dialog.execute()
        password = ""
        if result == 1:
            control = dialog.getControl("Edit")
            password = control.getText()
            control.setText("")

        dialog.dispose()
        return password

    def mostrar_alerta(self, titulo, mensaje):
        desktop = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", self.ctx)
        frame = desktop.getCurrentFrame()
        window = frame.getContainerWindow() if frame else None
        toolkit = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.awt.Toolkit", self.ctx)
        if toolkit and window:
            msgbox = toolkit.createMessageBox(
                window,
                "infobox",
                1,
                titulo,
                mensaje,
            )
            msgbox.execute()


# --- REGISTRO EXPLÍCITO DE EXTENSIÓN ---
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(
    SifenExtension,
    "org.sifenlibre.extension.SifenExtension",
    ("com.sun.star.task.Job",),
)

def getComponentFactory(implementation_name, service_manager, registry_key):
    return g_ImplementationHelper.getComponentFactory(implementation_name, service_manager, registry_key)

def writeRegistryInfo(service_manager, registry_key):
    return g_ImplementationHelper.writeRegistryInfo(service_manager, registry_key)