import cv2
import math
import serial
from ultralytics import YOLO

# Variaveis globais

CONFIANCA_MINIMA = 0.70
ANGULO_CENTRO_SERVO = 90

# Tem que ser o mesmo valor da câmera.
FOV_HORIZONTAL = 90 

# Inicialização da câmera, arduino e modelo YOLO

def iniciar_camera():

    camera = cv2.VideoCapture(
        "/dev/video1",
        cv2.CAP_V4L2
    )

    camera.set(
        cv2.CAP_PROP_FOURCC,
        cv2.VideoWriter_fourcc(*"MJPG")
    )

    camera.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        1920
    )

    camera.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        1080
    )

    camera.set(
        cv2.CAP_PROP_FPS,
        30
    )

    if not camera.isOpened():
        print("Erro: não foi possível abrir a DV20.")
        return None

    print("DV20 aberta com sucesso!")

    return camera


def iniciar_arduino():
    arduino = serial.Serial("/dev/ttyACM0", 9600)

    return arduino


def iniciar_modelo():
    return YOLO("yolov8n.pt")

# CÁLCULO DO ÂNGULO

def calcular_distancia_focal(largura):
    f = (largura / 2) / math.tan(
        math.radians(FOV_HORIZONTAL / 2)
    )

    return f


def calcular_angulo(centro_x, largura, distancia_focal):

    centro_camera = largura / 2

    angulo = math.degrees(
        math.atan(
            (centro_x - centro_camera) / distancia_focal
        )
    )

    return angulo

def calcular_angulo_servo(angulo):

    angulo_servo = ANGULO_CENTRO_SERVO + angulo

    # Limita entre 0 e 180
    angulo_servo = max(
        0,
        min(180, angulo_servo)
    )

    return angulo_servo

# ARDUINO

def enviar_servo(arduino, angulo_servo):

    comando = f"{angulo_servo:.0f}\n"

    arduino.write(
        comando.encode()
    )

# YOLO, segue a pessoa

def detectar_pessoa(modelo, frame):

    resultados = modelo(frame)

    deteccao = None

    for resultado in resultados:

        for box in resultado.boxes:

            classe = int(box.cls[0])
            confianca = float(box.conf[0])

            # Classe 0 = pessoa
            if classe != 0:
                continue

            # Ignora detecções com baixa confiança
            if confianca < CONFIANCA_MINIMA:
                continue

            x1, y1, x2, y2 = map(
                int,
                box.xyxy[0]
            )

            centro_x = (x1 + x2) / 2
            centro_y = (y1 + y2) / 2

            deteccao = {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "centro_x": centro_x,
                "centro_y": centro_y,
                "confianca": confianca
            }

            break

    return deteccao

# Quadrado na tela do YOLO, dando a informação do ângulo, ângulo do servo e confiança da detecção.

def desenhar_deteccao(
    frame,
    deteccao,
    angulo,
    angulo_servo
):

    x1 = deteccao["x1"]
    y1 = deteccao["y1"]
    x2 = deteccao["x2"]
    y2 = deteccao["y2"]

    confianca = deteccao["confianca"]

    # Bounding box
    cv2.rectangle(
        frame,
        (x1, y1),
        (x2, y2),
        (0, 255, 0),
        2
    )

    # Texto
    texto = (
        f"Pessoa | "
        f"Angulo: {angulo:+.1f} | "
        f"Servo: {angulo_servo:.0f} | "
        f"Conf: {confianca:.2f}"
    )

    cv2.putText(
        frame,
        texto,
        (x1, y1 - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )

# Programa principal

def main():

    camera = iniciar_camera()

    arduino = iniciar_arduino()

    modelo = iniciar_modelo()

    while True:

        ret, frame = camera.read()

        if not ret:
            print("Não foi possível obter imagem da câmera.")
            break

        altura, largura = frame.shape[:2]

        distancia_focal = calcular_distancia_focal(
            largura
        )

        deteccao = detectar_pessoa(
            modelo,
            frame
        )

        if deteccao is not None:

            angulo = calcular_angulo(
                deteccao["centro_x"],
                largura,
                distancia_focal
            )

            angulo_servo = calcular_angulo_servo(
                angulo
            )

            enviar_servo(
                arduino,
                angulo_servo
            )

            desenhar_deteccao(
                frame,
                deteccao,
                angulo,
                angulo_servo
            )

        cv2.imshow(
            "Camera",
            frame
        )

        # Q para sair
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camera.release()
    arduino.close()
    cv2.destroyAllWindows()

if __name__ == "__main__": # Codigo so roda se for chamado por esse arquivo, nunca se for importado por outro arquivo
    main()