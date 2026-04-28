import network

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# Define um nome de host para a placa
network.hostname('Pico_2')
print("Nome do Host definido.")

# A outra placa pode ser chamada de 'pico_w_cozinha', por exemplo.