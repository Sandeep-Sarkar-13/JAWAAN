import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import cv2
import numpy as np
import base64
import tempfile
from ultralytics import YOLO
from threading import Thread, Event
import heapq
import math
import matplotlib.pyplot as plt
import io

# Dash application setup
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Global variables
video_capture = None
yolo_model = YOLO("final_jawaan_final_120.pt")
latest_frame = None
thermal_frame = None
magma_frame = None
detection_data = {}
unauthorized_counts = []  # Count of unauthorized persons every 10 frames
stop_event = Event()
processing_thread = None
video_file_path = None
processing_started = False
unauthorized_detected = False
use_webcam = False  # Flag to indicate webcam usage

# A* Pathfinding Functions
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
    global latest_frame, thermal_frame, magma_frame, detection_data, unauthorized_counts, unauthorized_detected, video_capture

    if video_capture is None:
        print("Error: video_capture is None. Exiting the video processing thread.")
        return

    frame_count = 0
    unauthorized_chunk_count = 0  # Tracks unauthorized count for 10-frame chunks

    while video_capture.isOpened():
        success, frame = video_capture.read()
        if not success or stop_event.is_set():
            break

        frame_count += 1
        frame_resized = cv2.resize(frame, (960, 540))
        results = yolo_model.predict(frame_resized)
        result = results[0]

        for box in result.boxes:
            label = result.names[box.cls[0].item()]
            if label == "Unauthorized":
                unauthorized_chunk_count += 1
                unauthorized_detected = True

        # Every 10 frames, update the count and reset
        if frame_count % 10 == 0:
            unauthorized_counts.append(unauthorized_chunk_count)
            unauthorized_chunk_count = 0

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

app.layout = html.Div([
    html.H1("Real-Time Video Processing Dashboard", style={"text-align": "center"}),

    dcc.Upload(
        id='upload-video',
        children=html.Div(['Drag and Drop or ', html.A('Select a Video File')]),
        style={
            'width': '80%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '1px', 'borderStyle': 'dashed',
            'borderRadius': '5px', 'textAlign': 'center', 'margin': 'auto'
        },
        accept='.mp4, .avi, .mov',
    ),

    # Video display component
    html.Video(id='video-display', style={'width': '70%', 'max-width': '2000px'}, controls=True),  # Define the video element here
    
    dbc.Row([
        dbc.Col(dbc.Button("Start Processing", id="start-processing", color="success")),
        dbc.Col(dbc.Button("Stop Processing", id="stop-processing", color="danger")),
        dbc.Col(dbc.Button("Toggle Webcam", id="toggle-webcam", color="info")),
    ], justify="center", style={"margin": "20px"}),

    dbc.Row([
        dbc.Col(dbc.Alert("Unauthorized Person Detected!", id="unauthorized-alert", color="danger", is_open=False), width=12),
    ]),

    dbc.Row([
        dbc.Col(html.Img(id='live-detection', style={"width": "100%"}), width=4),
        dbc.Col(html.Img(id='thermal-frame', style={"width": "100%"}), width=4),
        dbc.Col(html.Img(id='magma-frame', style={"width": "100%"}), width=4),
    ]),

    dcc.Interval(id='interval-component', interval=1000, n_intervals=0),

    html.Hr(),

    dbc.Row([
        dbc.Col(html.Img(src=f"data:image/png;base64,{base64.b64encode(img_with_obstacles.read()).decode('utf-8')}", style={"width": "100%"}), width=6),
        dbc.Col(html.Img(src=f"data:image/png;base64,{base64.b64encode(img_without_obstacles.read()).decode('utf-8')}", style={"width": "100%"}), width=6),
    ]),

    html.Div(id='dummy-div')
])


if __name__ == '__main__':
    app.run_server(debug=True)
