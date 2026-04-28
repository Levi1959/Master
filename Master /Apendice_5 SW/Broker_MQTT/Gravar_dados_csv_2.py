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
# Ouvindo o tópico que ambas as estações usam
TOPIC_URBANO = "Urbano_Temperatura_Local"

# Arquivos CSV
FILE_SD = "dados_estacao_SD.csv"
FILE_REMOTO = "dados_estacao_REMOTE.csv"

# Inicializa arquivos CSV com cabeçalho se não existirem
for f in [FILE_SD, FILE_REMOTO]:
    if not os.path.exists(f):
        with open(f, "w") as file:
            file.write("leitura,data_hora,temp,umid,id_placa\n")

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
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

def atualizar_grafico(i):
    try:
        ax1.clear()
        ax2.clear()
        
        # Estação SD (Azul)
        if os.path.exists(FILE_SD) and os.path.getsize(FILE_SD) > 50:
            df_sd = pd.read_csv(FILE_SD)
            ultimos_sd = df_sd.tail(15) # Mostra as últimas 15 leituras
            ax1.plot(ultimos_sd['temp'], label='SD: Temp', color='#1f77b4', marker='o')
            ax2.plot(ultimos_sd['umid'], label='SD: Umid', color='#17becf', marker='o', linestyle='--')
            
        # Estação Remota (Verde/Laranja)
        if os.path.exists(FILE_REMOTO) and os.path.getsize(FILE_REMOTO) > 50:
            df_re = pd.read_csv(FILE_REMOTO)
            ultimos_re = df_re.tail(15)
            ax1.plot(ultimos_re['temp'], label='Remoto: Temp', color='#2ca02c', marker='s')
            ax2.plot(ultimos_re['umid'], label='Remoto: Umid', color='#ff7f0e', marker='s', linestyle='--')

        # Estilização Temperatura
        ax1.set_title("Comparativo de Temperatura (°C)")
        ax1.set_ylabel("Celsius")
        ax1.legend(loc='upper left', fontsize='small')
        ax1.grid(True, alpha=0.3)

        # Estilização Umidade
        ax2.set_title("Comparativo de Umidade (%)")
        ax2.set_ylabel("Percentual")
        ax2.set_xlabel("Últimas Leituras")
        ax2.legend(loc='upper left', fontsize='small')
        ax2.grid(True, alpha=0.3)

    except Exception as e:
        print(f"Aguardando dados para o gráfico... {e}")

# --- Inicialização do Cliente MQTT ---
client = mqtt.Client()
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(MQTT_SERVER, MQTT_PORT, 60)
    client.loop_start() # Roda o MQTT em background
except:
    print("Não foi possível conectar ao Broker Local.")

# Animação da Janela
print("Abrindo interface gráfica...")
ani = FuncAnimation(fig, atualizar_grafico, interval=5000) # Atualiza a cada 5 segundos
plt.tight_layout()
plt.show()