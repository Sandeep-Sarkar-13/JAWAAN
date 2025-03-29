import cv2
import numpy as np
from ultralytics import YOLO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Function to send an emergency alert
"""def send_alert():
    sender_email = "your_email@example.com"
    sender_password = "your_password"
    recipient_email = "base_camp_email@example.com"
    subject = "Emergency Alert: Unauthorized Person Detected"
    body = "An unauthorized person has been detected. Please take immediate action."

    # Set up the email message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    # Send the email
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
        print("Alert sent successfully.")
    except Exception as e:
        print(f"Failed to send alert: {e}")"""

# Thermal mapping
def rgb_to_thermal(image):
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    thermal_image = cv2.applyColorMap(gray_image, cv2.COLORMAP_JET)
    return thermal_image

# Magma mapping
def rgb_to_magma(image):
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    magma_image = cv2.applyColorMap(gray_image, cv2.COLORMAP_MAGMA)
    return magma_image

# Object detection
def detect_objects(frame, model):
    results = model(frame)
    detections = results[0].boxes.data.cpu().numpy()

    # Define the labels based on the given format
    labels_map = {
        0: "Shotguns",
        1: "assault rifle",
        2: "lmgs",
        3: "pistols",
        4: "smgs",
        5: "snipers",
        6: "throwables"
    }

    unauthorized_detected = False
    for detection in detections:
        x1, y1, x2, y2, confidence, class_id = detection
        label = labels_map.get(int(class_id), "Unauthorized")  # Default to "Unauthorized" if not in map

        # Draw bounding box and label
        color = (0, 255, 0) if label != "Unauthorized" else (0, 0, 255)
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
        cv2.putText(frame, f"{label} {confidence:.2f}", (int(x1), int(y1)-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Check for unauthorized weapon/person
        if label == "Unauthorized":
            unauthorized_detected = True

    # Send alert if unauthorized weapon/person is detected
    """if unauthorized_detected:
        send_alert()"""

    return frame


# Main execution
def main():
    # Load the fine-tuned YOLO model
    model = YOLO("final_weapons.pt")  # Replace with your model file path

    # Load video feed (0 for webcam or provide video file path)
    cap = cv2.VideoCapture('guns-from-different-countries.mp4')

    # Get screen resolution for full-screen display
    screen_width = 1920  # Set your screen width
    screen_height = 1080  # Set your screen height

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Thermal and magma mapping
        thermal_frame = rgb_to_thermal(frame)
        magma_frame = rgb_to_magma(frame)

        # Perform object detection
        detection_frame = detect_objects(frame.copy(), model)

        # Resize frames for 2x2 grid
        grid_width = screen_width // 2
        grid_height = screen_height // 2

        thermal_frame = cv2.resize(thermal_frame, (grid_width, grid_height))
        magma_frame = cv2.resize(magma_frame, (grid_width, grid_height))
        detection_frame = cv2.resize(detection_frame, (grid_width, grid_height))
        original_frame = cv2.resize(frame, (grid_width, grid_height))

        # Combine frames into a 2x2 grid
        top_row = np.hstack((original_frame, thermal_frame))
        bottom_row = np.hstack((detection_frame, magma_frame))
        combined_frame = np.vstack((top_row, bottom_row))

        # Display the combined frame in full-screen
        cv2.namedWindow("Border Monitoring", cv2.WINDOW_NORMAL)
        cv2.setWindowProperty("Border Monitoring", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.imshow("Border Monitoring", combined_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
