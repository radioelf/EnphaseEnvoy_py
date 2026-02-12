'''
Código para leer los datos de un Envoy / IQ Gateway de Enphase V8:
✅ Autenticación segura con Enphase Cloud
✅ Gestión inteligente de tokens (cache)
✅ Auto-recuperación ante errores
✅ Lectura de todos los datos del Envoy
✅ Presentación de los datos leídos por consola

Configurar ip y credenciales:
ENVOY_IP =                    # IP de tu Envoy
ENPHASE_EMAIL = "             # Email de Enphase
ENPHASE_PASSWORD =            # Contraseña de Enphase

Creative Commons License Disclaimer

UNLESS OTHERWISE MUTUALLY AGREED TO BY THE PARTIES IN WRITING, LICENSOR 
OFFERS THE WORK AS-IS AND MAKES NO REPRESENTATIONS OR WARRANTIES OF ANY 
KIND CONCERNING THE WORK, EXPRESS, IMPLIED, STATUTORY OR OTHERWISE, 
INCLUDING, WITHOUT LIMITATION, WARRANTIES OF TITLE, MERCHANTIBILITY, 
FITNESS FOR A PARTICULAR PURPOSE, NONINFRINGEMENT, OR THE ABSENCE OF 
LATENT OR OTHER DEFECTS, ACCURACY, OR THE PRESENCE OF ABSENCE OF ERRORS,
WHETHER OR NOT DISCOVERABLE. SOME JURISDICTIONS DO NOT ALLOW THE EXCLUSION 
OF IMPLIED WARRANTIES, SO SUCH EXCLUSION MAY NOT APPLY TO YOU. EXCEPT TO 
THE EXTENT REQUIRED BY APPLICABLE LAW, IN NO EVENT WILL LICENSOR BE 
LIABLE TO YOU ON ANY LEGAL THEORY FOR ANY SPECIAL, INCIDENTAL, 
CONSEQUENTIAL, PUNITIVE OR EXEMPLARY DAMAGES ARISING OUT OF THIS LICENSE 
OR THE USE OF THE WORK, EVEN IF LICENSOR HAS BEEN ADVISED OF THE 
POSSIBILITY OF SUCH DAMAGES.

http://creativecommons.org/licenses/by-sa/3.0/
'''

import requests
import json
from datetime import datetime, timedelta
import urllib3
import re
import os

# Desactivar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Archivo donde se guardará el token (en el mismo directorio que el script)
TOKEN_FILE = "envoy_token.json"

class EnphaseEnvoyV8Final:
    """
    Acceso al Envoy con firmware 8.x+ usando el método correcto de autenticación
    """
    
    def __init__(self, host, enphase_email, enphase_password):
        """
        Args:
            host: IP del Envoy (ej: '192.168.x.x')
            enphase_email: Email de tu cuenta Enphase Enlighten
            enphase_password: Contraseña de tu cuenta Enphase
        """
        self.host = host
        self.base_url = f"https://{host}"
        self.enphase_email = enphase_email
        self.enphase_password = enphase_password
        self.token = None
        self.session = requests.Session()
        self.session.verify = False
        self.serial = None
    
    def save_token(self):
        """Guarda el token en un archivo con timestamp"""
        try:
            token_data = {
                'token': self.token,
                'serial': self.serial,
                'timestamp': datetime.now().isoformat(),
                'email': self.enphase_email
            }
            with open(TOKEN_FILE, 'w') as f:
                json.dump(token_data, f)
            print(f"💾 Token guardado en {TOKEN_FILE}")
        except Exception as e:
            print(f"⚠️  No se pudo guardar el token: {e}")
    
    def load_token(self):
        """Carga el token desde el archivo si existe y es válido"""
        try:
            if not os.path.exists(TOKEN_FILE):
                return False
            
            with open(TOKEN_FILE, 'r') as f:
                token_data = json.load(f)
            
            # Verificar que el token sea para el mismo email
            if token_data.get('email') != self.enphase_email:
                print("ℹ️  Token guardado es para otro usuario")
                return False
            
            # Verificar que no haya expirado (24 horas)
            token_time = datetime.fromisoformat(token_data['timestamp'])
            time_diff = datetime.now() - token_time
            
            if time_diff > timedelta(hours=23):  # 23 horas para estar seguros
                print("ℹ️  Token expirado (>23 horas)")
                return False
            
            # Token válido
            self.token = token_data['token']
            self.serial = token_data['serial']
            
            hours_old = time_diff.total_seconds() / 3600
            print(f"✓ Token cargado desde archivo (antigüedad: {hours_old:.1f} horas)")
            
            # Configurar headers con el token
            self.session.headers.update({
                'Authorization': f'Bearer {self.token}'
            })
            
            return True
            
        except Exception as e:
            print(f"⚠️  Error cargando token: {e}")
            return False
    
    def get_envoy_serial(self):
        """Obtiene el número de serie del Envoy"""
        try:
            url = f"{self.base_url}/info.xml"
            response = self.session.get(url, timeout=10)
            match = re.search(r'<sn>(\d+)</sn>', response.text)
            if match:
                self.serial = match.group(1)
                return self.serial
            return None
        except Exception as e:
            print(f"❌ Error obteniendo serial: {e}")
            return None
    
    def get_token(self):
        """Obtiene token JWT usando el método correcto"""
        try:
            # Paso 1: Login en Enlighten
            print("🔐 Autenticando en Enphase Cloud...")
            login_url = "https://enlighten.enphaseenergy.com/login/login.json"
            
            login_data = {
                'user[email]': self.enphase_email,
                'user[password]': self.enphase_password
            }
            
            response = requests.post(login_url, data=login_data, timeout=15)
            
            if response.status_code != 200:
                print(f"❌ Error en login: Status {response.status_code}")
                return False
            
            response_data = json.loads(response.text)
            
            if 'session_id' not in response_data:
                print("❌ Login fallido - verifica tus credenciales")
                return False
            
            session_id = response_data['session_id']
            print(f"✓ Login exitoso")
            
            # Paso 2: Obtener serial del Envoy si no lo tenemos
            if not self.serial:
                self.get_envoy_serial()
            
            if not self.serial:
                print("❌ No se pudo obtener el serial del Envoy")
                return False
            
            print(f"✓ Serial del Envoy: {self.serial}")
            
            # Paso 3: Obtener token usando el endpoint correcto
            print("🔑 Obteniendo token JWT...")
            token_url = "https://entrez.enphaseenergy.com/tokens"
            
            token_data = {
                'session_id': session_id,
                'serial_num': self.serial,
                'username': self.enphase_email
            }
            
            token_response = requests.post(token_url, json=token_data, timeout=15)
            
            if token_response.status_code != 200:
                print(f"❌ Error obteniendo token: Status {token_response.status_code}")
                return False
            
            self.token = token_response.text.strip()
            
            print(f"✓ Token JWT obtenido exitosamente")
            
            # Guardar el token para uso futuro
            self.save_token()
            
            # Configurar headers con el token
            self.session.headers.update({
                'Authorization': f'Bearer {self.token}'
            })
            
            return True
            
        except Exception as e:
            print(f"❌ Error en autenticación: {e}")
            return False
    
    def authenticate(self):
        """Autentica con Enphase Cloud y obtiene token"""
        # Primero intentar cargar el token guardado
        if self.load_token():
            # Verificar que el token funcione
            try:
                print("🔍 Verificando token guardado...")
                test_url = f"{self.base_url}/production.json"
                response = self.session.get(test_url, timeout=5)
                
                if response.status_code == 200:
                    print("✓ Token guardado es válido, reutilizando")
                    return True
                else:
                    print("⚠️  Token guardado no funciona, obteniendo uno nuevo...")
            except:
                print("⚠️  Error verificando token, obteniendo uno nuevo...")
        
        # Si no hay token válido, obtener uno nuevo
        return self.get_token()
    
    def _make_request(self, url, timeout=10):
        """
        Hace una petición con auto-renovación de token si expira
        
        Args:
            url: URL a consultar
            timeout: Tiempo de espera
            
        Returns:
            Response object o None si falla
        """
        try:
            response = self.session.get(url, timeout=timeout)
            
            # Si es 401 (no autorizado), el token puede haber expirado
            if response.status_code == 401:
                print("⚠️  Token expirado (401), renovando automáticamente...")
                
                # Eliminar token guardado
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                
                # Obtener nuevo token
                if self.get_token():
                    # Reintentar la petición con el nuevo token
                    print("🔄 Reintentando petición con nuevo token...")
                    response = self.session.get(url, timeout=timeout)
                else:
                    print("❌ No se pudo renovar el token")
                    return None
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error en petición: {e}")
            return None
    
    def get_production_json(self):
        """Obtiene datos de producción"""
        url = f"{self.base_url}/production.json"
        response = self._make_request(url)
        
        if response:
            try:
                return response.json()
            except json.JSONDecodeError:
                print(f"❌ Error decodificando JSON")
                return None
        return None
    
    def get_api_production(self):
        """Obtiene datos de producción v1"""
        url = f"{self.base_url}/api/v1/production"
        response = self._make_request(url)
        
        if response:
            try:
                return response.json()
            except json.JSONDecodeError:
                return None
        return None
    
    def get_ivp_meters(self):
        """Obtiene lecturas de medidores (usa /readings que tiene más datos)"""
        # Usar directamente /ivp/meters/readings que tiene activePower y más datos
        url = f"{self.base_url}/ivp/meters/readings"
        response = self._make_request(url)
        
        if response:
            try:
                return response.json()
            except:
                return None
        return None
    
    def get_inverters(self):
        """Obtiene datos de inversores individuales"""
        url = f"{self.base_url}/api/v1/production/inverters"
        response = self._make_request(url)
        
        if response:
            try:
                return response.json()
            except json.JSONDecodeError:
                return None
        return None
    
    def get_info(self):
        """Obtiene información del sistema"""
        try:
            url = f"{self.base_url}/info.xml"
            response = self.session.get(url, timeout=10)
            text = response.text
            info = {}
            
            # El XML tiene una estructura anidada <device><sn>...</sn></device>
            # Extraer todo el bloque <device>
            device_match = re.search(r'<device>(.*?)</device>', text, re.DOTALL)
            if device_match:
                device_block = device_match.group(1)
                
                # Extraer campos dentro del bloque device
                sn_match = re.search(r'<sn>(.*?)</sn>', device_block)
                pn_match = re.search(r'<pn>(.*?)</pn>', device_block)
                software_match = re.search(r'<software>(.*?)</software>', device_block)
                
                if sn_match:
                    info['sn'] = sn_match.group(1)
                if pn_match:
                    info['pn'] = pn_match.group(1)
                if software_match:
                    info['software'] = software_match.group(1)
                
                # El device siempre es "Envoy" según el XML
                info['device'] = 'Envoy'
            
            return info
        except requests.exceptions.RequestException as e:
            print(f"❌ Error obteniendo info: {e}")
            return None


class EnvoyDataFormatter:
    """Clase para formatear y mostrar datos del Envoy de forma legible"""
    
    @staticmethod
    def print_header(title):
        """Imprime un encabezado bonito"""
        print("\n" + "=" * 60)
        print(f"  {title}")
        print("=" * 60)
    
    @staticmethod
    def print_system_info(info):
        """Muestra información del sistema"""
        if not info:
            return
        
        EnvoyDataFormatter.print_header("📋 INFORMACIÓN DEL SISTEMA")
        print(f"Dispositivo:               {info.get('device', 'N/A')}")
        print(f"Número de serie:           {info.get('sn', 'N/A')}")
        print(f"Modelo:                    {info.get('pn', 'N/A')}")
        print(f"Versión de software:       {info.get('software', 'N/A')}")
    
    @staticmethod
    def print_production_summary(production_data):
        """Muestra resumen de producción de forma legible"""
        if not production_data:
            print("❌ No hay datos de producción disponibles")
            return
        
        EnvoyDataFormatter.print_header("📊 RESUMEN DE PRODUCCIÓN")
        
        if 'production' in production_data:
            for item in production_data['production']:
                if item.get('type') == 'eim' or item.get('measurementType') == 'production':
                    wNow = item.get('wNow', 0)
                    whToday = item.get('whToday', 0)
                    whLastSevenDays = item.get('whLastSevenDays', 0)
                    whLifetime = item.get('whLifetime', 0)
                    
                    print(f"⚡ Potencia actual:        {wNow:>8} W")
                    print(f"📅 Producción hoy:         {whToday/1000:>8.2f} kWh")
                    print(f"📆 Última semana:          {whLastSevenDays/1000:>8.2f} kWh")
                    print(f"📈 Producción total:       {whLifetime/1000:>8.2f} kWh")
                    return
    
    @staticmethod
    def print_meters_summary(meters_data):
        """Muestra resumen de medidores de forma legible"""
        if not meters_data:
            print("ℹ️  No hay datos de medidores disponibles")
            return
        
        EnvoyDataFormatter.print_header("🔌 MEDIDORES")
        
        if isinstance(meters_data, list):
            for meter in meters_data:
                # Identificar el tipo de medidor por el eid
                eid = meter.get('eid')
                active_power = meter.get('activePower', 0)
                
                # 704643328 = production, 704643584 = net-consumption
                if eid == 704643328:
                    icon = "☀️"
                    name = "PRODUCCIÓN"
                elif eid == 704643584:
                    icon = "🏠"
                    name = "CONSUMO NETO"
                elif eid == 1023410688:
                    # Este parece ser un medidor de almacenamiento inactivo
                    continue
                else:
                    icon = "📊"
                    name = f"MEDIDOR {eid}"
                
                print(f"\n{icon} {name}:")
                print(f"   Potencia activa:        {active_power:>8.1f} W")
                
                if 'actEnergyDlvd' in meter:
                    energy = meter['actEnergyDlvd'] / 1000
                    print(f"   Energía entregada:      {energy:>8.2f} kWh")
                
                if 'actEnergyRcvd' in meter:
                    energy = meter['actEnergyRcvd'] / 1000
                    print(f"   Energía recibida:       {energy:>8.2f} kWh")
                
                if 'voltage' in meter:
                    print(f"   Voltaje:                {meter['voltage']:>8.1f} V")
                
                if 'current' in meter:
                    print(f"   Corriente:              {meter['current']:>8.3f} A")
                
                if 'freq' in meter:
                    print(f"   Frecuencia:             {meter['freq']:>8.1f} Hz")
    
    @staticmethod
    def print_inverters_summary(inverters_data, show_all=False):
        """Muestra resumen de inversores de forma legible"""
        if not inverters_data:
            print("ℹ️  No hay datos de inversores disponibles")
            return
        
        EnvoyDataFormatter.print_header("🔆 INVERSORES")
        
        total_inverters = len(inverters_data)
        active_inverters = sum(1 for inv in inverters_data if inv.get('lastReportWatts', 0) > 0)
        total_power = sum(inv.get('lastReportWatts', 0) for inv in inverters_data)
        
        print(f"Total de inversores:       {total_inverters}")
        print(f"Inversores activos:        {active_inverters}")
        print(f"Potencia total:            {total_power} W")
        
        if show_all and total_inverters > 0:
            print(f"\nDetalle por inversor:")
            print("-" * 60)
            for i, inv in enumerate(inverters_data, 1):
                power = inv.get('lastReportWatts', 0)
                status = "🟢" if power > 0 else "🔴"
                serial = inv.get('serialNumber', 'N/A')
                print(f"{status} Inv {i:2d} | Serial: {serial:15} | {power:4d} W")
        elif not show_all and total_inverters > 0:
            print(f"\n💡 Modifica show_all=True en el código para ver detalle")
    
    @staticmethod
    def print_current_status(production_data, meters_data):
        """Muestra el estado actual del sistema de forma clara"""
        EnvoyDataFormatter.print_header("⚡ ESTADO ACTUAL DEL SISTEMA")
        
        production_w = 0
        consumption_w = 0
        total_consumption_w = 0
        
        # Obtener producción desde production.json
        if production_data and 'production' in production_data:
            for item in production_data['production']:
                if item.get('type') == 'eim' and item.get('measurementType') == 'production':
                    production_w = item.get('wNow', 0)
                    break
        
        # Obtener consumo desde production.json (es más confiable)
        if production_data and 'consumption' in production_data:
            for item in production_data['consumption']:
                if item.get('measurementType') == 'net-consumption':
                    consumption_w = item.get('wNow', 0)
                elif item.get('measurementType') == 'total-consumption':
                    total_consumption_w = item.get('wNow', 0)
        
        # Mostrar estado
        print(f"☀️  Producción solar:       {production_w:>8.1f} W")
        
        if total_consumption_w > 0:
            print(f"🏠 Consumo total:          {total_consumption_w:>8.1f} W")
            print(f"📊 Consumo neto:           {consumption_w:>8.1f} W")
            print("-" * 60)
            
            # El consumo neto ya incluye la producción restada
            # Si es positivo = importando, si es negativo = exportando
            if consumption_w > 0:
                # Estamos importando de la red
                exportando = False
                grid_power = consumption_w
                print(f"📥 Importando de red:      {grid_power:>8.1f} W")
            else:
                # Estamos exportando a la red  
                exportando = True
                grid_power = abs(consumption_w)
                print(f"📤 Exportando a red:       {grid_power:>8.1f} W  ✓")
            
            # Calcular autoconsumo
            if total_consumption_w > 0:
                autoconsumo_w = min(production_w, total_consumption_w)
                percentage = (autoconsumo_w / total_consumption_w * 100) if total_consumption_w > 0 else 0
                print(f"🌱 Autoconsumo:            {percentage:>7.1f} %")
        else:
            print(f"🏠 Consumo: No disponible")


# ============================================
# CONFIGURACIÓN - MODIFICA ESTOS VALORES
# ============================================
ENVOY_IP = "192.168.x.x"                      # IP de tu Envoy
ENPHASE_EMAIL = "tu@email.com"                # Email de Enphase
ENPHASE_PASSWORD = "tupassword"               # Contraseña de Enphase

# Opción para pedir credenciales interactivamente
ASK_CREDENTIALS = True                        # True = pedir en cada ejecución

# Opción para forzar renovación del token
FORCE_NEW_TOKEN = False                       # True = siempre obtener token nuevo
                                              # False = reutilizar token guardado

# ============================================
# PROGRAMA PRINCIPAL
# ============================================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  ENVOY READER - FIRMWARE 8.x+ (MÉTODO CORRECTO)")
    print("=" * 60)
    
    # Pedir credenciales si está activado
    if ASK_CREDENTIALS:
        print("\n📝 Introduce las credenciales de acceso:\n")
        
        envoy_ip = input(f"📍 IP del Envoy [{ENVOY_IP}]: ").strip() or ENVOY_IP
        email = input(f"📧 Email de Enphase [{ENPHASE_EMAIL}]: ").strip() or ENPHASE_EMAIL
        
        import getpass
        password = getpass.getpass("🔒 Contraseña de Enphase: ") or ENPHASE_PASSWORD
        
        print("")
    else:
        envoy_ip = ENVOY_IP
        email = ENPHASE_EMAIL
        password = ENPHASE_PASSWORD
    
    print(f"📍 IP del Envoy: {envoy_ip}")
    print(f"📧 Email: {email}")
    print("")
    
    # Crear instancia y autenticar
    envoy = EnphaseEnvoyV8Final(envoy_ip, email, password)
    formatter = EnvoyDataFormatter()
    
    # Obtener información del sistema
    info = envoy.get_info()
    formatter.print_system_info(info)
    
    # Autenticar con Enphase Cloud
    print("\n" + "=" * 60)
    
    # Forzar renovación si está configurado
    if FORCE_NEW_TOKEN and os.path.exists(TOKEN_FILE):
        print("🔄 Forzando renovación del token...")
        os.remove(TOKEN_FILE)
    
    if envoy.authenticate():
        print("=" * 60)
        
        # Obtener datos de producción
        production = envoy.get_production_json()
        meters = envoy.get_ivp_meters()
        
        # Mostrar estado actual
        formatter.print_current_status(production, meters)
        
        # Mostrar resumen de producción
        formatter.print_production_summary(production)
        
        # Mostrar medidores
        formatter.print_meters_summary(meters)
        
        # Obtener inversores
        print("\n🔍 Consultando inversores...")
        inverters = envoy.get_inverters()
        formatter.print_inverters_summary(inverters, show_all=False)
        
        print("\n" + "=" * 60)
        print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60 + "\n")
        
        print("✅ ¡TODO FUNCIONÓ CORRECTAMENTE!")
        print(f"\n💡 INFO: Token guardado en {TOKEN_FILE}")
        print("   El token será reutilizado en las próximas 23 horas")
        print("   Para forzar renovación, cambia FORCE_NEW_TOKEN = True\n")
        
    else:
        print("=" * 60)
        print("\n❌ NO SE PUDO AUTENTICAR")
        print("\n💡 VERIFICA:")
        print("   1. Email y contraseña de Enphase Enlighten correctos")
        print("   2. El Envoy está registrado en tu cuenta de Enlighten")
        print("   3. Tienes conexión a internet")
        print("   4. La IP del Envoy es correcta\n")
