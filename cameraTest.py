import cv2 # Biblioteca OpenCV para captura de vídeo e processamento de imagens
from ultralytics import YOLO # Biblioteca para detecção de objetos usando o modelo YOLOv8

# Carrega o modelo YOLOv8
model = YOLO("yolov8n.pt")

# Abre a webcam
camera = cv2.VideoCapture(0)

if not camera.isOpened(): # Verifica se a câmera foi aberta com sucesso
    print("Não foi possível abrir a câmera.")
    exit()

while True:
    ret, frame = camera.read() # Lê um frame da câmera

    if not ret:
        break

    # Detecta objetos
    results = model(frame)

    # Percorre as detecções
    for result in results:
        for box in result.boxes:

            # Número da classe
            classe = int(box.cls[0])

            # Nome da classe caso queira alguma especifica, por exemplo, "pessoa" ou "carro", você pode usar o nome da classe para filtrar as detecções
            name = model.names[classe]

            # Coordenadas
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # Confiança
            trust = float(box.conf[0])

            # Desenha o retângulo
            cv2.rectangle(frame, (x1, y1), (x2, y2),
                        (0, 255, 0), 2)

            # Escreve o nome da classe
            cv2.putText(
                frame,
                f"{name} x({(x2+x1)/2:.0f}) y({(y2+y1)/2:.0f}) {trust:.2f}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

    cv2.imshow("Detecção de Pessoas", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()