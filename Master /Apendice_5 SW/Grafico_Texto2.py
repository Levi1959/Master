import paho.mqtt.client as mqtt
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import threading
import json

# Configurações MQTT
MQTT_SERVER = "localhost"
MQTT_PORT = 1883
MQTT_USER = "icts"
MQTT_PASSWORD = "icts"
TOPIC_TO_SUBSCRIBE = "temperatura/umidade"

# Listas para armazenar os dados recebidos para o gráfico
temperatures = []
humidities = []
timestamps = []

# Função chamada quando a conexão com o broker for estabelecida
def on_connect(client, userdata, flags, rc):
    print("Conectado ao broker MQTT com código de resultado:", rc)
    client.subscribe(TOPIC_TO_SUBSCRIBE)

# Função chamada quando uma mensagem for recebida
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        
        # Tenta carregar o JSON do payload
        data = json.loads(payload)
        
        # Extrai os valores do JSON
        temp = data['temperatura']
        hum = data['umidade']
        data_hora = data['data_hora']
        
        # Adiciona os dados às listas
        timestamps.append(data_hora.split(' ')[1])  # Usa apenas a hora
        temperatures.append(temp)
        humidities.append(hum)
        
        # Mantém apenas os últimos 20 pontos de dados para evitar sobrecarga
        if len(timestamps) > 20:
            timestamps.pop(0)
            temperatures.pop(0)
            humidities.pop(0)

        print(f"Dados JSON recebidos e armazenados: Temp={temp}, Humid={hum}")
        
    except json.JSONDecodeError:
        print("Erro: O payload não é um JSON válido. Ignorando mensagem.")
    except KeyError:
        print("Erro: As chaves 'temperatura' ou 'umidade' não foram encontradas no JSON.")
    except Exception as e:
        print(f"Erro inesperado: {e}")

# Configura o gráfico
fig, ax1 = plt.subplots(figsize=(10, 6))
ax2 = ax1.twinx()

# Configura as cores e labels
line1, = ax1.plot([], [], 'r-o', label='Temperatura (°C)')
line2, = ax2.plot([], [], 'b-o', label='Humidade (%)')

ax1.set_title("Dados de Temperatura e Humidade em Tempo Real", fontsize=16)
ax1.set_xlabel("Tempo", fontsize=12)
ax1.set_ylabel("Temperatura (°C)", color='r', fontsize=12)
ax2.set_ylabel("Humidade (%)", color='b', fontsize=12)

# Configura os limites iniciais dos eixos
ax1.set_ylim(20, 35)
ax2.set_ylim(40, 70)
ax1.grid(True)
fig.legend(loc="upper left", bbox_to_anchor=(0.1, 0.95))

# Função para animar o gráfico
def animate(i):
    if not timestamps:
        return line1, line2

    # Atualiza os dados das linhas
    line1.set_data(range(len(timestamps)), temperatures)
    line2.set_data(range(len(timestamps)), humidities)

    # Ajusta o eixo X para que os rótulos sejam visíveis
    ax1.set_xticks(range(len(timestamps)))
    ax1.set_xticklabels(timestamps, rotation=45, ha='right')
    ax1.set_xlim(0, len(timestamps) - 1)
    
    # Ajusta os limites Y dinamicamente
    if temperatures:
        min_temp = min(temperatures)
        max_temp = max(temperatures)
        ax1.set_ylim(min_temp - 2, max_temp + 2)
    if humidities:
        min_hum = min(humidities)
        max_hum = max(humidities)
        ax2.set_ylim(min_hum - 2, max_hum + 2)

    fig.tight_layout()
    return line1, line2

# Cria o cliente MQTT
client = mqtt.Client()
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_SERVER, MQTT_PORT, 60)

# Inicia o loop do MQTT em uma thread separada para não bloquear a interface
client.loop_start()

# Inicia a animação do gráfico
ani = FuncAnimation(fig, animate, interval=1000, blit=False)

# Inicia a interface gráfica do Matplotlib
plt.show()

# O programa continua aqui apenas quando a janela do gráfico é fechada
print("Fechando a conexão MQTT...")
client.loop_stop()
client.disconnect()