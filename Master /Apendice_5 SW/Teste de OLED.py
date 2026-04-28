from machine import Pin, I2C
import time
import ssd1306

# Configura as dimensões do display OLED (128x64 ou 128x32)
OLED_WIDTH = 128
OLED_HEIGHT = 64

# Configura o barramento I2C para comunicação com o OLED
# SDA no pino GP4 e SCL no pino GP5
i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=400000)

# Inicializa o display OLED
oled = ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)

# --- INÍCIO DA MENSAGEM ATUALIZADA ---

# Mensagens a serem exibidas, cada uma em uma nova linha
linhas = [
    "OLED funcionando",
    "perfeitamente no",
    "Pi Pico 2 W!",
    "================",
    "Temperatura",
    "Umidade"
]

# Posição inicial no eixo Y (vertical)
y_posicao = 0

# Altura de cada linha de texto em pixels (padrão 8x8 pixels para caracteres)
altura_da_linha = 8

# Limpa o buffer do display
oled.fill(0)

# Usa um loop para escrever cada linha
for linha in linhas:
    oled.text(linha, 0, y_posicao)
    # Move para a próxima linha
    y_posicao += altura_da_linha
    
# --- FIM DA MENSAGEM ATUALIZADA ---

# Atualiza o display para mostrar o que foi desenhado no buffer
oled.show()

# O programa vai parar aqui
print("Mensagem longa e formatada enviada para o OLED.")