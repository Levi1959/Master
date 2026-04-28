import machine
from machine import Pin, I2C
import ssd1306
import time

# Configuração I2C do OLED
i2c = I2C(0, scl=Pin(1), sda=Pin(0))
oled_width = 128
oled_height = 64
oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)

# Exibe uma mensagem de teste
oled.fill(0)
oled.text("OLED OK!", 0, 0)
oled.show()

print("OLED inicializado com sucesso!")

# Espera 5 segundos para a próxima tentativa
time.sleep(5)
