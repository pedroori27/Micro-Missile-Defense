import serial
import time

arduino = serial.Serial("/dev/ttyACM0", 9600)

time.sleep(10)  # Espera o Arduino reiniciar

while True:
    mensagem = arduino.readline().decode("utf-8").strip()
    print(mensagem)