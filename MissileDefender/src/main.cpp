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

        int virgula = entrada.indexOf(',');             // acha a vírgula
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