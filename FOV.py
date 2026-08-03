import cv2

for dispositivo in ["/dev/video1", "/dev/video2"]:

    print(f"Testando {dispositivo}...")

    camera = cv2.VideoCapture(
        dispositivo,
        cv2.CAP_V4L2
    )

    if camera.isOpened():
        print(f"{dispositivo} abriu corretamente!")

        ret, frame = camera.read()

        if ret:
            print("Frame recebido:", frame.shape)
        else:
            print("Abriu, mas não conseguiu receber frame.")

    else:
        print(f"{dispositivo} não abriu.")

    camera.release()