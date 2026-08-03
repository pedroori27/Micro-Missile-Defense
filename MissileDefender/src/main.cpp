#include <Arduino.h>
#include <Servo.h>

Servo servo;

const int PINO_SERVO = 9;

// Último ângulo enviado ao servo
int ultimoAngulo = 90;

// Diferença mínima necessária para movimentar
const int ZONA_MORTA = 2;

void setup() {
    Serial.begin(9600);

    servo.attach(PINO_SERVO);

    // Começa no centro
    servo.write(ultimoAngulo);
}

void loop() {

    if (Serial.available() > 0) {

        // Recebe o ângulo enviado pelo Python
        int novoAngulo = Serial.parseInt();

        // Garante que fique entre 0 e 180
        novoAngulo = constrain(novoAngulo, 0, 180);

        // Calcula a diferença em relação ao último ângulo
        int diferenca = abs(novoAngulo - ultimoAngulo);

        // Só movimenta se a diferença for >= 2°
        if (diferenca >= ZONA_MORTA) {

            // Move o servo
            servo.write(novoAngulo);

            // Guarda o novo ângulo
            ultimoAngulo = novoAngulo;

            // Informa o ângulo pelo Serial
            Serial.print("Servo: ");
            Serial.println(novoAngulo);
        }
    }
}