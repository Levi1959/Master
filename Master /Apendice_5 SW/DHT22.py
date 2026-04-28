import machine
import dht
import time

# Configura o pino GPIO onde o pino de dados do DHT22 está conectado
dht_pin = machine.Pin(2) # Este pin2 é o GP2 

# Inicializa o sensor DHT22
dht_sensor = dht.DHT22(dht_pin)

# Loop principal para ler os dados e imprimir no shell do Thonny
while True:
    try:
        # Lê a temperatura e a umidade do sensor
        dht_sensor.measure()
        temperatura = dht_sensor.temperature()
        umidade = dht_sensor.humidity()

        # Imprime os valores no shell do Thonny
        print(f"Temperatura: {temperatura}°C")
        print(f"Umidade: {umidade}%")

    except OSError as e:
        print("Erro ao ler dados do sensor:", e)

    # Espera 2 segundos antes da próxima leitura
    time.sleep(2)