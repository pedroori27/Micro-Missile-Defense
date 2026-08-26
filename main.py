import cv2
import math
import serial
from ultralytics import YOLO
import serial.tools.list_ports
import time

# CONFIGURAÇÕES

CONFIANCA_MINIMA = 0.70

# Ângulo central do servo
ANGULO_CENTRO_SERVO = 90

# FOV horizontal que tem a câmera
FOV_HORIZONTAL = 90

# CÂMERA

def iniciar_camera():

    print("Procurando câmera...")

    # Tenta algumas portas de câmera
    for indice in range(10):

        print(f"Tentando câmera {indice}...")

        # Windows / Linux
        camera = cv2.VideoCapture(indice)

        if not camera.isOpened():
            camera.release()
            continue

        # Tenta configurar a câmera
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

        # Testa se realmente consegue receber uma imagem
        ret, frame = camera.read()

        if not ret:
            camera.release()
            continue

        largura = int(
            camera.get(cv2.CAP_PROP_FRAME_WIDTH)
        )

        altura = int(
            camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
        )

        fps = camera.get(
            cv2.CAP_PROP_FPS
        )

        print("Câmera encontrada!")
        print(f"Índice: {indice}")
        print(f"Resolução: {largura}x{altura}")
        print(f"FPS: {fps:.0f}")

        return camera

    print("Nenhuma câmera encontrada.")

    return None

# ARDUINO

def iniciar_arduino():

    print("Procurando Arduino...")

    portas = serial.tools.list_ports.comports()

    if not portas:

        print("Nenhuma porta serial encontrada.")

        return None

    for porta in portas:

        descricao = (
            porta.description or ""
        ).lower()

        fabricante = (
            porta.manufacturer or ""
        ).lower()

        print(
            f"{porta.device} - "
            f"{porta.description}"
        )

        # Procura por nomes comuns de Arduino
        if (
            "arduino" in descricao
            or "arduino" in fabricante
            or "usb serial" in descricao
            or "ch340" in descricao
            or "ch340" in fabricante
            or "wch" in descricao
            or "wch" in fabricante
        ):

            try:

                arduino = serial.Serial(
                    porta.device,
                    9600,
                    timeout=1
                )

                # O Arduino normalmente reinicia
                # quando a porta serial é aberta
                time.sleep(2)

                print(
                    f"Arduino encontrado em: "
                    f"{porta.device}"
                )

                return arduino

            except serial.SerialException as erro:

                print(
                    f"Erro ao abrir {porta.device}: "
                    f"{erro}"
                )

    print("Arduino não encontrado.")

    return None
# YOLO

def iniciar_modelo():

    print("Carregando YOLO...")

    modelo = YOLO("yolov8n.pt")

    print("YOLO carregado.")

    return modelo

# CÁLCULO DA DISTÂNCIA FOCAL

def calcular_distancia_focal(largura):

    distancia_focal = (
        (largura / 2)
        /
        math.tan(
            math.radians(
                FOV_HORIZONTAL / 2
            )
        )
    )

    return distancia_focal

# CÁLCULO DO ÂNGULO

def calcular_angulo_x(
    centro_x,
    largura,
    distancia_focal
):

    centro_camera = largura / 2

    angulo_x = math.degrees(
        math.atan(
            (
                centro_x
                -
                centro_camera
            )
            /
            distancia_focal
        )
    )

    return angulo_x

# ÂNGULO DO SERVO

def calcular_angulo_servo_x(angulo_x):

    angulo_servo_x = (
        ANGULO_CENTRO_SERVO
        +
        angulo_x
    )

    # Limita entre 0 e 180
    angulo_servo_x = max(
        0,
        min(
            180,
            angulo_servo_x
        )
    )

    return angulo_servo_x

def calcular_angulo_y(
    centro_y,
    altura,
    distancia_focal
):

    centro_camera = altura / 2

    angulo_y = math.degrees(
        math.atan(
            (
                centro_y
                -
                centro_camera
            )
            /
            distancia_focal
        )
    )

    return angulo_y

# ÂNGULO DO SERVO

def calcular_angulo_servo_y(angulo_y):

    angulo_servo_y = (
        ANGULO_CENTRO_SERVO
        +
        angulo_y
    )

    # Limita entre 0 e 180
    angulo_servo_y = max(
        0,
        min(
            180,
            angulo_servo_y
        )
    )

    return angulo_servo_y

# ENVIO PARA O ARDUINO

def enviar_servo(
    arduino,
    angulo_servo_x,
    angulo_servo_y
):

    comando = (
        f"{angulo_servo_x:.0f},{angulo_servo_y:.0f}\n"
    )

    arduino.write(
        comando.encode()
    )

# DETECÇÃO DA PESSOA

def detectar_pessoa(
    modelo,
    frame
):

    resultados = modelo(frame)

    deteccao = None

    for resultado in resultados:

        for box in resultado.boxes:

            classe = int(
                box.cls[0]
            )

            confianca = float(
                box.conf[0]
            )

            # Classe 0 = pessoa
            if classe != 0:
                continue

            # Ignora baixa confiança
            if confianca < CONFIANCA_MINIMA:
                continue

            x1, y1, x2, y2 = map(
                int,
                box.xyxy[0]
            )

            centro_x = (
                x1 + x2
            ) / 2

            centro_y = (
                y1 + y2
            ) / 2

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

# DESENHA A DETECÇÃO

def desenhar_deteccao(
    frame,
    deteccao,
    angulo_x,
    angulo_servo_x,
    angulo_y,
    angulo_servo_y
):

    x1 = deteccao["x1"]
    y1 = deteccao["y1"]

    x2 = deteccao["x2"]
    y2 = deteccao["y2"]

    centro_x = deteccao["centro_x"]
    centro_y = deteccao["centro_y"]

    confianca = deteccao["confianca"]

    # Bounding box
    cv2.rectangle(
        frame,
        (x1, y1),
        (x2, y2),
        (0, 255, 0),
        2
    )

    # Centro da pessoa
    cv2.circle(
        frame,
        (
            int(centro_x),
            int(centro_y)
        ),
        5,
        (0, 0, 255),
        -1
    )

    # Centro da câmera
    altura, largura = frame.shape[:2]

    centro_camera = int(
        largura / 2
    )

    cv2.line(
        frame,
        (centro_camera, 0),
        (centro_camera, altura),
        (255, 0, 0),
        2
    )

    # Texto
    texto = (
        f"Pessoa | "
        f"Angulo X: {angulo_x:+.1f} | "
        f"Servo X: {angulo_servo_x:.0f} | "
        f"Angulo Y: {angulo_y:+.1f} | "
        f"Servo Y: {angulo_servo_y:.0f} | "
        f"Conf: {confianca:.2f}"
    )

    cv2.putText(
        frame,
        texto,
        (x1, max(y1 - 10, 30)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )

# PROGRAMA PRINCIPAL

def main():
    # Inicialização

    camera = iniciar_camera()

    if camera is None:

        print(
            "Não foi possível iniciar a câmera."
        )

        return

    arduino = iniciar_arduino()

    if arduino is None:

        print(
            "Não foi possível conectar ao Arduino."
        )

        camera.release()

        return

    modelo = iniciar_modelo()

    # Loop principal

    while True:

        ret, frame = camera.read()

        if not ret:

            print(
                "Não foi possível obter "
                "imagem da câmera."
            )

            break

        # Dimensões reais do frame

        altura, largura = (
            frame.shape[:2]
        )

        # Distância focal

        distancia_focal = (
            calcular_distancia_focal(
                largura
            )
        )

        # YOLO

        deteccao = detectar_pessoa(
            modelo,
            frame
        )

        # Se encontrou uma pessoa

        if deteccao is not None:

            # Calcula ângulo da pessoa
            angulo_x = calcular_angulo_x(
                deteccao["centro_x"],
                largura,
                distancia_focal
            )

            # Converte para ângulo do servo
            angulo_servo_x = (
                calcular_angulo_servo_x(
                    angulo_x
                )
            )

            angulo_y = calcular_angulo_y(
                deteccao["centro_y"],
                altura,
                distancia_focal
            )

            angulo_servo_y = (
                calcular_angulo_servo_y(
                    angulo_y
                )
            )


            # Envia para Arduino
            enviar_servo(
                arduino,
                angulo_servo_x,
                angulo_servo_y
            )


            # Desenha informações
            desenhar_deteccao(
                frame,
                deteccao,
                angulo_x,
                angulo_servo_x,
                angulo_y,
                angulo_servo_y
            )


        # Mostra câmera

        cv2.imshow(
            "Camera",
            frame
        )


        # Q para sair
        if (
            cv2.waitKey(1)
            &
            0xFF
            ==
            ord("q")
        ):

            break

    # Encerramento
   
    camera.release()

    arduino.close()

    cv2.destroyAllWindows()


# EXECUÇÃO

if __name__ == "__main__":

    main()