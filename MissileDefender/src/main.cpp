#include <Arduino.h>
#include <Servo.h>

Servo servox;
Servo servoy;
Servo servo_gatilho;

const int PINO_SERVOX = 9;
const int PINO_SERVOY = 10;
const int PINO_GATILHO = 11;
const int BUZZER = 12;
const int PINO_BOTAO_LIGAR = 8; 
const int PINO_BOTAO = 7;
const int LED_LIGADO = 6;
const int LED_LIGANDO = 5;
const int LED_DESLIGADO = 4;
const int LED_ATIRANDO = 3;
const int LED_MIRANDO = 2;

const int ANGULO_REPOUSO  = 0;
const int ANGULO_ACIONADO = 90;
const int DURACAO_GATILHO = 600;
const int DURACAO_BRILHO_GATILHO = 1000;
const int ZONA_MORTA      = 2;
const int DEBOUNCE_MS     = 50;

int ligando = 0;

int ultimoAnguloX = 90;
int ultimoAnguloY = 90;

bool           gatilho_ativo   = false;
unsigned long  tempo_gatilho   = 0;
unsigned long tempo_brilho_gatilho = 0;

bool           botao_anterior  = HIGH;
unsigned long  tempo_debounce  = 0;

bool           botao_anterior_ligar  = HIGH;
unsigned long  tempo_debounce_ligar = 0;

bool ligar = false;  // Estado do sistema (ligado/desligado)

void setup() {
    Serial.begin(9600);

    servox.attach(PINO_SERVOX);
    servoy.attach(PINO_SERVOY);
    servo_gatilho.attach(PINO_GATILHO);

    pinMode(PINO_BOTAO, INPUT_PULLUP);  // botão entre pino 7 e GND
    pinMode(PINO_BOTAO_LIGAR, INPUT_PULLUP);  // botão entre pino 8 e GND
    pinMode(LED_LIGADO, OUTPUT);
    pinMode(LED_LIGANDO, OUTPUT);
    pinMode(LED_DESLIGADO, OUTPUT);
    pinMode(LED_ATIRANDO, OUTPUT);
    pinMode(LED_MIRANDO, OUTPUT);
    pinMode(BUZZER, OUTPUT);

    servox.write(90);
    servoy.write(90);
    servo_gatilho.write(ANGULO_REPOUSO);
    
    digitalWrite(LED_DESLIGADO, HIGH);
    digitalWrite(LED_LIGADO,    LOW);
    digitalWrite(LED_LIGANDO,   LOW);
    digitalWrite(LED_ATIRANDO,  LOW);
    digitalWrite(LED_MIRANDO,   LOW);
}

void loop() {
    // Botão de ligar/desligar (com debounce)
    bool botao_ligar_atual = digitalRead(PINO_BOTAO_LIGAR);

    bool botao_atual = digitalRead(PINO_BOTAO);

    if (botao_ligar_atual == LOW && botao_anterior_ligar == HIGH && (millis() - tempo_debounce_ligar > DEBOUNCE_MS))
    {   
        ligar = !ligar;  // Alterna o estado de ligar/desligar
        ligando = 0; // reseta o estado de inicialização
        Serial.println(ligar ? "Ligado" : "Desligado");
        if (ligar) {
            servox.write(90);
            servoy.write(90);
        }
        tempo_debounce_ligar = millis();
    }

    botao_anterior_ligar = botao_ligar_atual;

    if (!ligar) {
        botao_anterior = botao_atual;

        digitalWrite(LED_DESLIGADO, HIGH);
        digitalWrite(LED_LIGADO,    LOW);
        digitalWrite(LED_LIGANDO,   LOW);
        digitalWrite(LED_ATIRANDO,  LOW);
        digitalWrite(LED_MIRANDO,   LOW);
        noTone(BUZZER);
        return;
    }
    
    // Sistema ligando
    digitalWrite(LED_DESLIGADO, LOW);

    // LED de inicialização (servo voltando ao centro)
    int anguloAtualX = servox.read();
    int anguloAtualY = servoy.read();

    if (anguloAtualX != 90 && anguloAtualY != 90 && ligando == 0) {
        digitalWrite(LED_LIGANDO, HIGH);
        digitalWrite(LED_LIGADO,  LOW);
    } else {
        ligando = 1;
        digitalWrite(LED_LIGANDO, LOW);
        digitalWrite(LED_LIGADO,  HIGH);
    }

    // Botão de recarga (com debounce)
    
    if (botao_atual == LOW && botao_anterior == HIGH && (millis() - tempo_debounce > DEBOUNCE_MS))
    {
        Serial.println("RECARGA");   // Python recebe e libera o sistema
        tempo_debounce = millis();
    }
    botao_anterior = botao_atual;

    // Retorno automático do gatilho
    if (gatilho_ativo && (millis() - tempo_gatilho >= DURACAO_GATILHO)) {
        servo_gatilho.write(ANGULO_REPOUSO);
        gatilho_ativo = false;
    }

    // LED e buzzer de disparo
    if (gatilho_ativo || (millis() - tempo_brilho_gatilho < DURACAO_BRILHO_GATILHO)) {
        digitalWrite(LED_ATIRANDO, HIGH);
        tone(BUZZER, 1200);  // beep 1.2kHz enquanto atira
    } else {
        digitalWrite(LED_ATIRANDO, LOW);
        noTone(BUZZER);
    }

    // Leitura serial (Python → Arduino)
    if (Serial.available() > 0) {
        String entrada = Serial.readStringUntil('\n');

        // Formato: "X,Y,GATILHO\n"
        int virgula1 = entrada.indexOf(',');
        int virgula2 = entrada.indexOf(',', virgula1 + 1);
        int virgula3 = entrada.indexOf(',', virgula2 + 1);

        int novoAnguloX = entrada.substring(0, virgula1).toInt();
        int novoAnguloY = entrada.substring(virgula1 + 1, virgula2).toInt();
        int gatilho     = entrada.substring(virgula2 + 1, virgula3).toInt();
        int mirando     = entrada.substring(virgula3 + 1).toInt();

        novoAnguloX = constrain(novoAnguloX, 0, 180);
        novoAnguloY = constrain(novoAnguloY, 0, 180);

        // Brilho se tiver mirando
        digitalWrite(LED_MIRANDO, mirando ? HIGH : LOW);

        // Move os servos de mira
        if (abs(novoAnguloX - ultimoAnguloX) >= ZONA_MORTA || abs(novoAnguloY - ultimoAnguloY) >= ZONA_MORTA)
        {
            servox.write(novoAnguloX);
            servoy.write(novoAnguloY);
            ultimoAnguloX = novoAnguloX;
            ultimoAnguloY = novoAnguloY;
        }

        // Aciona o gatilho
        if (gatilho == 1 && !gatilho_ativo) {
            servo_gatilho.write(ANGULO_ACIONADO);
            gatilho_ativo = true;
            tempo_gatilho = millis();
            Serial.println("DISPARO");
        }
    }
}