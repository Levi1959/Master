import paho.mqtt.client as mqtt
import time

# Configurações MQTT
MQTT_SERVER = "localhost"  # O broker está no mesmo Pi, então o IP é localhost
MQTT_PORT = 1883
MQTT_USER = "icts"
MQTT_PASSWORD = "icts"
TOPIC_TO_SUBSCRIBE = "temperatura/umidade"
FILENAME = "dados_dht.txt"

# Função chamada quando a conexão com o broker for estabelecida
def on_connect(client, userdata, flags, rc):
    print("Conectado ao broker MQTT com código de resultado:", rc)
    # Assina o tópico assim que a conexão for estabelecida
    client.subscribe(TOPIC_TO_SUBSCRIBE)

# Função chamada quando uma mensagem for recebida
def on_message(client, userdata, msg):
    # Decodifica a mensagem de bytes para string
    payload = msg.payload.decode()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    
    # Formata a linha de dados com timestamp e o payload
    line = f"[{timestamp}] Tópico: {msg.topic}, Dados: {payload}\n"
    
    # Abre o arquivo em modo de anexação e escreve a nova linha
    with open(FILENAME, "a") as file:
        file.write(line)
    
    print(f"Dados salvos no arquivo: {payload}")

# Criar o cliente MQTT
client = mqtt.Client()

# Definir as credenciais
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

# Atribuir as funções de callback
client.on_connect = on_connect
client.on_message = on_message

# Conectar ao broker
client.connect(MQTT_SERVER, MQTT_PORT, 60)

# Iniciar o loop de escuta. Este loop bloqueia o programa.
client.loop_forever()