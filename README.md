# Micro Missile Defense 

Sistema de rastreamento automático de classes disponíveis(Como pessoas ou objetos, por isso estara escrito no read me "detectar uma pessoa ou objeto", alem disso esta programado como classe padrão o celular) em tempo real, que usa visão computacional (YOLO11) para detectar uma pessoa ou objeto na imagem da câmera e movimenta dois servos motores (eixos X e Y) via Arduino, mantendo o alvo centralizado no campo de visão.

## Como funciona

1. A câmera captura vídeo em tempo real.
2. O modelo **YOLO11** detecta pessoas ou objetos em cada frame.
3. O programa calcula o deslocamento do centro da pessoa ou objeto detectada em relação ao centro da imagem.
4. Esse deslocamento é convertido em ângulos horizontal (X) e vertical (Y), considerando o campo de visão (FOV) da câmera.
5. Os ângulos calculados são enviados ao Arduino via porta serial.
6. O Arduino movimenta os servos motores (pan/tilt) para apontar na direção da pessoa ou objeto detectada.
7. O vídeo é exibido com bounding box, centro da detecção, linha central da câmera e informações de ângulo/confiança sobrepostas.

## Requisitos

### Hardware
- Arduino Uno (placa utilizada e configurada no projeto)
- 3 servos motores (pan/tilt — eixo X e eixo Y e motor gatilho)
- Webcam ou câmera USB
- Cabo USB para conexão do Arduino ao computador

**Ligação dos servos:**

| Componente | Pino no Arduino |
|---|---|
| Servo X (horizontal) | 9 |
| Servo Y (vertical) | 10 |
| Servo Gatilho (gatilho) | 11 |

### Software
- Python 3.8+
- Bibliotecas Python:
  - `opencv-python`
  - `ultralytics` (YOLO11)
  - `pyserial`
- [PlatformIO](https://platformio.org/) (extensão do VS Code ou CLI) para compilar e gravar o firmware do Arduino
  - Biblioteca `Servo`, gerenciada como dependência pelo PlatformIO.

## Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/pedroori27/Micro-Missile-Defense.git
   cd Micro-Missile-Defense
   ```

2. Instale as dependências:
   ```bash
   pip install opencv-python ultralytics pyserial
   ```

3. O modelo `yolo11s.pt` é baixado automaticamente pela biblioteca `ultralytics` na primeira execução. Caso prefira baixar manualmente, ele está disponível nos releases oficiais do [Ultralytics](https://github.com/ultralytics/assets/releases) — coloque o arquivo na pasta do projeto.

4. Grave o firmware no Arduino usando o PlatformIO:
   ```bash
   cd MissileDefender
   pio run --target upload
   ```
   O código-fonte (`src/main.cpp`) está descrito na seção [Firmware](#firmware-arduino--platformio) abaixo. Ele escuta a porta serial em `9600` baud, recebe comandos no formato `"X,Y,GATILHO,MIRANDO"` (ex.: `"95,88,0,1\n"`) e move os servos X e Y de acordo.

## Configuração

Antes de executar, ajuste as constantes no início do script conforme o seu setup:

| Variável | Descrição | Valor padrão |
|---|---|---|
| `CONFIANCA_MINIMA` | Confiança mínima para considerar uma detecção válida (0 a 1) | `0.40` |
| `ANGULO_CENTRO_SERVO` | Ângulo central dos servos (posição neutra) | `90` |
| `FOV_HORIZONTAL` | Campo de visão horizontal da câmera, em graus | `130` |
| `FOV_VERTICAL` | Campo de visão vertical da câmera, em graus | `62` |
| Porta serial (dentro de `iniciar_arduino`) | Porta de conexão com o Arduino | `procura automaticamente` |
| `ZONA_MORTA` *(no firmware, `main.cpp`)* | Diferença mínima (em graus) para o servo se mover — evita jitter | `8` |

## Uso

Execute o script principal:
```bash
python main.py
```

- Uma janela exibirá o vídeo com a detecção em tempo real.
- Pressione **Q** para encerrar o programa.

## Firmware (Arduino / PlatformIO)

O Arduino roda um firmware em C++ (`src/main.cpp`, projeto PlatformIO) responsável por:

- Ler os ângulos enviados pelo Python via serial (`"anguloX,anguloY\n"`);
- Limitar os valores entre 0° e 180° (`constrain`);
- Aplicar uma **zona morta** de 2°: o servo só se move se a diferença em relação ao último ângulo for igual ou maior que isso — isso evita tremulação (jitter) por pequenas variações de detecção;
- Mover os servos X (pino 9), Y (pino 10) e gatilho (pino 11);
  
## Estrutura do código

### Python (`main.py`)

| Função | Responsabilidade |
|---|---|
| `iniciar_camera()` | Detecta e configura a câmera disponível (resolução 1920x1080, 30 FPS, MJPG) |
| `iniciar_arduino()` | Abre a conexão serial com o Arduino |
| `iniciar_modelo()` | Carrega o modelo YOLO11 (`yolo11s.pt`) |
| `calcular_distancia_focal()` | Calcula a distância focal com base na largura do frame e no FOV |
| `calcular_angulo_x()` / `calcular_angulo_y()` | Calculam o ângulo entre o centro da câmera e o centro da pessoa ou objeto detectada |
| `calcular_angulo_servo_x()` / `calcular_angulo_servo_y()` | Convertem os ângulos calculados em ângulos de servo (0–180°) |
| `enviar_servo()` | Envia os ângulos calculados ao Arduino via serial |
| `detectar_objeto()` | Executa o YOLO no frame e retorna a detecção de pessoa (classe 0) ou objeto (com outras classes) com confiança suficiente |
| `desenhar_deteccoes()` | Desenha bounding box, centro da detecção, linha central da câmera e texto informativo |
| `main()` | Loop principal que integra captura, detecção, cálculo de ângulos e envio ao Arduino |

### Firmware (`MissileDefender/src/main.cpp`)

| Trecho | Responsabilidade |
|---|---|
| `setup()` | Inicializa a serial, anexa os servos aos pinos 9 e 10 e os centraliza em 90° |
| Leitura serial em `loop()` | Lê a linha recebida e separa os valores de X e Y pela vírgula |
| `constrain(...)` | Garante que os ângulos fiquem entre 0° e 180° |
| Zona morta | Só aciona os servos se a variação for ≥ `ZONA_MORTA` (8°), evitando jitter |
| `servox.write()` / `servoy.write()` | Move os servos para o novo ângulo |
| `Serial.print(...)` | Envia mensagens de estado e eventos pela comunicação serial, permitindo que o Python identifique alterações no funcionamento do sistema. |

### Estrutura de pastas sugerida

```
Micro-Missile-Defense/
├── main.py                 # Script Python (câmera, YOLO, cálculo de ângulos)
└── MissileDefender/                # Projeto PlatformIO do Arduino
    ├── platformio.ini
    └── src/
        └── main.cpp          # Firmware que recebe os ângulos e move os servos
```

## Aviso

Este projeto tem finalidade educacional, voltado ao estudo de visão computacional, integração serial com Arduino e controle de servo motores (pan/tilt tracking). Não deve ser adaptado para uso com dispositivos que possam causar dano a pessoas ou animais.
