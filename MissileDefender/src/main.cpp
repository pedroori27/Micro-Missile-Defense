#include <Arduino.h>
#include <Servo.h>

Servo servox;
Servo servoy;
Servo servo_gatilho;

const int PINO_SERVOX   = 9;
const int PINO_SERVOY   = 10;
const int PINO_GATILHO  = 11;
const int PINO_BOTAO    = 7;   // ← botão de recarga (GND + pino 7)
const int PINO_BOTAO_LIGAR = 8; // ← botão de ligar/desligar (GND + pino 8)

const int ANGULO_REPOUSO  = 0;
const int ANGULO_ACIONADO = 90;
const int DURACAO_GATILHO = 600;
const int ZONA_MORTA      = 2;
const int DEBOUNCE_MS     = 50;

int ultimoAnguloX = 90;
int ultimoAnguloY = 90;

bool           gatilho_ativo   = false;
unsigned long  tempo_gatilho   = 0;

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

    servox.write(90);
    servoy.write(90);
    servo_gatilho.write(ANGULO_REPOUSO);
}

void loop() {
    // Botão de ligar/desligar (com debounce)
    bool botao_ligar_atual = digitalRead(PINO_BOTAO_LIGAR);

    bool botao_atual = digitalRead(PINO_BOTAO);

    if (botao_ligar_atual == LOW && botao_anterior_ligar == HIGH && (millis() - tempo_debounce_ligar > DEBOUNCE_MS))
    {   
        ligar = !ligar;  // Alterna o estado de ligar/desligar
        if (ligar) {
            Serial.println("Ligado");   // Python recebe e libera o sistema
        }
        else {
            Serial.println("Desligado"); // Python recebe e bloqueia o sistema
        }
        tempo_debounce_ligar = millis();
    }

    botao_anterior_ligar = botao_ligar_atual;

    if (!ligar) {
        // Se o sistema estiver desligado, não faz nada
        return;
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

    // Leitura serial (Python → Arduino)
    if (Serial.available() > 0) {
        String entrada = Serial.readStringUntil('\n');

        // Formato: "X,Y,GATILHO\n"
        int virgula1 = entrada.indexOf(',');
        int virgula2 = entrada.indexOf(',', virgula1 + 1);

        int novoAnguloX = entrada.substring(0, virgula1).toInt();
        int novoAnguloY = entrada.substring(virgula1 + 1, virgula2).toInt();
        int gatilho     = entrada.substring(virgula2 + 1).toInt();

        novoAnguloX = constrain(novoAnguloX, 0, 180);
        novoAnguloY = constrain(novoAnguloY, 0, 180);

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