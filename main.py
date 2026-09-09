import cv2
import math
import serial
from ultralytics import YOLO
import serial.tools.list_ports
import time

# CONFIGURAÇÕES

CONFIANCA_MINIMA = 0.40

# Ângulo central do servo
ANGULO_CENTRO_SERVO = 90

# FOV horizontal que tem a câmera
FOV_HORIZONTAL = 90

# Classe alvo para detecção
CLASSE_ALVO = ["celular"]

estrategia_prioridade = "B"  # A, B ou C

# Classes disponíveis (YOLO COCO dataset)
CLASSES_DISPONIVEIS = {
    "pessoa":   0,
    "celular":  67,
    "livro":    73,
    "bola":     32,
    "garrafa":  39,
    "cadeira":  56,
    "laptop":   63,
    "mochila":  24,
    "copo":     41,
}

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
    try:
        arduino = serial.Serial(
            port="COM5",
            baudrate=9600,
            timeout=1
        )

        time.sleep(2)
        return arduino

    except Exception as e:
        print("Erro ao conectar ao Arduino:")
        print(e)
        return None
# YOLO

def iniciar_modelo():

    print("Carregando YOLO...")

    modelo = YOLO("yolo11s.pt")

    print("a carregado.")

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

def detectar_objeto(
    modelo,
    frame
):
    # Pega os IDs de todas as classes configuradas
    ids_alvo = {
        nome: CLASSES_DISPONIVEIS[nome]
        for nome in CLASSE_ALVO
        if nome in CLASSES_DISPONIVEIS
    }

    resultados = modelo(frame)
    deteccoes = []  # ← agora é uma lista, não um único objeto

    for resultado in resultados:
        for box in resultado.boxes:

            classe = int(box.cls[0])
            confianca = float(box.conf[0])

            # Ignora se não está na lista de alvos
            nome_classe = next(
                (nome for nome, id_ in ids_alvo.items() if id_ == classe),
                None
            )
            if nome_classe is None:
                continue

            if confianca < CONFIANCA_MINIMA:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            deteccoes.append({
                "classe": nome_classe,   # ← agora guarda o nome do objeto
                "x1": x1, "y1": y1,
                "x2": x2, "y2": y2,
                "centro_x": (x1 + x2) / 2,
                "centro_y": (y1 + y2) / 2,
                "confianca": confianca
            })

    return deteccoes
# DESENHA A DETECÇÃO

def desenhar_deteccoes(frame, deteccoes, distancia_focal):

    altura, largura = frame.shape[:2]

    # Linha central da câmera
    cv2.line(frame, (largura // 2, 0), (largura // 2, altura), (255, 0, 0), 1)

    for det in deteccoes:

        x1, y1, x2, y2 = det["x1"], det["y1"], det["x2"], det["y2"]
        centro_x, centro_y = det["centro_x"], det["centro_y"]

        angulo_x = calcular_angulo_x(centro_x, largura, distancia_focal)
        angulo_y = calcular_angulo_y(centro_y, altura, distancia_focal)

        # Cor diferente por classe
        CORES = {
            "pessoa":  (0, 255, 0),
            "celular": (0, 200, 255),
            "bola":    (255, 100, 0),
            "livro":   (180, 0, 255),
        }
        cor = CORES.get(det["classe"], (200, 200, 200))

        # Bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), cor, 2)

        # Centro do objeto
        cv2.circle(frame, (int(centro_x), int(centro_y)), 5, (0, 0, 255), -1)

        # Texto com classe + ângulos
        texto = (
            f"{det['classe']} | "
            f"X: {angulo_x:+.1f} | "
            f"Y: {angulo_y:+.1f} | "
            f"Conf: {det['confianca']:.2f}"
        )
        cv2.putText(
            frame, texto,
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2
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
            break

        altura, largura = frame.shape[:2]
        distancia_focal = calcular_distancia_focal(largura)

        deteccoes = detectar_objeto(modelo, frame)  # lista agora

        if deteccoes:
            # ESTRATÉGIA DE PRIORIDADE
            if estrategia_prioridade == "A":
                # Opção A: segue o primeiro da lista CLASSE_ALVO que aparecer
                ordem = {nome: i for i, nome in enumerate(CLASSE_ALVO)}
                alvo = min(deteccoes, key=lambda d: ordem.get(d["classe"], 99))
            elif estrategia_prioridade == "B":
                # Opção B: segue o objeto mais central na tela
                alvo = min(deteccoes, key=lambda d: abs(d["centro_x"] - largura / 2))
            elif estrategia_prioridade == "C":
                # Opção C: segue o maior objeto (maior área)
                alvo = max(deteccoes, key=lambda d: (d["x2"]-d["x1"]) * (d["y2"]-d["y1"]))
            else:
                alvo = deteccoes[0]  # fallback 

            angulo_servo_x = calcular_angulo_servo_x(
                calcular_angulo_x(alvo["centro_x"], largura, distancia_focal)
            )
            angulo_servo_y = calcular_angulo_servo_y(
                calcular_angulo_y(alvo["centro_y"], altura, distancia_focal)
            )

            enviar_servo(arduino, angulo_servo_x, angulo_servo_y)
            desenhar_deteccoes(frame, deteccoes, distancia_focal)  # desenha todos

        cv2.imshow("Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        # Encerramento
    
    camera.release()

    arduino.close()

    cv2.destroyAllWindows()


# EXECUÇÃO

if __name__ == "__main__":

    main()