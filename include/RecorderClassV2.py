"""
DualCameraApp Class

This class provides a graphical user interface (GUI) for recording video using two cameras 
simultaneously. It allows the user to control the recording process, including the ability 
to start/stop recording, adjust the camera focus, and save the recorded video files. The 
recorded files are saved in AVI format, and the filenames are generated dynamically based 
on user input.

Methods:
- __init__(window): Initializes the application window, sets up the GUI components, and initializes cameras.
- set_focus1(val): Sets the focus of camera 1 based on the slider value.
- set_focus2(val): Sets the focus of camera 2 based on the slider value.
- set_recording_done_callback(callback): Sets a callback function to be called when the recording is finished.
- toggle_recording(): Starts or stops the recording process.
- update_frame(): Continuously updates the frames from both cameras in the GUI.
- on_closing(): Releases the video capture objects and destroys the window when the application is closed.

Author: Stijn Kolkman (s.y.kolkman@student.utwente.nl)
Date: April 2025
"""

import cv2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import time
import numpy as np 
import os
import subprocess 
import csv

cap_api = cv2.CAP_DSHOW  # Found to be the best API for using with logitech C920 in Windows. Other options are also possible

class DualCameraApp:
    def __init__(self, window):
        self.window = window
        self.window.title("Dual Camera Recorder")
        self.recording = False
        self.recorded_file_names = None 
        self.frames_cam1 = []
        self.frames_cam2 = []
        self.record_start_time = None

        # Define the size of the GUI
        self.window.geometry("1250x700")

        # Here the camera's are defined. Camera's can have different numbers on different computers, so change the number if needed (default is cap1 = 1, cap2 = 0)
        self.cap1 = cv2.VideoCapture(1, cap_api) # cap1 needs to be the bottom camera!!
        self.cap2 = cv2.VideoCapture(0, cap_api)

        # Camera resolution
        self.cap1.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap1.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.cap2.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap2.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        # Camera framerate
        self.cap1.set(cv2.CAP_PROP_FPS, 30)
        self.cap2.set(cv2.CAP_PROP_FPS, 30)

        # Camera compression technique --> If turned off the FPS will be really low (around 5 fps)
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        self.cap1.set(cv2.CAP_PROP_FOURCC, fourcc)
        self.cap2.set(cv2.CAP_PROP_FOURCC, fourcc)

        #Turns off the autofocus 
        self.cap1.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        self.cap2.set(cv2.CAP_PROP_AUTOFOCUS, 0)

        # Camera calibration parameters
        self.camera_matrix1 = np.array([
            [1397.9,   0, 953.6590],
            [   0, 1403.0, 555.1515],
            [   0,   0,   1]
        ], dtype=np.float64)
        self.dist_coeffs1 = np.array([0.1216, -0.1727, 0.00, 0.00, 0.0], dtype=np.float64)
        self.camera_matrix2 = np.array([
            [1397.9,   0, 953.6590],
            [   0, 1403.0, 555.1515],
            [   0,   0,   1]
        ], dtype=np.float64)
        self.dist_coeffs2 = np.array([0.1216, -0.1727, 0.00, 0.00, 0.0], dtype=np.float64)

        # === GUI components ===
        # Label to display the text "File name:"
        self.filename_label = tk.Label(window, text="File name:")
        self.filename_label.pack(pady=(10, 0))

        # Entry widget to allow the user to input a file name
        self.filename_entry = tk.Entry(window)
        self.filename_entry.insert(0, "Recording")
        self.filename_entry.pack(pady=(0, 10))

        # Frame container that holds the two video display labels side by side
        self.frame_container = tk.Frame(window)
        self.frame_container.pack()

        # Label for displaying the first video feed, placed on the left side of the frame container
        self.video_label1 = tk.Label(self.frame_container)
        self.video_label1.pack(side="left", padx=10)

        # Label for displaying the second video feed, placed on the right side of the frame container
        self.video_label2 = tk.Label(self.frame_container)
        self.video_label2.pack(side="right", padx=10)

        # Label and slider for adjusting the focus of the first camera
        self.focus_label1 = tk.Label(window, text="Focus Camera 1")
        self.focus_label1.pack()

        # Slider for setting the focus of Camera 1, with a range from 0 to 255
        self.focus_slider1 = ttk.Scale(window, from_=0, to=255, orient='horizontal', length=400, command=self.set_focus1)
        self.focus_slider1.set(58)  # Set the default focus value for Camera 1 to 58
        self.focus_slider1.pack()

        # Label to display the current focus value for Camera 1
        self.focus_value_label1 = tk.Label(window, text=f"Focus Camera 1 Value: {self.focus_slider1.get()}")
        self.focus_value_label1.pack()

        # Label and slider for adjusting the focus of the second camera
        self.focus_label2 = tk.Label(window, text="Focus Camera 2")
        self.focus_label2.pack()

        # Slider for setting the focus of Camera 2, with a range from 0 to 255
        self.focus_slider2 = ttk.Scale(window, from_=0, to=255, orient='horizontal', length=400, command=self.set_focus2)
        self.focus_slider2.set(91)  # Set the default focus value for Camera 2 to 91
        self.focus_slider2.pack()

        # Label to display the current focus value for Camera 2
        self.focus_value_label2 = tk.Label(window, text=f"Focus Camera 2 Value: {self.focus_slider2.get()}")
        self.focus_value_label2.pack()

        # Button to start or stop recording
        self.record_button = tk.Button(window, text="Start recording", command=self.toggle_recording, bg="red", fg="white")
        self.record_button.pack(pady=10)

        # Label to display the names of the recorded files (empty initially)
        self.recorded_files_label = tk.Label(window, text="", fg="blue")
        self.recorded_files_label.pack(pady=10)

        #Initiate timestamps array
        self.timestamps = []

        # Method to continuously update the frame (e.g., display live video feed)
        self.update_frame()

        # Ensuring proper cleanup
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

    def set_focus1(self, val):
        # Update the focus on camera1
        focus_value = float(val)
        self.cap1.set(cv2.CAP_PROP_FOCUS, focus_value)
        if hasattr(self, 'focus_value_label1'):  # Ensure the label exists before updating
            # Update the label
            self.focus_value_label1.config(text=f"Focus Camera 1 Value: {focus_value:.2f}")

    def set_focus2(self, val):
        # Update the focus on camera2
        focus_value = float(val)
        self.cap2.set(cv2.CAP_PROP_FOCUS, focus_value)
        if hasattr(self, 'focus_value_label2'):  # Ensure the label exists before updating
            # Update the label
            self.focus_value_label2.config(text=f"Focus Camera 2 Value: {focus_value:.2f}")

    def set_recording_done_callback(self, callback):
        # needed to send to  main that the recording is done and the tracker should start
        self.recording_done_callback = callback

    def toggle_recording(self):
        self.recording = not self.recording
        filename = self.filename_entry.get().strip() or "recording"
        output_dir = os.path.join(os.getcwd(), filename)
        os.makedirs(output_dir, exist_ok=True)

        cam1_filename = os.path.join(output_dir, f"{filename}_cam1.avi")
        cam2_filename = os.path.join(output_dir, f"{filename}_cam2.avi")

        if self.recording:
            # Create video writer
            self.frames_cam1 = []
            self.frames_cam2 = []
            self.record_start_time = time.time()
            self.record_button.config(text="Stop recording", bg="gray")
            self.recorded_files_label.config(text="Recording in progress...")
            print(f"Started recording: {cam1_filename} & {cam2_filename}")
            
            self.out1 = cv2.VideoWriter(cam1_filename, cv2.VideoWriter_fourcc(*'XVID'), 30, (1920, 1080))
            self.out2 = cv2.VideoWriter(cam2_filename, cv2.VideoWriter_fourcc(*'XVID'), 30, (1920, 1080))

        else:
            # Stop recording and calculate FPS
            duration = time.time() - self.record_start_time
            fps_value = len(self.frames_cam1) / duration if duration > 0 else 30.0
            print(f"Duration: {duration:.2f}s — FPS: {fps_value:.2f}")

            # Adjust the FPS value of the video writers after recording
            self.out1.set(cv2.CAP_PROP_FPS, fps_value)
            self.out2.set(cv2.CAP_PROP_FPS, fps_value)
            self.out1.release()
            self.out2.release()
            #self.fix_video_fps_inplace(cam1_filename, fps_value)
            #self.fix_video_fps_inplace(cam2_filename, fps_value)
            #print(f'Fixed video 1 and 2 fps to {fps_value}')

            self.record_button.config(text="Start recording", bg="red")
            files_text = f"Recorded files:\n{cam1_filename}\n{cam2_filename}"
            self.recorded_files_label.config(text=files_text)
            print("Recording done and saved")
            self.recorded_file_names = (cam1_filename, cam2_filename)  # Store filenames

            # Save timestamps to CSV
            timestamp_filename = os.path.join(output_dir, f"{filename}_timestamps.csv")
            with open(timestamp_filename, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Frame", "Timestamp (s)"])
                for i, ts in enumerate(self.timestamps):
                    writer.writerow([i, ts])

            print(f"[INFO] Timestamps saved to {timestamp_filename}")

            # Call the callback when recording is done and change the fps to the correct value, but only if files are recorded
            if hasattr(self, 'recording_done_callback') and self.recorded_file_names:
                self.recording_done_callback()  # Notify that recording is done

    def update_frame(self):
        # Check if the window is still open before updating
        if not self.window.winfo_exists():
            return  # Exit the function if the window is closed
        
         #Read the frames
        ret1, frame1 = self.cap1.read()
        ret2, frame2 = self.cap2.read()

        if self.recording and ret1 and ret2:
            # Save frames
            self.frames_cam1.append(frame1.copy())
            self.frames_cam2.append(frame2.copy())
            self.out1.write(frame1)
            self.out2.write(frame2)

            # Only log timestamp if both frames were successfully saved
            timestamp = time.time() - self.record_start_time
            self.timestamps.append(timestamp)

        #Undistort the frames --> I UNDISTORT IN THE TRAJECTORY GENERATOR CLASS
        #frame1 = cv2.undistort(frame1, self.camera_matrix1, self.dist_coeffs1)
        #frame2 = cv2.undistort(frame2, self.camera_matrix2, self.dist_coeffs2)

        if ret1:
            # Update the GUI with the frame --> first the frame is resized to fit in the GUI 
            frame1_resized = cv2.resize(frame1, (576, 324), interpolation=cv2.INTER_LINEAR)
            frame_rgb1 = cv2.cvtColor(frame1_resized, cv2.COLOR_BGR2RGB)
            img1 = ImageTk.PhotoImage(Image.fromarray(frame_rgb1))
            self.video_label1.imgtk = img1
            self.video_label1.config(image=img1)

        if ret2:
            # Update the GUI with the frame --> first the frame is resized to fit in the GUI     
            frame2_resized = cv2.resize(frame2, (576, 324), interpolation=cv2.INTER_LINEAR)
            frame_rgb2 = cv2.cvtColor(frame2_resized, cv2.COLOR_BGR2RGB)
            img2 = ImageTk.PhotoImage(Image.fromarray(frame_rgb2))
            self.video_label2.imgtk = img2
            self.video_label2.config(image=img2)

        self.window.after(10, self.update_frame)

    def on_closing(self):
        self.cap1.release()
        self.cap2.release()
        self.window.destroy()

# Used if the recorder class is called seperately
if __name__ == "__main__":
    root = tk.Tk()
    app = DualCameraApp(root)
    root.mainloop()
