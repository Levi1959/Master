from machine import Pin, I2C
import ssd1306
import dht
import time

# ===== Configuração I2C do OLED =====
i2c = I2C(0, scl=Pin(1), sda=Pin(0))  # GP1=SCL, GP0=SDA
oled_width = 128
oled_height = 64
oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)

# ===== Configuração do DHT22 =====
sensor = dht.DHT22(Pin(2))  # GP2

# ===== Configuração do botão =====
botao = Pin(3, Pin.IN, Pin.PULL_DOWN)  # GP3

# ===== Função para mostrar dados =====
def mostrar_dados(temp, hum):
    # OLED
    oled.fill(0)
    oled.text("DHT22 Sensor", 0, 0)
    oled.text("Temp: {:.1f}C".format(temp), 0, 20)
    oled.text("Umid: {:.1f}%".format(hum), 0, 40)
    oled.show()
    # Thonny
    print("=== Leitura DHT22 ===")
    print("Temperatura: {:.1f} C".format(temp))
    print("Umidade: {:.1f} %".format(hum))
    print("---------------------")

# ===== Função para reiniciar loop com botão =====
def aguardar_botao():
    oled.fill(0)
    oled.text("Pressione botão", 0, 20)
    oled.text("p/ reiniciar", 0, 35)
    oled.show()
    print("Aguardando botão para reiniciar...")
    while not botao.value():
        time.sleep(0.1)

# ===== Loop principal =====
while True:
    try:
        sensor.measure()
        temp = sensor.temperature()
        hum = sensor.humidity()
        mostrar_dados(temp, hum)
    except OSError:
        oled.fill(0)
        oled.text("Erro sensor", 0, 20)
        oled.show()
        print("Erro no sensor!")

    # Aguarda 2 segundos e verifica botão
    for _ in range(20):
        if botao.value():
            aguardar_botao()
        time.sleep(0.1)
