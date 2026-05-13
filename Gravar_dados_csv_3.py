import paho.mqtt.client as mqtt
import time
import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

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
            
            # Define o arquivo baseado no ID enviado pelo Pico
            filename = FILE_SD if "SD_CARD" in id_placa else FILE_REMOTO
            
            with open(filename, "a") as f:
                f.write(payload + "\n")
            
            print(f"Dados Gravados [{id_placa}]: {payload}")
            
    except Exception as e:
        print(f"Erro no processamento: {e}")

# --- Configuração da Interface Gráfica ---
plt.style.use('ggplot')

# 1 linha, 2 colunas (lado a lado)
fig, (ax_sd, ax_re) = plt.subplots(1, 2, figsize=(12, 5), sharex=True)

def atualizar_grafico(i):
    try:
        ax_sd.clear()
        ax_re.clear()
        
        # =========================
        # GRÁFICO 1 - ESTAÇÃO SD
        # =========================
        if os.path.exists(FILE_SD) and os.path.getsize(FILE_SD) > 50:
            df_sd = pd.read_csv(FILE_SD)
            ultimos_sd = df_sd.tail(15)

            ax_sd.plot(ultimos_sd['temp'], label='Temp (SD)', color='#1f77b4', marker='o')
            ax_sd.plot(ultimos_sd['umid'], label='Umid (SD)', color='#17becf', marker='o', linestyle='--')

        ax_sd.set_title("Estação SD")
        ax_sd.set_ylabel("Valores")
        ax_sd.legend(loc='upper left', fontsize='small')
        ax_sd.grid(True, alpha=0.3)

        # =========================
        # GRÁFICO 2 - ESTAÇÃO REMOTA
        # =========================
        if os.path.exists(FILE_REMOTO) and os.path.getsize(FILE_REMOTO) > 50:
            df_re = pd.read_csv(FILE_REMOTO)
            ultimos_re = df_re.tail(15)

            ax_re.plot(ultimos_re['temp'], label='Temp (Remoto)', color='#2ca02c', marker='s')
            ax_re.plot(ultimos_re['umid'], label='Umid (Remoto)', color='#ff7f0e', marker='s', linestyle='--')

        ax_re.set_title("Estação Remota")
        ax_re.set_ylabel("Valores")
        ax_re.set_xlabel("Últimas Leituras")
        ax_re.legend(loc='upper left', fontsize='small')
        ax_re.grid(True, alpha=0.3)

    except Exception as e:
        print(f"Aguardando dados para o gráfico... {e}")

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

# --- ANIMAÇÃO ---
print("Abrindo interface gráfica...")

ani = FuncAnimation(fig, atualizar_grafico, interval=5000)

plt.tight_layout()
plt.show()