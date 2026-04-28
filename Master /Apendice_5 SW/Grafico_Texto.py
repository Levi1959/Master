import paho.mqtt.client as mqtt
import time
import matplotlib.pyplot as plt
from collections import deque

# Configurações MQTT
MQTT_SERVER = "localhost"
MQTT_PORT = 1883
MQTT_USER = "icts"
MQTT_PASSWORD = "icts"
TOPIC_TO_SUBSCRIBE = "temperatura/umidade"
FILENAME = "dados_dht.txt"

# Estruturas para armazenar os dados do gráfico
# deque é eficiente para adicionar e remover dados de uma lista com tamanho fixo
max_data_points = 100
temperatures = deque(maxlen=max_data_points)
timestamps = deque(maxlen=max_data_points)

# Configurar o plot interativo do Matplotlib
plt.ion()
fig, ax = plt.subplots()
line, = ax.plot([], [], 'r-o', label='Temperatura (°C)')
ax.set_title("Dados de Temperatura em Tempo Real")
ax.set_xlabel("Tempo")
ax.set_ylabel("Temperatura (°C)")
ax.grid(True)
ax.legend()


# Função chamada quando uma mensagem for recebida
def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    
    # Adicionar os dados recebidos às listas
    try:
        data_parts = payload.split('/')
        if len(data_parts) == 2:
            temp = float(data_parts[0].split(': ')[1])
            temperatures.append(temp)
            timestamps.append(timestamp)

            # Salvar no arquivo
            line = f"[{timestamp}] Tópico: {msg.topic}, Dados: {payload}\n"
            with open(FILENAME, "a") as file:
                file.write(line)
            print(f"Dados salvos e prontos para plotar: {payload}")
    except (ValueError, IndexError) as e:
        print(f"Erro ao processar a mensagem: {e}")

# Função para atualizar o gráfico
def update_plot():
    ax.set_xlim(0, len(timestamps))
    ax.set_ylim(min(temperatures) - 2, max(temperatures) + 2)
    line.set_data(range(len(timestamps)), temperatures)
    
    # Atualizar os rótulos do eixo X
    ax.set_xticks(range(len(timestamps)))
    ax.set_xticklabels(timestamps, rotation=45, ha='right')
    
    fig.canvas.draw()
    fig.canvas.flush_events()

# Resto do código (mantém o mesmo)
def on_connect(client, userdata, flags, rc):
    print("Conectado ao broker MQTT com código de resultado:", rc)
    client.subscribe(TOPIC_TO_SUBSCRIBE)

client = mqtt.Client()
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_SERVER, MQTT_PORT, 60)

# Iniciar o loop em uma thread para não bloquear a interface
client.loop_start()

# Loop principal para a visualização
while True:
    try:
        if len(temperatures) > 0:
            update_plot()
        plt.pause(1)  # Pausa para permitir que o gráfico seja atualizado
    except Exception as e:
        print(f"Ocorreu um erro no loop de visualização: {e}")
        break