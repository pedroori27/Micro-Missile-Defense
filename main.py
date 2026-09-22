import cv2
import math
import serial
from ultralytics import YOLO
import serial.tools.list_ports
import time
import subprocess
import platform

# CONFIGURAÇÕES

CONFIANCA_MINIMA = 0.40

# Ângulo central do servo
ANGULO_CENTRO_SERVO = 90

# Inverte o sentido caso o servo esteja montado ao contrário
INVERTER_X = True
INVERTER_Y = False

# FOV horizontal que tem a câmera
FOV_HORIZONTAL = 130

# FOV vertical que tem a câmera
FOV_VERTICAL = 62

# Índice da câmera (funciona tanto no Windows quanto no Linux)
INDICE_CAMERA = 3

# Caminho do dispositivo no Linux (usado só para ajustar a frequência da rede elétrica via v4l2-ctl)
DISPOSITIVO_CAMERA = "/dev/video2"

# Detecta o sistema operacional uma única vez
SISTEMA_OPERACIONAL = platform.system()  # "Windows", "Linux", "Darwin"

# Atirar com o servo
TOLERANCIA_MIRA = 60    # pixels do centro para considerar "na mira"
TEMPO_MIRA       = 2.5  # segundos até acionar o servo gatilho
COOLDOWN_GATILHO  = 10  # segundos de espera entre disparos
MAX_USOS_GATILHO  = 1   # usos antes de exigir recarga

# Suavização da posição do alvo entre frames (0 a 1)
# Menor = mais suave e mais "atrasado"; maior = mais responsivo e mais "trêmulo"
ALPHA_SUAVIZACAO = 0.3

# Velocidade/sensibilidade do rastreamento
# Menor = movimento mais suave; maior = movimento mais rápido
GANHO_RASTREIO_X = 0.12
GANHO_RASTREIO_Y = 0.05

# Máximo que cada servo pode corrigir por atualização
PASSO_MAXIMO_X = 3.0
PASSO_MAXIMO_Y = 1.0

# Limites para evitar que os servos cheguem ao fim mecânico
ANGULO_MINIMO = 15
ANGULO_MAXIMO = 165

# Classe alvo para detecção
CLASSE_ALVO = ["celular"]

ESTRATEGIA_PRIORIDADE = "B"  # A, B ou C

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
    print(f"Sistema operacional: {SISTEMA_OPERACIONAL}")

    # Ajusta a frequência da rede elétrica para 60 Hz (evita cintilação)
    # Isso só existe no Linux/V4L2, então no Windows essa etapa é pulada
    if SISTEMA_OPERACIONAL == "Linux":
        try:
            subprocess.run(
                [
                    "v4l2-ctl",
                    f"--device={DISPOSITIVO_CAMERA}",
                    "--set-ctrl=power_line_frequency=2"
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            )
        except FileNotFoundError:
            # Caso v4l2-ctl não esteja instalado, o programa continua normalmente
            pass

    print(f"Tentando câmera {INDICE_CAMERA}...")

    # Escolhe o backend certo para cada sistema operacional.
    # DSHOW é o mais confiável no Windows para aplicar resolução/FPS/MJPG;
    # V4L2 é o equivalente no Linux; CAP_ANY serve de fallback genérico.
    if SISTEMA_OPERACIONAL == "Windows":
        backend = cv2.CAP_DSHOW
    elif SISTEMA_OPERACIONAL == "Linux":
        backend = cv2.CAP_V4L2
    else:
        backend = cv2.CAP_ANY

    camera = cv2.VideoCapture(INDICE_CAMERA, backend)

    if not camera.isOpened():
        camera.release()
        print("Nenhuma câmera encontrada.")
        return None

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
        print("A câmera foi encontrada, mas não retornou imagem.")
        return None

    largura = int(
        camera.get(cv2.CAP_PROP_FRAME_WIDTH)
    )

    altura = int(
        camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
    )

    fps = camera.get(
        cv2.CAP_PROP_FPS
    )

    # Verifica o formato realmente aceito pela câmera
    fourcc = int(
        camera.get(cv2.CAP_PROP_FOURCC)
    )

    formato = "".join([
        chr(fourcc & 0xFF),
        chr((fourcc >> 8) & 0xFF),
        chr((fourcc >> 16) & 0xFF),
        chr((fourcc >> 24) & 0xFF)
    ])

    print("Câmera encontrada!")
    print(f"Índice: {INDICE_CAMERA}")
    if SISTEMA_OPERACIONAL == "Linux":
        print(f"Dispositivo: {DISPOSITIVO_CAMERA}")
    print(f"Resolução: {largura}x{altura}")
    print(f"FPS: {fps:.0f}")
    print(f"Formato: {formato}")

    # A câmera deve trabalhar em MJPG para alcançar 30 FPS em 1920x1080
    if formato.strip() != "MJPG":
        print("AVISO: a câmera não está usando MJPG.")

    if largura != 1920 or altura != 1080:
        print("AVISO: a câmera não aceitou 1920x1080.")

    if fps < 25:
        print("AVISO: a câmera está trabalhando abaixo de 30 FPS.")

    return camera


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

    modelo = YOLO("yolo11s.pt")

    print("a carregado.")

    return modelo

# CÁLCULO DA DISTÂNCIA FOCAL

def calcular_distancia_focal(tamanho, fov):

    distancia_focal = (
        (tamanho / 2)
        /
        math.tan(
            math.radians(
                fov / 2
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

def calcular_angulo_servo_x(angulo_x, angulo_atual):

    if INVERTER_X:
        angulo_x = -angulo_x

    # Usa o ângulo detectado como uma pequena correção da posição atual
    correcao = (
        angulo_x
        *
        GANHO_RASTREIO_X
    )

    # Limita a velocidade da correção
    correcao = max(
        -PASSO_MAXIMO_X,
        min(
            PASSO_MAXIMO_X,
            correcao
        )
    )

    angulo_servo_x = (
        angulo_atual
        +
        correcao
    )

    # Limita para não chegar ao fim mecânico do servo
    angulo_servo_x = max(
        ANGULO_MINIMO,
        min(
            ANGULO_MAXIMO,
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

def calcular_angulo_servo_y(angulo_y, angulo_atual):

    if INVERTER_Y:
        angulo_y = -angulo_y

    # Usa o ângulo detectado como uma pequena correção da posição atual
    correcao = (
        angulo_y
        *
        GANHO_RASTREIO_Y
    )

    # Limita a velocidade da correção
    correcao = max(
        -PASSO_MAXIMO_Y,
        min(
            PASSO_MAXIMO_Y,
            correcao
        )
    )

    angulo_servo_y = (
        angulo_atual
        +
        correcao
    )

    # Limita para não chegar ao fim mecânico do servo
    angulo_servo_y = max(
        ANGULO_MINIMO,
        min(
            ANGULO_MAXIMO,
            angulo_servo_y
        )
    )

    return angulo_servo_y

# ENVIO PARA O ARDUINO

def enviar_servo(arduino, angulo_servo_x, angulo_servo_y, acionar_gatilho=False, mirando=False):
    gatilho = 1 if acionar_gatilho else 0
    mira = 1 if mirando else 0
    comando = f"{angulo_servo_x:.0f},{angulo_servo_y:.0f},{gatilho},{mira}\n"
    arduino.write(comando.encode())

# LEITURA DO ARDUINO

def ler_arduino(arduino):
    try:
        if arduino.in_waiting > 0:
            linha = arduino.readline().decode().strip()
            return linha
    except (serial.SerialException, UnicodeDecodeError):
        pass
    return ""

# DETECÇÃO DA PESSOA/OBJETO

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

    resultados = modelo(frame, verbose=False)
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

# Desenha status de cooldown e recarga na tela

def desenhar_status(frame, usos, cooldown_restante, esperando_recarga, sistema_ligado):
    altura, largura = frame.shape[:2]

    # Fundo do painel de status
    cv2.rectangle(frame, (10, 10), (320, 100), (30, 30, 30), -1)
    cv2.rectangle(frame, (10, 10), (320, 100), (80, 80, 80), 1)

    # Indicador ligado/desligado
    cor_estado = (0, 220, 80) if sistema_ligado else (60, 60, 200)
    label_estado = "ON" if sistema_ligado else "OFF"
    cv2.circle(frame, (295, 28), 10, cor_estado, -1)
    cv2.putText(frame, label_estado, (280, 55),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, cor_estado, 1)


    # Ícones de uso (balas)
    for i in range(MAX_USOS_GATILHO):
        cor = (0, 200, 100) if i >= usos else (50, 50, 200)
        cx = 30 + i * 35
        cv2.circle(frame, (cx, 35), 12, cor, -1)
        cv2.putText(frame, str(i + 1), (cx - 6, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # Status de recarga
    if esperando_recarga:
        cv2.putText(frame, "! PRESSIONE O BOTAO PARA RECARREGAR !",
                    (15, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 80, 255), 2)

    # Barra de cooldown
    elif cooldown_restante > 0:
        progresso_cd = 1.0 - (cooldown_restante / COOLDOWN_GATILHO)
        barra_x      = 15
        barra_y      = 65
        barra_larg   = 290
        barra_alt    = 18
        preenchido   = int(barra_larg * progresso_cd)

        cv2.rectangle(frame, (barra_x, barra_y),
                      (barra_x + barra_larg, barra_y + barra_alt), (60, 60, 60), -1)
        cv2.rectangle(frame, (barra_x, barra_y),
                      (barra_x + preenchido, barra_y + barra_alt), (0, 180, 255), -1)
        cv2.putText(frame, f"Cooldown: {cooldown_restante:.1f}s",
                    (barra_x, barra_y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 180, 255), 1)
    else:
        cv2.putText(frame, "PRONTO", (15, 85),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 100), 2)

# DESENHA A DETECÇÃO

def desenhar_deteccoes(frame, deteccoes, distancia_focal_x, distancia_focal_y):

    altura, largura = frame.shape[:2]

    # Linha central da câmera
    cv2.line(frame, (largura // 2, 0), (largura // 2, altura), (255, 0, 0), 1)

    for det in deteccoes:

        x1, y1, x2, y2 = det["x1"], det["y1"], det["x2"], det["y2"]
        centro_x, centro_y = det["centro_x"], det["centro_y"]

        angulo_x = calcular_angulo_x(centro_x, largura, distancia_focal_x)
        angulo_y = calcular_angulo_y(centro_y, altura, distancia_focal_y)

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

# desenha mira mais barra de progresso
def desenhar_mira(frame, progresso, na_mira, gatilho_acionado):
    altura, largura = frame.shape[:2]
    cx, cy = largura // 2, altura // 2

    # Cruz central
    cor_mira = (0, 255, 0) if na_mira else (100, 100, 100)
    cv2.line(frame, (cx - 30, cy), (cx + 30, cy), cor_mira, 2)
    cv2.line(frame, (cx, cy - 30), (cx, cy + 30), cor_mira, 2)
    cv2.circle(frame, (cx, cy), 40, cor_mira, 1)

    # Barra de progresso (arco ao redor da mira)
    if na_mira and not gatilho_acionado:
        angulo_arco = int(360 * progresso)
        cv2.ellipse(frame, (cx, cy), (50, 50), -90, 0, angulo_arco, (0, 200, 255), 3)

        # Tempo restante
        restante = TEMPO_MIRA * (1 - progresso)
        cv2.putText(frame, f"{restante:.1f}s", (cx + 55, cy + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)

    # Aviso de FIRE
    if gatilho_acionado:
        cv2.putText(frame, "FIRE!", (cx - 35, cy - 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

# PROGRAMA PRINCIPAL
def main():
    # Variaveis
    sistema_ligado = False
    tempo_inicio_mira = None
    gatilho_acionado = False
    progresso = 0.0
    usos_gatilho = 0
    tempo_ultimo_gatilho = 0.0
    esperando_recarga = False
    centro_x_suave = None
    centro_y_suave = None
    angulo_servo_x = ANGULO_CENTRO_SERVO
    angulo_servo_y = ANGULO_CENTRO_SERVO

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
        distancia_focal_x = calcular_distancia_focal(largura, FOV_HORIZONTAL)
        distancia_focal_y = calcular_distancia_focal(altura, FOV_VERTICAL)

        # Dentro do while True, substitua o bloco if deteccoes:
        # 5. main() — substitua o bloco completo "if deteccoes:" dentro do while True:

        # Lê sinal do botão vindo do Arduino
        sinal = ler_arduino(arduino)
 
        if sinal == "Ligado":
            sistema_ligado = True
            angulo_servo_x = ANGULO_CENTRO_SERVO
            angulo_servo_y = ANGULO_CENTRO_SERVO
            print("Sistema LIGADO")
 
        elif sinal == "Desligado":
            sistema_ligado    = False
            # Reseta o estado ao desligar
            tempo_inicio_mira = None
            gatilho_acionado  = False
            progresso         = 0.0
            centro_x_suave    = None
            centro_y_suave    = None
            print("Sistema DESLIGADO")
 
        elif sinal == "RECARGA" and esperando_recarga:
            esperando_recarga    = False
            usos_gatilho         = 0
            tempo_ultimo_gatilho = 0.0
            print("Recarga confirmada! Sistema liberado.")

            
        # Calcula cooldown restante
        cooldown_restante = max(
            0.0,
            COOLDOWN_GATILHO - (time.time() - tempo_ultimo_gatilho)
        ) if tempo_ultimo_gatilho > 0 else 0.0

        cooldown_ativo = cooldown_restante > 0

        if sistema_ligado:
            # Apenas roda o sistema caso ligado
            deteccoes = detectar_objeto(modelo, frame)
            
            if deteccoes:
                if ESTRATEGIA_PRIORIDADE == "A":
                    ordem = {nome: i for i, nome in enumerate(CLASSE_ALVO)}
                    alvo = min(deteccoes, key=lambda d: ordem.get(d["classe"], 99))
                elif ESTRATEGIA_PRIORIDADE == "B":
                    alvo = min(deteccoes, key=lambda d: abs(d["centro_x"] - largura / 2))
                elif ESTRATEGIA_PRIORIDADE == "C":
                    alvo = max(deteccoes, key=lambda d: (d["x2"]-d["x1"]) * (d["y2"]-d["y1"]))
                else:
                    alvo = deteccoes[0]

                # SUAVIZAÇÃO DO ALVO 
                # A posição bruta da YOLO "treme" um pouco quadro a quadro;
                # isso suaviza antes de calcular o ângulo, pra não ficar
                # mandando micro-correções pro servo o tempo todo.
                if centro_x_suave is None:
                    centro_x_suave = alvo["centro_x"]
                    centro_y_suave = alvo["centro_y"]
                else:
                    centro_x_suave = (ALPHA_SUAVIZACAO * alvo["centro_x"]
                                       + (1 - ALPHA_SUAVIZACAO) * centro_x_suave)
                    centro_y_suave = (ALPHA_SUAVIZACAO * alvo["centro_y"]
                                       + (1 - ALPHA_SUAVIZACAO) * centro_y_suave)
 
                angulo_x = calcular_angulo_x(
                    centro_x_suave,
                    largura,
                    distancia_focal_x
                )

                angulo_y = calcular_angulo_y(
                    centro_y_suave,
                    altura,
                    distancia_focal_y
                )

                angulo_servo_x = calcular_angulo_servo_x(
                    angulo_x,
                    angulo_servo_x
                )

                angulo_servo_y = calcular_angulo_servo_y(
                    angulo_y,
                    angulo_servo_y
                )

                # LÓGICA DE MIRA
                na_mira = (abs(centro_x_suave - largura / 2) < TOLERANCIA_MIRA and abs(centro_y_suave - altura  / 2) < TOLERANCIA_MIRA)

                if na_mira:
                    if tempo_inicio_mira is None:
                        tempo_inicio_mira = time.time()
                    tempo_na_mira = time.time() - tempo_inicio_mira
                    progresso     = min(tempo_na_mira / TEMPO_MIRA, 1.0)
                else:
                    tempo_inicio_mira = None
                    gatilho_acionado  = False
                    progresso         = 0.0

                # ── DISPARO — checa cooldown e recarga ─────────────
                disparar_agora = False

                pode_disparar = (
                    na_mira and
                    progresso >= 1.0 and
                    not gatilho_acionado and
                    not cooldown_ativo and
                    not esperando_recarga
                )
                
                disparar_agora = False

                pode_disparar = (
                    na_mira and
                    progresso >= 1.0 and
                    not gatilho_acionado and
                    not cooldown_ativo and
                    not esperando_recarga
                )
                
                if pode_disparar:
                    gatilho_acionado = True
                    disparar_agora = True
                    usos_gatilho += 1
                    tempo_ultimo_gatilho = time.time()

                    if usos_gatilho >= MAX_USOS_GATILHO:
                        esperando_recarga = True

                    print(f"Disparo! ({usos_gatilho}/{MAX_USOS_GATILHO})")

                enviar_servo(arduino, angulo_servo_x, angulo_servo_y, disparar_agora, na_mira)
                # ───────────────────────────────────────────────────

                enviar_servo(arduino, angulo_servo_x, angulo_servo_y, gatilho_acionado, na_mira)
                desenhar_deteccoes(frame, deteccoes, distancia_focal_x, distancia_focal_y)
                desenhar_mira(frame, progresso, na_mira, gatilho_acionado)

            else:
                # Se perder o alvo, limpa o estado da mira e da suavização
                tempo_inicio_mira = None
                gatilho_acionado  = False
                progresso         = 0.0
                centro_x_suave    = None
                centro_y_suave    = None
                desenhar_mira(frame, 0, False, False)

        else:
            tempo_inicio_mira = None
            gatilho_acionado  = False
            progresso         = 0.0
            desenhar_mira(frame, 0, False, False)

        desenhar_status(frame, usos_gatilho, cooldown_restante, esperando_recarga, sistema_ligado)

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