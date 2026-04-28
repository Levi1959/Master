import paho.mqtt.client as mqtt
import time
import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# --- Configurações de Limites (Altere conforme sua necessidade) ---
TEMP_MAX = 35.0
TEMP_MIN = 15.0
UMID_MAX = 80.0
UMID_MIN = 30.0

# --- Configurações MQTT ---
MQTT_SERVER = "localhost" 
MQTT_PORT = 1883
MQTT_USER = "icts"
MQTT_PASSWORD = "icts"

TOPIC_URBANO = "Urbano_Temperatura_Local"

# Arquivos CSV
FILE_SD = "dados_estacao_SD.csv"
FILE_REMOTO = "dados_estacao_REMOTE.csv"

# Inicializa arquivos CSV com cabeçalho se não existirem
for f in [FILE_SD, FILE_REMOTO]:
    if not os.path.exists(f):
        with open(f, "w") as file:
            file.write("leitura,data_hora,temp,umid,id_placa\n")

# --- MQTT ---
def on_connect(client, userdata, flags, rc):
    print(f"Conectado ao Broker Local (Código: {rc})")
    client.subscribe(TOPIC_URBANO)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        dados = payload.split(',')
        
        if len(dados) >= 5:
            id_placa = dados[4].strip()
            filename = FILE_SD if "SD_CARD" in id_placa else FILE_REMOTO
            
            with open(filename, "a") as f:
                f.write(payload + "\n")
            
            print(f"Dados Gravados [{id_placa}]: {payload}")
            
    except Exception as e:
        print(f"Erro no processamento: {e}")

# --- Configuração da Interface Gráfica ---
plt.style.use('ggplot')

# Criando uma grade 2x2
fig, ((ax_temp_sd, ax_temp_re), (ax_umid_sd, ax_umid_re)) = plt.subplots(2, 2, figsize=(14, 9))

def atualizar_grafico(i):
    try:
        # Limpa todos os eixos
        axes = [ax_temp_sd, ax_umid_sd, ax_temp_re, ax_umid_re]
        for ax in axes:
            ax.clear()
        
        # --- PROCESSAMENTO SD CARD ---
        if os.path.exists(FILE_SD) and os.path.getsize(FILE_SD) > 50:
            df_sd = pd.read_csv(FILE_SD)
            ultimos_sd = df_sd.tail(15)

            # Temp SD
            ax_temp_sd.plot(ultimos_sd['temp'], label='Temp SD (°C)', color='#e31a1c', marker='o')
            ax_temp_sd.axhline(y=TEMP_MAX, color='red', linestyle='--', alpha=0.6, label=f'Max ({TEMP_MAX})')
            ax_temp_sd.axhline(y=TEMP_MIN, color='blue', linestyle='--', alpha=0.6, label=f'Min ({TEMP_MIN})')
            ax_temp_sd.set_title("SD Card: Temperatura")

            # Umid SD
            ax_umid_sd.plot(ultimos_sd['umid'], label='Umid SD (%)', color='#1f78b4', marker='o')
            ax_umid_sd.axhline(y=UMID_MAX, color='darkblue', linestyle=':', alpha=0.6, label=f'Max ({UMID_MAX}%)')
            ax_umid_sd.axhline(y=UMID_MIN, color='orange', linestyle=':', alpha=0.6, label=f'Min ({UMID_MIN}%)')
            ax_umid_sd.set_title("SD Card: Umidade")

        # --- PROCESSAMENTO REMOTO ---
        if os.path.exists(FILE_REMOTO) and os.path.getsize(FILE_REMOTO) > 50:
            df_re = pd.read_csv(FILE_REMOTO)
            ultimos_re = df_re.tail(15)

            # Temp Remoto
            ax_temp_re.plot(ultimos_re['temp'], label='Temp Remoto (°C)', color='#ff7f00', marker='s')
            ax_temp_re.axhline(y=TEMP_MAX, color='red', linestyle='--', alpha=0.6)
            ax_temp_re.axhline(y=TEMP_MIN, color='blue', linestyle='--', alpha=0.6)
            ax_temp_re.set_title("Remoto: Temperatura")

            # Umid Remoto
            ax_umid_re.plot(ultimos_re['umid'], label='Umid Remoto (%)', color='#33a02c', marker='s')
            ax_umid_re.axhline(y=UMID_MAX, color='darkblue', linestyle=':', alpha=0.6)
            ax_umid_re.axhline(y=UMID_MIN, color='orange', linestyle=':', alpha=0.6)
            ax_umid_re.set_title("Remoto: Umidade")

        # Ajustes de legenda e grade
        for ax in axes:
            ax.legend(loc='best', fontsize='x-small')
            ax.grid(True, alpha=0.3)
            ax.set_xlabel("Leituras")

    except Exception as e:
        print(f"Aguardando dados... {e}")

# --- MQTT CLIENT ---
client = mqtt.Client()
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(MQTT_SERVER, MQTT_PORT, 60)
    client.loop_start()
except:
    print("Não foi possível conectar ao Broker Local.")

print("Interface com limites de segurança ativa...")
ani = FuncAnimation(fig, atualizar_grafico, interval=5000)
plt.tight_layout()
plt.show()