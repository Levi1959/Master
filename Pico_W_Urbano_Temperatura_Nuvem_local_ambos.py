import time
import machine
import ntptime
import binascii
import os

# Módulos essenciais
from machine import Pin, I2C, SPI 
import network      # Módulo Wi-Fi (agora importado corretamente)
import ssd1306
import dht
import sdcard       # Driver do SD Card

# ==================== Configuração de Periféricos ====================

# Configuração I2C do OLED (Pinos 0 e 1)
try:
    i2c = I2C(0, scl=Pin(1), sda=Pin(0))
    oled_width = 128
    oled_height = 64
    oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)
except Exception as e:
    print(f"Erro ao inicializar o OLED: {e}. O programa continuará sem o display.")
    oled = None

# Configuração do DHT22 (Pino 2)
sensor = dht.DHT22(Pin(2))

# Configuração do botão (Pino 3)
botao = Pin(3, Pin.IN, Pin.PULL_DOWN)

# ==================== Configuração do SD Card (SPI 0) ====================
# PINAGEM: MISO=GP16, SCK=GP18, MOSI=GP19, CS=GP17
SD_SCK = 18
SD_MISO = 16
SD_MOSI = 19
SD_CS = 17

LOG_FILE = "log_temperatura.csv"
SD_MOUNT_POINT = "/sd"
sd = None # Variável global para a instância do SD Card

# ==================== Variáveis e Constantes Globais ====================
SSID = "Eliete_2G" 
PASSWORD = "senha01957"

# Fuso horário de Brasília (UTC-3) em segundos
FUSO_HORARIO_SEGUNDOS = -3 * 3600

# ==================== Funções Auxiliares ====================

def show_oled(text, line=0):
    """Função auxiliar para mostrar texto no OLED."""
    if oled:
        if line == 0:
            oled.fill(0) 
        elif line > 0:
            oled.rect(0, line, 128, 12, 0, True) # Limpa a linha
            
        oled.text(text, 0, line)
        oled.show()

def conecta_wifi():
    """Tenta conectar ao Wi-Fi em um período curto para NTP."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    mac_bytes = wlan.config('mac')
    mac_hex = binascii.hexlify(mac_bytes).decode()
    hostname_placa = "Pico W_" + mac_hex[-6:]
    wlan.config(hostname=hostname_placa)
    
    wlan.connect(SSID, PASSWORD)
    show_oled("Conectando Wi-Fi", 0)
    
    for _ in range(15): # 15 segundos para conectar
        time.sleep(1)
        if wlan.isconnected():
            print("Conectado ao Wi-Fi:", wlan.ifconfig())
            return wlan, hostname_placa
    
    print("Falha na conexão Wi-Fi. Continuando sem sincronização de hora.")
    return None, hostname_placa

def sincroniza_ntp():
    """Sincroniza a hora via NTP."""
    try:
        ntptime.host = "a.ntp.br"
        ntptime.settime()
        print("Data e hora sincronizadas via NTP.")
        return True
    except Exception as e:
        print("Erro ao sincronizar NTP:", e)
        return False

def obter_horario_utc3():
    """Retorna o horário atual ajustado para o fuso UTC-3."""
    utc_time_seconds = time.time()
    local_time_tuple = time.localtime(utc_time_seconds + FUSO_HORARIO_SEGUNDOS)
    return "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(*local_time_tuple[:6])

def inicializa_sd_card():
    """Inicializa e monta o cartão SD com baudrate reduzido para estabilidade."""
    global sd
    try:
        # Redução do Baudrate para 2MHz para estabilidade
        spi = SPI(0, baudrate=2000000, polarity=0, phase=0, 
                  miso=Pin(SD_MISO), sck=Pin(SD_SCK), mosi=Pin(SD_MOSI))
        
        cs = Pin(SD_CS, Pin.OUT)
        sd = sdcard.SDCard(spi, cs)
        os.mount(sd, SD_MOUNT_POINT)
        print(f"Cartão SD montado com sucesso em {SD_MOUNT_POINT}")
        show_oled("SD Card OK", 10)
        
        # Cria o cabeçalho se o arquivo for novo
        log_path = f"{SD_MOUNT_POINT}/{LOG_FILE}"
        if LOG_FILE not in os.listdir(SD_MOUNT_POINT):
             with open(log_path, "a") as f:
                header = "Leitura,Horario,Temperatura(C),Umidade(%),Dispositivo\n"
                f.write(header)
                print("Cabeçalho do arquivo de log criado.")
        return sd
        
    except Exception as e:
        print(f"Falha ao inicializar/montar o SD Card: {e}")
        show_oled("Erro SD Card!", 10)
        return None

def log_data_sd(sd_instancia, leitura_num, horario, temp, hum, hostname):
    """Grava os dados no arquivo CSV do SD Card."""
    if sd_instancia is None:
        return

    data_line = f"{leitura_num},{horario},{temp:.1f},{hum:.1f},{hostname}\n"
    log_path = f"{SD_MOUNT_POINT}/{LOG_FILE}"
    
    try:
        with open(log_path, "a") as f:
            f.write(data_line)
        print("Log gravado no SD Card.")
        
    except Exception as e:
        print(f"Erro ao escrever no SD Card: {e}. Desmontando...")
        
        # Tenta desmontar para evitar corrupção
        try:
            os.umount(SD_MOUNT_POINT)
            global sd
            sd = None
            print("SD Card desmontado após erro de escrita.")
        except:
            pass 

def mostrar_dados(leitura_num, temp, hum, horario, sd_ok):
    """Atualiza o display OLED com os dados mais recentes."""
    if oled:
        # Limpa as linhas de status e de dados
        oled.rect(0, 0, 128, 30, 0, True) 
        oled.text(f"L{leitura_num} {horario[11:16]}", 0, 0)
        oled.text("SD OK" if sd_ok else "SD OFFLINE", 100, 0) # Feedback do SD
        
        oled.rect(0, 30, 128, 24, 0, True)
        oled.text(f"T: {temp:.1f} C", 0, 40)
        oled.text(f"U: {hum:.1f} %", 0, 50)
        oled.show()

# ==================== Programa Principal ====================
leitura_numero = 0

try:
    show_oled("INICIANDO", 0)
    
    # 1. Tenta conectar Wi-Fi e sincronizar NTP
    wlan, hostname_placa = conecta_wifi()
    if wlan and sincroniza_ntp():
         show_oled("NTP OK", 20)
    else:
         show_oled("Sem Hora NTP", 20)
         hostname_placa = "Pico_Sem_Rede" # Garante um hostname padrão
         
    # 2. Inicializa o SD Card
    sd_instancia = inicializa_sd_card()
    
    while True:
        leitura_numero += 1
        
        # Leitura do sensor
        try:
            time.sleep(2)
            sensor.measure()
            temp = sensor.temperature()
            hum = sensor.humidity()
            horario = obter_horario_utc3()
            
            sd_ok = sd_instancia is not None # Checa se o SD está montado
            mostrar_dados(leitura_numero, temp, hum, horario, sd_ok)

            print(f"=== Leitura #{leitura_numero} ===")
            print(f"Horário: {horario}")
            print(f"Temperatura: {temp:.1f} C, Umidade: {hum:.1f} %")
            
            # 3. LOG NO SD CARD
            log_data_sd(sd_instancia, leitura_numero, horario, temp, hum, hostname_placa)
            
        except OSError as e:
            # Erro de leitura do DHT22
            show_oled("Erro sensor", 40)
            print("Erro de leitura do sensor (OSError):", e)
        
        # Pausa para o próximo ciclo de leitura
        print("Iniciando espera de 20 segundos...")
        for _ in range(20):
            #wdt.feed()
            time.sleep(1)
            
except Exception as e:
    # Captura qualquer erro crítico não tratado
    show_oled("ERRO CRITICO", 20)
    show_oled(str(e), 40)
    print("Erro critico:", e)
    
    # Tenta desmontar o SD card antes de reiniciar/encerrar
    if sd is not None:
        try:
            os.umount(SD_MOUNT_POINT)
            print("SD Card desmontado com sucesso no erro crítico.")
        except:
            pass
            
    # Reinicia a placa para tentar corrigir o problema
    machine.reset()