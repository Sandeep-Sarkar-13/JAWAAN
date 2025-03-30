import dash
from dash import Dash, dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import base64
import tempfile
import cv2
from threading import Thread, Event
import numpy as np
from ultralytics import YOLO
import requests
import io
import matplotlib.pyplot as plt
import heapq
import math
from flask import request
import cohere
from gtts import gTTS
import pygame
import os


# Initialize Cohere API
COHERE_API_KEY = "d28Y2HwnozUpGgMspNmhA83M3HZPJCAfqQoDqeuw"
co = cohere.Client(COHERE_API_KEY)
# FastAPI service URL
FASTAPI_URL = "http://127.0.0.1:10000/predict"

# App Initialization
app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
app.config.suppress_callback_exceptions = True

# Global variables
yolo_model = YOLO("final_jawaan_final_120.pt")
video_capture = None
latest_frame = None
thermal_frame = None
magma_frame = None
detection_data = {}
unauthorized_counts = []
stop_event = Event()
processing_thread = None
video_file_path = None
processing_started = False
unauthorized_detected = False
use_webcam = False  # Webcam usage flag

# Lethality tab global variables
lethality_model = YOLO("ffinal_weapons.pt")
uploaded_image = None
detected_weapons = []
guidance_text = ""
hindi_summary = ""


import torch
# Removed extra indent before try
try:
    model_dict = torch.load("final_jawaan_final_120.pt")
except Exception as e:
    print("Error loading model:", e)

class Node:
    """Represents a node in the grid."""
    def __init__(self, x, y, cost=0, parent=None):
        self.x = x
        self.y = y
        self.cost = cost
        self.parent = parent

    def __lt__(self, other):
        return self.cost < other.cost

def heuristic(node, goal):
    """Heuristic function: Euclidean distance."""
    return math.sqrt((node.x - goal.x) ** 2 + (node.y - goal.y) ** 2)

def a_star(start, goal, obstacles, grid_size):
    """A* pathfinding algorithm with additional checks to avoid infinite loops."""
    open_list = []
    closed_list = set()
    heapq.heappush(open_list, (0, start))

    while open_list:
        # Pop the node with the smallest cost
        _, current_node = heapq.heappop(open_list)

        # Check if the current node is the goal
        if (current_node.x, current_node.y) == (goal.x, goal.y):
            path = []
            while current_node:
                path.append((current_node.x, current_node.y))
                current_node = current_node.parent
            return path[::-1]  # Return the path in the correct order

        # Add current node to closed list
        closed_list.add((current_node.x, current_node.y))

        # Explore neighbors
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:  # Up, Down, Left, Right
            neighbor_x, neighbor_y = current_node.x + dx, current_node.y + dy

            # Skip out-of-bounds neighbors
            if not (0 <= neighbor_x < grid_size[0] and 0 <= neighbor_y < grid_size[1]):
                continue

            # Skip obstacles or already processed nodes
            if (neighbor_x, neighbor_y) in obstacles or (neighbor_x, neighbor_y) in closed_list:
                continue

            # Calculate the neighbor's cost and heuristic
            neighbor = Node(neighbor_x, neighbor_y, current_node.cost + 1, current_node)
            neighbor.cost += heuristic(neighbor, goal)

            # Skip adding neighbors already in the open list with a lower cost
            if any(neighbor_x == n.x and neighbor_y == n.y and neighbor.cost >= n.cost for _, n in open_list):
                continue

            heapq.heappush(open_list, (neighbor.cost, neighbor))

    return None

def visualize_path(grid_size, obstacles, path, title):
    """Visualize a path on a grid."""
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_xlim(-1, grid_size[0])
    ax.set_ylim(-1, grid_size[1])
    ax.set_xticks(range(grid_size[0]))
    ax.set_yticks(range(grid_size[1]))
    ax.grid(True)

    # Plot obstacles
    for obs in obstacles:
        ax.add_patch(plt.Rectangle(obs, 1, 1, color="black"))

    # Plot path
    if path:
        x, y = zip(*path)
        ax.plot(x, y, marker="o", color="green", label="Path")

    ax.set_title(title)
    ax.legend()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    return buf

# Generate paths for the plots
grid_size = (10, 10)
obstacles = {(3, 3), (3, 4), (3, 5), (4, 5), (5, 5)}
start = Node(0, 0)
goal = Node(7, 7)

path_with_obstacles = a_star(start, goal, obstacles, grid_size)
path_without_obstacles = a_star(start, goal, set(), grid_size)

img_with_obstacles = visualize_path(grid_size, obstacles, path_with_obstacles, "Path With Obstacles")
img_without_obstacles = visualize_path(grid_size, set(), path_without_obstacles, "Path Without Obstacles")


def release_video():
    global video_capture
    if video_capture:
        video_capture.release()
        video_capture = None

def process_video():
    global latest_frame, thermal_frame, magma_frame, unauthorized_detected, video_capture

    if video_capture is None:
        return

    frame_count = 0
    unauthorized_chunk_count = 0

    while video_capture.isOpened():
        success, frame = video_capture.read()
        if not success or stop_event.is_set():
            break

        frame_resized = cv2.resize(frame, (960, 540))
        results = yolo_model.predict(frame_resized)
        result = results[0]

        for box in result.boxes:
            label = result.names[box.cls[0].item()]
            if label == "Unauthorized":
                unauthorized_chunk_count += 1
                unauthorized_detected = True

        gray_frame = cv2.cvtColor(frame_resized, cv2.COLOR_RGB2GRAY)
        thermal_map = cv2.applyColorMap(gray_frame, cv2.COLORMAP_JET)
        magma_map = cv2.applyColorMap(gray_frame, cv2.COLORMAP_MAGMA)

        latest_frame = cv2.imencode('.jpg', result.plot())[1].tobytes()
        thermal_frame = cv2.imencode('.jpg', thermal_map)[1].tobytes()
        magma_frame = cv2.imencode('.jpg', magma_map)[1].tobytes()

    print("Video processing completed.")

@app.callback(
    Output('video-display', 'src'),
    [Input('upload-video', 'contents')],
    [State('upload-video', 'filename')]
)

def display_video(contents, filename):
    global video_capture, video_file_path, use_webcam, stop_event, processing_started
    if contents and not use_webcam:
        if processing_started:
            stop_event.set()
            processing_thread.join()
            release_video()
            processing_started = False

        content_type, content_string = contents.split(',')
        video_data = base64.b64decode(content_string)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        temp_file.write(video_data)
        temp_file.close()

        video_file_path = temp_file.name
        video_capture = cv2.VideoCapture(video_file_path)

        if video_capture.isOpened():
            print(f"Video file uploaded: {video_file_path}")
            return f"data:video/mp4;base64,{base64.b64encode(video_data).decode()}"
        else:
            print("Error: Could not open video file.")
    return None

@app.callback(
    Output('live-detection', 'src'),
    Output('thermal-frame', 'src'),
    Output('magma-frame', 'src'),
    Output('unauthorized-alert', 'is_open'),
    Input('interval-component', 'n_intervals')
)


def update_frames(n_intervals):
    global unauthorized_detected
    detection_src = (
        'data:image/jpeg;base64,' + base64.b64encode(latest_frame).decode('utf-8')
        if latest_frame else ""
    )
    thermal_src = (
        'data:image/jpeg;base64,' + base64.b64encode(thermal_frame).decode('utf-8')
        if thermal_frame else ""
    )
    magma_src = (
        'data:image/jpeg;base64,' + base64.b64encode(magma_frame).decode('utf-8')
        if magma_frame else ""
    )

    return detection_src, thermal_src, magma_src, unauthorized_detected


@app.callback(
    Output('dummy-div', 'children'),
    Input('start-processing', 'n_clicks'),
    Input('stop-processing', 'n_clicks'),
    Input('toggle-webcam', 'n_clicks'),
    prevent_initial_call=True
)

def manage_processing(start_clicks, stop_clicks, toggle_webcam_clicks):
    global processing_thread, processing_started, stop_event, use_webcam, video_capture
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update

    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if triggered_id == 'start-processing' and not processing_started:
        stop_event.clear()
        if use_webcam:
            video_capture = cv2.VideoCapture(0)
        processing_thread = Thread(target=process_video)
        processing_thread.start()
        processing_started = True
    elif triggered_id == 'stop-processing' and processing_started:
        stop_event.set()
        processing_thread.join()
        release_video()
        processing_started = False
    elif triggered_id == 'toggle-webcam':
        use_webcam = not use_webcam
        release_video()

    return None

@app.callback(
    [Output("classification-result", "children"),
     Output("audio-plot", "children")],
    [Input("classify-button", "n_clicks")],
    [State("upload-video", "filename"), State("upload-video", "contents")]
)


def classify_video(n_clicks, filename, contents):
    if n_clicks and filename and contents:
        content_type, content_string = contents.split(",")
        video_data = base64.b64decode(content_string)

        try:
            files = {"file": (filename, video_data)}
            response = requests.post(FASTAPI_URL, files=files)
            response_data = response.json()

            if "error" in response_data:
                return html.Div(f"Error: {response_data['error']}", className="text-danger"), None

            # Extracting data from the response
            audio_class = response_data.get("audio_class", "Unknown")
            audio_plot_base64 = response_data.get("audio_features_plot", "")
            detected_language = response_data.get("detected_language", "Unknown")
            transcription = response_data.get("transcription", "Unknown")
            translated_text = response_data.get("translated_text", "Unknown")
            text_classification = response_data.get("text_classification", "Unknown")

            # Convert the result into Dash components
            result_display = html.Div([
                html.H5("Classification Results:", className="text-primary"),
                html.P(f"Predicted Audio Class: {audio_class}"),
                html.P(f"Detected Language: {detected_language}"),
                html.P(f"Transcription: {transcription}"),
                html.P(f"Translated Text: {translated_text}"),
                html.P(f"Text Classification: {text_classification}"),
            ])

            # Convert the audio plot to an image
            plot = html.Img(
                src=f"data:image/png;base64,{audio_plot_base64}",
                style={"maxWidth": "100%"}
            ) if audio_plot_base64 else None

            return result_display, plot

        except Exception as e:
            return html.Div(f"Error: {str(e)}", className="text-danger"), None

    return None, None

app.layout = html.Div([
    html.H1("FAUJJI", style={
        'textAlign': 'center',
        'color': '#D4AF37',
        'fontSize': '3em',
        'fontWeight': '700',
    }),

    dbc.ButtonGroup([
    dbc.Button(
        'VIGILANCE', 
        id='vigilance-tab', 
        color="primary", 
        n_clicks=0,
        className="mx-2",  # Add margin between buttons
        style={
            'fontSize': '1.2em',  # Increase font size
            'fontWeight': 'bold',  # Bold text
            'borderRadius': '10px',  # Rounded corners
            'boxShadow': '2px 2px 5px rgba(0, 0, 0, 0.2)',  # Add shadow
            'transition': 'all 0.3s ease',  # Smooth hover effect
        }
    ),
    dbc.Button(
        'LETHALITY', 
        id='lethality-tab', 
        color="success", 
        n_clicks=0,
        className="mx-2",
        style={
            'fontSize': '1.2em',
            'fontWeight': 'bold',
            'borderRadius': '10px',
            'boxShadow': '2px 2px 5px rgba(0, 0, 0, 0.2)',
            'transition': 'all 0.3s ease',
        }
    ),
    dbc.Button(
        'SOS', 
        id='sos-tab', 
        href='https://sos-jawaan.netlify.app/', 
        target='_blank', 
        color="danger",  # Red color for SOS button
        n_clicks=0,
        className="mx-2",
        style={
            'fontSize': '1.2em',
            'fontWeight': 'bold',
            'borderRadius': '10px',
            'boxShadow': '2px 2px 5px rgba(0, 0, 0, 0.2)',
            'transition': 'all 0.3s ease',
        }
    ),
    dbc.Button(
        'HEALTH', 
        id='health-tab', 
        href='https://faujji-health.netlify.app/', 
        target='_blank', 
        color="info", 
        n_clicks=0,
        className="mx-2",
        style={
            'fontSize': '1.2em',
            'fontWeight': 'bold',
            'borderRadius': '10px',
            'boxShadow': '2px 2px 5px rgba(0, 0, 0, 0.2)',
            'transition': 'all 0.3s ease',
        }
    ),
    dbc.Button(
        'GAME TRAINING', 
        id='game-tab', 
        href='https://faujji-trainer.netlify.app/', 
        target='_blank', 
        color="warning", 
        n_clicks=0,
        className="mx-2",
        style={
            'fontSize': '1.2em',
            'fontWeight': 'bold',
            'borderRadius': '10px',
            'boxShadow': '2px 2px 5px rgba(0, 0, 0, 0.2)',
            'transition': 'all 0.3s ease',
        }
    ),
], className='d-flex justify-content-center my-3'),

    html.Div(id='content-container', className='p-4'),
])


@app.callback(
    Output('content-container', 'children'),
    [Input('vigilance-tab', 'n_clicks'),
     Input('lethality-tab', 'n_clicks'),
     Input('sos-tab', 'n_clicks')]
)



#TAB FUNCTION
def render_content(vigilance_clicks, lethality_clicks, sos_clicks):
    ctx = callback_context
    if not ctx.triggered:
        return ""

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'vigilance-tab':
        return html.Div([
            html.H3("Vigilance System", className="text-center text-primary mb-4"),
            dcc.Upload(
                id="upload-video",
                children=html.Div(["Drag and Drop or ", html.A("Select a Video File")]),
                style={
                    "width": "100%",
                    "height": "60px",
                    "lineHeight": "60px",
                    "borderWidth": "1px",
                    "borderStyle": "dashed",
                    "borderRadius": "5px",
                    "textAlign": "center",
                    "margin": "10px"
                },
                multiple=False
            ),
            html.Video(id='video-display', controls=True, style={'width': '100%'}),
            dbc.Row([
        dbc.Col(dbc.Button("Classify Video", id="classify-button", color="primary", n_clicks=0)),
        dbc.Col(dbc.Button("Start Processing", id="start-processing", color="success")),
        dbc.Col(dbc.Button("Stop Processing", id="stop-processing", color="danger")),
        dbc.Col(dbc.Button("Toggle Webcam", id="toggle-webcam", color="info")),
    ]),

             dbc.Row([
        dbc.Col(html.Img(id='live-detection', style={"width": "100%"}), width=4),
        dbc.Col(html.Img(id='thermal-frame', style={"width": "100%"}), width=4),
        dbc.Col(html.Img(id='magma-frame', style={"width": "100%"}), width=4),
    ]),

        dbc.Alert("Unauthorized Person Detected!", id="unauthorized-alert", color="danger", is_open=False),
        html.Div(id="classification-result", className="mt-4"),
        html.Div(id="audio-plot", className="mt-4"),
        html.Div(id='dummy-div'),

        dcc.Interval(id='interval-component', interval=1000, n_intervals=0),

        html.Hr(),

        dbc.Row([
        dbc.Col(html.Img(src=f"data:image/png;base64,{base64.b64encode(img_with_obstacles.read()).decode('utf-8')}", style={"width": "100%"}), width=6),
        dbc.Col(html.Img(src=f"data:image/png;base64,{base64.b64encode(img_without_obstacles.read()).decode('utf-8')}", style={"width": "100%"}), width=6),
        ]),
    ])

    elif button_id == 'lethality-tab':
        return html.Div([
        html.H3("Lethality System", className="text-center text-primary mb-4"),
        dcc.Upload(
            id="upload-image",
            children=html.Div(["Drag and Drop or ", html.A("Select an Image File")]),
            style={
                "width": "100%",
                "height": "60px",
                "lineHeight": "60px",
                "borderWidth": "1px",
                "borderStyle": "dashed",
                "borderRadius": "5px",
                "textAlign": "center",
                "margin": "10px"
            },
            multiple=False
        ),
        html.Img(
            id='image-display', 
            style={
                'width': '70%',  # Set width to 70%
                'height': '50%',  # Set height to 80%
                'display': 'block',  # Center the image horizontally
                'margin-left': 'auto',  # Center the image horizontally
                'margin-right': 'auto',  # Center the image horizontally
                'margin-top': '20px',  # Add some top margin for better spacing
            }
        ),
        # Button placed below the image
        html.Div(
            dbc.Button("Process Image", id="process-image", color="primary", className="mt-3"),
            style={
                'textAlign': 'center',  # Center the button horizontally
                'margin-top': '20px',  # Add some top margin for spacing
            }
        ),
        html.Div(id="detected-weapons", className="mt-4"),
        html.Div(id="guidance-text", className="mt-4"),
        html.Div(id="hindi-summary", className="mt-4"),
        html.Audio(id="audio-player", controls=True, className="mt-4")
    ])
    else:
        return html.Div(f"Content for {button_id.split('-')[0].capitalize()} ")


# Callback to handle image upload and display
@app.callback(
    Output('image-display', 'src'),
    [Input('upload-image', 'contents')],
    [State('upload-image', 'filename')]
)
def upload_image(contents, filename):
    global uploaded_image
    if contents is not None:
        content_type, content_string = contents.split(',')
        image_data = base64.b64decode(content_string)
        uploaded_image = image_data
        return f"data:image/jpeg;base64,{base64.b64encode(image_data).decode('utf-8')}"
    return None


# Generate tactical defense guidance
def generate_defense_guidance(weapon):
    try:
        prompt = (f"I am a soldier spotting an enemy armed with a {weapon}. Provide a rapid, effective response including, make entire sentences, within 200 words: "
                  "tactical escape strategies, and survival techniques to neutralize or evade the threat.")        
        response = co.generate(
            model="command-xlarge-nightly",
            prompt=prompt,
            max_tokens=500,  # Increased max tokens for better completion
            temperature=0.5,
            stop_sequences=["###"]
        )
        
        return response.generations[0].text.strip()
    
    except Exception as e:
        return f"Error generating guidance: {str(e)}"

# Translate guidance to Hindi (Ensuring completeness)
def translate_to_hindi(text):
    try:
        prompt = (f"Translate the following English text to Hindi in a complete, fluent, and structured manner. Ensure no information is lost:\n\n{text}")
        
        response = co.generate(
            model="command-xlarge-nightly",
            prompt=prompt,
            max_tokens=500  # Increased to prevent incomplete translations
        )
        return response.generations[0].text.strip()
    
    except Exception as e:
        return f"Error translating: {str(e)}"

# Summarize Hindi guidance to 100 words
def summarize_text(text):
    try:
        response = co.generate(
            model="command-xlarge-nightly",
            prompt=f"Summarize the following text in 100 words in Hindi while keeping all key details:\n\n{text}",
            max_tokens=250  # Adjusted for better summarization
        )
        return response.generations[0].text.strip()
    
    except Exception as e:
        return f"Error summarizing: {str(e)}"

# Define the detect_objects function
def detect_objects(image, model):
    results = model(image)
    detections = results[0].boxes.data.cpu().numpy()

    labels_map = {
        0: "Shotguns",
        1: "Assault Rifle",
        2: "LMGs",
        3: "Pistols",
        4: "SMGs",
        5: "Snipers",
        6: "Throwables"
    }

    detected_labels = []

    for detection in detections:
        _, _, _, _, confidence, class_id = detection
        label = labels_map.get(int(class_id), "Unknown")
        detected_labels.append(f"{label} ({confidence:.2f})")

    return detected_labels

# Callback to process image and display results
@app.callback(
    [Output('detected-weapons', 'children'),
     Output('guidance-text', 'children'),
     Output('hindi-summary', 'children'),
     Output('audio-player', 'src')],
    [Input('process-image', 'n_clicks')]
)
def process_image_callback(n_clicks):
    global uploaded_image, detected_weapons, guidance_text, hindi_summary, lethality_model
    if n_clicks is None or uploaded_image is None:
        return None, None, None, None

    try:
        # Process image and detect weapons
        image = cv2.imdecode(np.frombuffer(uploaded_image, np.uint8), cv2.IMREAD_COLOR)
        detected_weapons = detect_objects(image, lethality_model)  # Pass lethality_model here

        if detected_weapons:
            weapon = detected_weapons[0]  # Take first detected weapon
            guidance_text = generate_defense_guidance(weapon)
            hindi_guidance = translate_to_hindi(guidance_text)
            hindi_summary = summarize_text(hindi_guidance)

            # Convert Hindi summary to speech
            temp_audio_path = "temp_audio.mp3"
            tts = gTTS(text=hindi_summary, lang="hi", slow=False)
            tts.save(temp_audio_path)
            audio_src = f"data:audio/mp3;base64,{base64.b64encode(open(temp_audio_path, 'rb').read()).decode('utf-8')}"
            os.remove(temp_audio_path)

            return (
                html.Div([html.P(f"Detected Weapon: {weapon}")]),
                html.Div([html.P(f"Guidance: {guidance_text}")]),
                html.Div([html.P(f"Hindi Summary: {hindi_summary}")]),
                audio_src
            )
        else:
            return html.Div("No weapons detected."), None, None, None
    except Exception as e:
        print(f"Error in process_image_callback: {e}")
        return html.Div(f"Error: {str(e)}"), None, None, None

if __name__ == '__main__':
    app.run_server(debug=True)