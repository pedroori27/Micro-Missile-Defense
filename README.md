# Micro Missile Defense

Sistema de rastreamento automático de pessoas em tempo real, que usa visão computacional (YOLOv8) para detectar uma pessoa na imagem da câmera e movimenta dois servos motores (eixos X e Y) via Arduino, mantendo o alvo centralizado no campo de visão.

## Como funciona
A câmera captura vídeo em tempo real.
O modelo YOLOv8 detecta pessoas em cada frame.
O programa calcula o deslocamento do centro da pessoa detectada em relação ao centro da imagem.
Esse deslocamento é convertido em ângulos horizontal (X) e vertical (Y), considerando o campo de visão (FOV) da câmera.
Os ângulos calculados são enviados ao Arduino via porta serial.
O Arduino movimenta os servos motores (pan/tilt) para apontar na direção da pessoa detectada.
O vídeo é exibido com bounding box, centro da detecção, linha central da câmera e informações de ângulo/confiança sobrepostas.

## Requisitos

Hardware:
Arduino (qualquer modelo compatível com comunicação serial, ex: Uno, Nano, Mega)
2 servos motores (pan/tilt — eixo X e eixo Y)
Webcam ou câmera USB
Cabo USB para conexão do Arduino ao computador

Ligação dos servos:

Componente	Pino no Arduino
Servo X (pan)	9
Servo Y (tilt)	10

💡 Se os dois servos consumirem mais corrente do que o pino 5V do Arduino aguenta, use uma fonte externa de 5V para os servos (com o GND compartilhado com o Arduino).

Software:
Python 3.8+
Bibliotecas Python:
opencv-python
ultralytics (YOLOv8)
pyserial
PlatformIO (extensão do VS Code ou CLI) para compilar e gravar o firmware do Arduino
Biblioteca Servo (já inclusa no core do Arduino)

## Instale as dependências:

bash
   pip install opencv-python ultralytics pyserial

O modelo yolov8n.pt é baixado automaticamente pela biblioteca ultralytics na primeira execução. Caso prefira baixar manualmente, ele está disponível nos releases oficiais do Ultralytics — coloque o arquivo na pasta do projeto.
Grave o firmware no Arduino usando o PlatformIO:
bash
   cd firmware
   pio run --target upload

O código-fonte (src/main.cpp) está descrito na seção Firmware abaixo. Ele escuta a porta serial em 9600 baud, recebe comandos no formato "anguloX,anguloY\n" (ex.: "95,88\n") e move os servos X e Y de acordo.

## Configuração

Antes de executar, ajuste as constantes no início do script conforme o seu setup:

Variável	Descrição	Valor padrão
CONFIANCA_MINIMA	Confiança mínima para considerar uma detecção válida (0 a 1)	0.70
ANGULO_CENTRO_SERVO	Ângulo central dos servos (posição neutra)	90
FOV_HORIZONTAL	Campo de visão horizontal da câmera, em graus	90
Porta serial (dentro de iniciar_arduino)	Porta de conexão com o Arduino	"COM5"
ZONA_MORTA (no firmware, main.cpp)	Diferença mínima (em graus) para o servo se mover — evita jitter	2

## Uso

Execute o script principal:

bash
python main.py

(substitua main.py pelo nome real do seu arquivo, caso seja diferente)

O programa procura automaticamente uma câmera disponível, testando os índices de 0 a 9.
Uma janela exibirá o vídeo com a detecção em tempo real.
Pressione Q para encerrar o programa.
Firmware (Arduino / PlatformIO)

O Arduino roda um firmware em C++ (src/main.cpp, projeto PlatformIO) responsável por:

Ler os ângulos enviados pelo Python via serial ("anguloX,anguloY\n");
Limitar os valores entre 0° e 180° (constrain);
Aplicar uma zona morta de 2°: o servo só se move se a diferença em relação ao último ângulo for igual ou maior que isso — isso evita tremulação (jitter) por pequenas variações de detecção;
Mover os servos X (pino 9) e Y (pino 10);
Responder pela serial com o ângulo aplicado, útil para depuração.
cpp
#include <Arduino.h>
#include <Servo.h>

Servo servox;
Servo servoy;

const int PINO_SERVOX = 9;
const int PINO_SERVOY = 10;

int valorX = 0;
int valorY = 0;

// Último ângulo enviado ao servo
int ultimoAnguloX = 90;
int ultimoAnguloY = 90;

// Diferença mínima necessária para movimentar
const int ZONA_MORTA = 2;

void setup() {
    Serial.begin(9600);

    servox.attach(PINO_SERVOX);
    servoy.attach(PINO_SERVOY);

    // Começa no centro
    servox.write(90);
    servoy.write(90);
}

void loop() {
    if (Serial.available() > 0) {
        String entrada = Serial.readStringUntil('\n');  // lê até o '\n'

        int virgula = entrada.indexOf(',');              // acha a vírgula
        valorX = entrada.substring(0, virgula).toInt();
        valorY = entrada.substring(virgula + 1).toInt();

        // Recebe o ângulo enviado pelo Python
        int novoAnguloX = valorX;
        int novoAnguloY = valorY;

        // Garante que fique entre 0 e 180
        novoAnguloX = constrain(novoAnguloX, 0, 180);
        novoAnguloY = constrain(novoAnguloY, 0, 180);

        // Calcula a diferença em relação ao último ângulo
        int diferencaX = abs(novoAnguloX - ultimoAnguloX);
        int diferencaY = abs(novoAnguloY - ultimoAnguloY);

        // Só movimenta se a diferença for >= 2°
        if (diferencaX >= ZONA_MORTA || diferencaY >= ZONA_MORTA) {

            // Move o servo
            servox.write(novoAnguloX);
            servoy.write(novoAnguloY);

            // Guarda o novo ângulo
            ultimoAnguloX = novoAnguloX;
            ultimoAnguloY = novoAnguloY;

            // Informa o ângulo pelo Serial
            Serial.print("Servo X: ");
            Serial.println(novoAnguloX);
            Serial.print("Servo Y: ");
            Serial.println(novoAnguloY);
        }
    }
}
Estrutura do código
Python (main.py)
Função	Responsabilidade
iniciar_camera()	Detecta e configura a câmera disponível (resolução 1920x1080, 30 FPS, MJPG)
iniciar_arduino()	Abre a conexão serial com o Arduino
iniciar_modelo()	Carrega o modelo YOLOv8 (yolov8n.pt)
calcular_distancia_focal()	Calcula a distância focal com base na largura do frame e no FOV
calcular_angulo_x() / calcular_angulo_y()	Calculam o ângulo entre o centro da câmera e o centro da pessoa detectada
calcular_angulo_servo_x() / calcular_angulo_servo_y()	Convertem os ângulos calculados em ângulos de servo (0–180°)
enviar_servo()	Envia os ângulos calculados ao Arduino via serial
detectar_pessoa()	Executa o YOLO no frame e retorna a detecção de pessoa (classe 0) com confiança suficiente
desenhar_deteccao()	Desenha bounding box, centro da detecção, linha central da câmera e texto informativo
main()	Loop principal que integra captura, detecção, cálculo de ângulos e envio ao Arduino
Firmware (firmware/src/main.cpp)
Trecho	Responsabilidade
setup()	Inicializa a serial, anexa os servos aos pinos 9 e 10 e os centraliza em 90°
Leitura serial em loop()	Lê a linha recebida e separa os valores de X e Y pela vírgula
constrain(...)	Garante que os ângulos fiquem entre 0° e 180°
Zona morta	Só aciona os servos se a variação for ≥ ZONA_MORTA (2°), evitando jitter
servox.write() / servoy.write()	Move os servos para o novo ângulo
Serial.print(...)	Envia de volta o ângulo aplicado, para depuração no monitor serial
Estrutura de pastas sugerida

   Micro-Missile-Defense/
   ├── main.py                 # Script Python (câmera, YOLO, cálculo de ângulos)
   └── firmware/                # Projeto PlatformIO do Arduino
       ├── platformio.ini
       └── src/
           └── main.cpp          # Firmware que recebe os ângulos e move os servos

## Aviso

Este projeto tem finalidade educacional, voltado ao estudo de visão computacional, integração serial com Arduino e controle de servo motores (pan/tilt tracking). Não deve ser adaptado para uso com dispositivos que possam causar dano a pessoas ou animais.
