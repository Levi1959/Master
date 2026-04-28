import network
import time
import machine
import binascii
import rp2
from umqtt.simple import MQTTClient
import ntptime
from machine import Pin, I2C
import ssd1306
import dht
import gc

# Define o país para libertar todos os canais de Wi-Fi de 2.4GHz
rp2.country('BR')

# ==================== Configuração de Periféricos ====================
def iniciar_oled():
    try:
        i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=400000)
        ds = ssd1306.SSD1306_I2C(128, 64, i2c)
        return ds
    except:
        return None

oled = iniciar_oled()

def tela_info(titulo, linha1="", linha2="", linha3=""):
    if oled:
        try:
            oled.fill(0)
            oled.text(titulo[:16], 0, 0)
            oled.text(linha1[:16], 0, 20)
            oled.text(linha2[:16], 0, 35)
            oled.text(linha3[:16], 0, 50)
            oled.show()
        except:
            pass

# ==================== DELAY DE SINCRONISMO (30s) ====================
print("A aguardar 30 segundos...")
for i in range(30, 0, -1):
    tela_info("INICIALIZANDO", f"Aguarde: {i}s", "A sincronizar...", "Rede Local")
    time.sleep(1)

# ==================== Configurações Wi-Fi e MQTT ====================
SSID = "Eliete_2G"
PASSWORD = "senha01957"
MQTT_SERVER_LOCAL = "192.168.15.14"
MQTT_SERVER_NUVEM = "163.176.182.91"
TOPIC_PUB_LOCAL = b"Urbano_Temperatura_Local"
TOPIC_PUB_NUVEM = b"Urbano_Temperatura"
FUSO_HORARIO_SEGUNDOS = -3 * 3600

sensor = dht.DHT22(Pin(2))
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
hostname_placa = "P_REM_" + binascii.hexlify(wlan.config('mac')).decode()[-6:]

def conectar_wifi():
    if not wlan.isconnected():
        print(f"A tentar ligar ao Wi-Fi: {SSID}")
        wlan.connect(SSID, PASSWORD)
        
        for tentativa in range(20, 0, -1):
            tela_info("WIFI", "A ligar...", SSID, f"Tempo: {tentativa}s")
            if wlan.isconnected():
                print("Wi-Fi Ligado! IP:", wlan.ifconfig()[0])
                return True
            time.sleep(1)
            
        status = wlan.status()
        print(f"Falha na ligação Wi-Fi. Código de Estado: {status}")
        tela_info("WIFI ERRO", "Falha de rede", f"Estado: {status}", "")
        
    return wlan.isconnected()

def publicar(msg):
    sucesso = False
    
    # 1. Tenta enviar para o Servidor Local
    try:
        print(f"-> A ligar ao Local ({MQTT_SERVER_LOCAL})...")
        c_local = MQTTClient(hostname_placa, MQTT_SERVER_LOCAL, user="icts", password="icts", keepalive=10)
        c_local.connect()
        c_local.publish(TOPIC_PUB_LOCAL, msg.encode())
        c_local.disconnect()
        print("   [OK] Enviado para o Local!")
        sucesso = True
    except Exception as e:
        print(f"   [ERRO] Falha no Local: {e}")

    # 2. Tenta enviar para o Servidor Nuvem
    try:
       print(f"-> A ligar à Nuvem ({MQTT_SERVER_NUVEM})...")
       c_nuvem = MQTTClient(hostname_placa, MQTT_SERVER_NUVEM, user="icts", password="icts", keepalive=10)
       c_nuvem.connect()
       c_nuvem.publish(TOPIC_PUB_NUVEM, msg.encode())
       c_nuvem.disconnect()
       print("   [OK] Enviado para a Nuvem!")
       sucesso = True
    except Exception as e:
       print(f"   [ERRO] Falha na Nuvem: {e}")

    gc.collect()
    return sucesso

# ==================== Loop Principal ====================
leitura_numero = 0

while True:
    try:
        if conectar_wifi():
            leitura_numero += 1
            
            # NTP
            if leitura_numero == 1 or leitura_numero % 50 == 0:
                try: 
                    ntptime.settime()
                except: pass

            sensor.measure()
            t, h = sensor.temperature(), sensor.humidity()
            horario = "{:02}:{:02}:{:02}".format(*time.localtime(time.time() + FUSO_HORARIO_SEGUNDOS)[3:6])
            
            payload = f"{leitura_numero},{horario},{t:.1f},{h:.1f},{hostname_placa}"
            
            print(f"\n--- A iniciar Leitura {leitura_numero} ---")
            sucesso = publicar(payload)
            print(f"Leitura {leitura_numero}: T={t} U={h} - Sucesso Geral: {sucesso}")
            
            # Mostra no ecrã OLED
            tela_info("ESTACAO REMOTA", f"T:{t:.1f}C U:{h:.1f}%", f"L:{leitura_numero} {horario}", "OK" if sucesso else "ERRO MQTT")
            
            # ESPERA DE 2 MINUTOS (120 segundos)
            segundos_espera = 120
            for s in range(segundos_espera, 0, -1):
                if s % 10 == 0: 
                    tela_info("A AGUARDAR", f"Prox: {s}s", f"Leitura: #{leitura_numero}", "Sistema Ativo")
                time.sleep(1)
                
        else:
            time.sleep(5)

    except Exception as e:
        print("Erro no loop principal:", e)
        time.sleep(5)