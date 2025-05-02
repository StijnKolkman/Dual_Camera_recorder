"""
Dual Camera Tracking and Trajectory Reconstruction

This script is designed to automate the process of:
1. Recording videos using two cameras through the DualCameraApp GUI.
2. Tracking UMR's in the recorded videos using VideoTracker.
3. Reconstructing and plotting the 3D trajectory of the UMR's using TrajectoryReconstructor.

Main Workflow:
- After the recording is completed, the 'on_recording_done' function is triggered.
- The recorded video files are passed to the VideoTracker to extract tracking data.
- The tracking data is saved in CSV format, which is then fed into the TrajectoryReconstructor for 3D trajectory reconstruction.
- Finally, the trajectory is plotted.

Dependencies:
- DualCameraApp (from RecorderClass.py): Provides GUI for dual camera video recording.
- VideoTracker (from TrackerClass.py): Tracks objects in video recordings.
- TrajectoryReconstructor (from TrajectoryClassV2.py): Reconstructs and plots the trajectory from tracking data.

Author: Stijn Kolkman (s.y.kolkman@student.utwente.nl)
Date: April 2025
"""

from include.RecorderClassV2 import DualCameraApp
from include.TrackerClassV3 import VideoTracker
from include.TrajectoryClassV5 import TrajectoryReconstructor
import tkinter as tk

# Function to be called after the recording process is finished, to start the tracker and trajectory generator
def on_recording_done():
    if hasattr(app, "recorded_file_names") and app.recorded_file_names:
        #Get the names of the recorded files
        cam1_file, cam2_file = app.recorded_file_names
        print("Recorded file names:", cam1_file, cam2_file)

        # Apply the tracker on the recordings
        tracker_cam1 = VideoTracker(cam1_file)
        tracker_cam1.track_and_save()
        csv_file_cam1 = tracker_cam1.csv_filename
        tracker_cam2 = VideoTracker(cam2_file)
        tracker_cam2.track_and_save()
        csv_file_cam2 = tracker_cam2.csv_filename
        
        # Apply the trajectory generator on the data from the tracker
        traj_reconstructor = TrajectoryReconstructor(csv_file_cam1, csv_file_cam2)
        traj_reconstructor.reconstruct()
        traj_reconstructor.plot_trajectory()
        traj_reconstructor.plot_velocity()
    else:
        print("No recordings were generated.")

# Start the recorder GUI
root = tk.Tk()
app = DualCameraApp(root)
app.set_recording_done_callback(on_recording_done)
root.mainloop()