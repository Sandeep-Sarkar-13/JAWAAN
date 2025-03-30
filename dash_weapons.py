import dash
from dash import dcc, html, Output, Input, State
import dash_uploader as du
import cv2
import numpy as np
import os
from ultralytics import YOLO
import base64
import cohere
from gtts import gTTS
import pygame

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=["https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css"])
du.configure_upload(app, "./uploads")

# Initialize Cohere API
COHERE_API_KEY = "d28Y2HwnozUpGgMspNmhA83M3HZPJCAfqQoDqeuw"
co = cohere.Client(COHERE_API_KEY)

# Load YOLO model
MODEL_PATH = "final_weapons.pt"
model = YOLO(MODEL_PATH)

# Object detection
def detect_objects(image):
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # Convert to RGB
    results = model(image_rgb)  # Ensure model gets correct format
    detections = results[0].boxes.data.cpu().numpy() if len(results[0].boxes) > 0 else []
    
    labels_map = {
        0: "Shotguns",
        1: "Assault Rifle",
        2: "LMGs",
        3: "Pistols",
        4: "SMGs",
        5: "Snipers",
        6: "Throwables"
    }
    
    detected_labels = [f"{labels_map.get(int(det[5]), 'Unauthorized')} ({det[4]:.2f})" for det in detections]
    return detected_labels if detected_labels else ["No weapons detected"]

# Generate tactical defense guidance
def generate_defense_guidance(weapon):
    try:
        prompt = (f"I am a soldier spotting an enemy armed with a {weapon}. Provide a rapid, effective response including full sentences within 300 words: "
                  "tactical escape strategies, and survival techniques to neutralize or evade the threat.")        
        response = co.generate(
            model="command-xlarge-nightly",
            prompt=prompt,
            max_tokens=800,  # Increased max tokens for full response
            temperature=0.5,
            stop_sequences=["###"]
        )
        
        return response.generations[0].text.strip()
    
    except Exception as e:
        return f"Error generating guidance: {str(e)}"

# Translate guidance to Hindi (ensuring full text is processed)
def translate_to_hindi(text):
    try:
        # Split the text into smaller chunks if it's too long
        chunks = [text[i:i+500] for i in range(0, len(text), 500)]
        translated_chunks = []

        for chunk in chunks:
            prompt = f"Translate the following English text to Hindi in a complete, fluent, and structured manner:\n\n{chunk}"
            response = co.generate(
                model="command-xlarge-nightly",
                prompt=prompt,
                max_tokens=800  # Increased to handle longer translations
            )
            translated_chunks.append(response.generations[0].text.strip())

        return " ".join(translated_chunks)  # Join all translated parts
    
    except Exception as e:
        return f"Error translating: {str(e)}"

# Summarize Hindi guidance to 100 words
def summarize_text(text):
    try:
        response = co.generate(
            model="command-xlarge-nightly",
            prompt=f"Summarize the following text in 100 words in Hindi while keeping all key details:\n\n{text}",
            max_tokens=300  # Increased max tokens for better summarization
        )
        return response.generations[0].text.strip()
    
    except Exception as e:
        return f"Error summarizing: {str(e)}"

# Convert Hindi text to speech and play it
def speak_text_hindi(text):
    try:
        temp_audio_path = "temp_audio.mp3"
        tts = gTTS(text=text, lang="hi", slow=False)  # Ensure normal speed
        tts.save(temp_audio_path)  # Save the audio file

        # Initialize pygame mixer
        pygame.mixer.init()
        pygame.mixer.music.load(temp_audio_path)
        pygame.mixer.music.play()

        # Wait for audio to finish
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        # Quit mixer and remove file after playing
        pygame.mixer.quit()
        os.remove(temp_audio_path)

    except Exception as e:
        print(f"Error in playing audio: {str(e)}")

# Convert OpenCV image to base64 for Dash display
def image_to_base64(image):
    _, buffer = cv2.imencode(".jpg", image)
    return f"data:image/jpeg;base64,{base64.b64encode(buffer).decode()}"

# Draw bounding boxes and labels on the image
def draw_boxes(image, detections, labels):
    for det, label in zip(detections, labels):
        x1, y1, x2, y2, conf, _ = det
        cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        cv2.putText(image, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    return image

app.layout = html.Div([
    html.H1("Weapon Detection and Tactical Guidance", className="text-center text-primary mt-4"),
    html.Div([
        dcc.Upload(
            id='upload-image',
            children=html.Button('Upload Image', className="btn btn-success"),
            multiple=False,
            className="d-flex justify-content-center"
        ),
        html.Div([
            html.Button('Process Image', id='process-btn', n_clicks=0, className="btn btn-primary mx-2"),
        ], className="d-flex justify-content-center mt-3"),
        html.Div(id='output-detection', className="text-center mt-3 text-info"),
        html.Img(id='display-image', style={'width': '50%', 'display': 'block', 'margin': 'auto'}, className="mt-3"),
        html.Div(id='guidance-output', className="text-center mt-3 text-success")
    ], className="container text-center")
])

@app.callback(
    [Output('display-image', 'src'), Output('output-detection', 'children'), Output('guidance-output', 'children')],
    [Input('process-btn', 'n_clicks')],
    [State('upload-image', 'contents')]
)
def process_image(n_clicks, contents):
    if not contents:
        return None, "Please upload an image.", ""
    
    try:
        # Decode the uploaded image
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        np_arr = np.frombuffer(decoded, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if image is None:
            return None, "Error: Unable to decode the image.", ""
        
        if n_clicks > 0:
            # Detect objects
            detected_labels = detect_objects(image)
            
            if detected_labels and detected_labels[0] != "No weapons detected":
                weapon = detected_labels[0]  # Take first detected weapon
                
                # Generate tactical guidance
                guidance = generate_defense_guidance(weapon)
                
                hindi_guidance = translate_to_hindi(guidance)  # Ensure full translation
                summarized_hindi = summarize_text(hindi_guidance)
                
                # Play audio
                speak_text_hindi(summarized_hindi)
                
                # Draw bounding boxes
                results = model(image)
                detections = results[0].boxes.data.cpu().numpy()
                image_with_boxes = draw_boxes(image.copy(), detections, detected_labels)
                
                return image_to_base64(image_with_boxes), f"Detected Weapons: {', '.join(detected_labels)}", html.Div([
                    html.H4("Tactical Guidance (English):"),
                    html.P(guidance),
                    html.H4("Tactical Guidance (Hindi):"),
                    html.P(summarized_hindi)
                ])
            else:
                return image_to_base64(image), "No weapons detected.", ""
        
        return None, "No operation performed.", ""
    
    except Exception as e:
        return None, f"Error: {str(e)}", ""

if __name__ == '__main__':
    app.run_server(debug=True)
