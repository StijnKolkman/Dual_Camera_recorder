"""
TrajectoryReconstructor Class

This class reconstructs the 3D trajectory of a moving object using input from two calibrated camera systems:
- Camera 1 provides 2D object coordinates (X, Y).
- Camera 2 provides depth-related information (interpreted from its Y coordinate).
The reconstruction is based on known physical dimensions of a calibration object (box) visible to both cameras,
allowing conversion of pixel measurements to real-world units (millimeters).

Main Workflow:
- Loads object tracking data from two CSV files:
  - Camera 1: provides 2D image coordinates (X, Y).
  - Camera 2: provides depth-related information derived from Y-coordinates.
- Computes real-world scaling factors (mm/pixel) using the box visible in each camera's field of view.
- Reconstructs the 3D position of the tracked object at each timestamp by combining:
  - 2D position from Camera 1,
  - Estimated depth from Camera 2,
  - Intrinsic camera parameters (focal length, optical center),
  - Geometric assumptions based on the pinhole camera model.
- Saves the full 3D trajectory, including timestamps, to a CSV file.
- Visualizes the result using matplotlib:
  - 3D trajectory in world coordinates.
  - 2D projections from both camera views.
  - Object velocity over time, smoothed with a moving average filter.

Methods:
- __init__(csv_file_cam1, csv_file_cam2): Initializes the class with the paths to the two CSV files containing tracking data.
- load_mm_per_pixel_from_box(csv_path, real_width_mm, real_height_mm): Calculates scaling factors from calibration box CSV.
- camera_to_box_distance(L_real_mm, L_pixels, focal_length_px):Computes camera-to-object distance using pinhole camera geometry.
- reconstruct(): Reconstructs the 3D trajectory by converting 2D points and depth into world coordinates, then saves the 3D points to a CSV file.
- plot_trajectory(): Plots the 3D trajectory of the tracked object and visualizes the 2D projections from both cameras.
- plot_velocity():Displays a smoothed velocity graph based on 3D displacement over time.

Author: Stijn Kolkman (s.y.kolkman@student.utwente.nl)
Date: April 2025
"""

#GOOD TO KNOW: the coordinate system used for the 3D position of the tracked object is based on the coordinate system of camera 1

import cv2
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os

class TrajectoryReconstructor:
    def __init__(self, csv_file_cam1, csv_file_cam2):
        
        # Load the CSV files using pandas.
        self.csv_file_cam1 = csv_file_cam1
        self.csv_file_cam2 = csv_file_cam2
        self.output_dir = os.path.dirname(csv_file_cam1)
        base = os.path.basename(csv_file_cam1)
        self.base_name = base.replace("_cam1_locations.csv", "")
        self.data_cam1 = pd.read_csv(csv_file_cam1)
        self.data_cam2 = pd.read_csv(csv_file_cam2)
        
        # Extract X, Y coordinates
        self.x_cam1 = self.data_cam1['X'].to_numpy()
        self.y_cam1 = self.data_cam1['Y'].to_numpy()
        self.x_cam2 = self.data_cam2['X'].to_numpy() 
        self.y_cam2 = self.data_cam2['Y'].to_numpy()  
        self.timestamps = self.data_cam1['Time (seconds)'].to_numpy()  # Assuming timestamps are the same for both cameras

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

        #Compensate for the distortion
        points_cam1 = np.column_stack((self.x_cam1, self.y_cam1)).astype(np.float32)
        undistorted_cam1 = cv2.undistortPoints(points_cam1, self.camera_matrix1, self.dist_coeffs1, P=self.camera_matrix1)
        undistorted_cam1 = undistorted_cam1.reshape(-1, 2)
        self.x_cam1 = undistorted_cam1[:, 0]
        self.y_cam1 = undistorted_cam1[:, 1]

        points_cam2 = np.column_stack((self.x_cam2, self.y_cam2)).astype(np.float32)
        undistorted_cam2 = cv2.undistortPoints(points_cam2, self.camera_matrix2, self.dist_coeffs2, P=self.camera_matrix2)
        undistorted_cam2 = undistorted_cam2.reshape(-1, 2)
        self.x_cam2 = undistorted_cam2[:, 0]
        self.y_cam2 = undistorted_cam2[:, 1]

        # Initialize 3D points to None
        self.points_3d = None

        # Known physical dimensions of the box in mm (MILLIMETER!!!) (per view)
        self.real_box_width_cam1_mm = 108    # Width as seen from camera 1 (top/bottom view)
        self.real_box_height_cam1_mm = 56    # Height as seen from camera 1

        self.real_box_width_cam2_mm = 108     # Width as seen from camera 2 (side view)
        self.real_box_height_cam2_mm = 32    # Height as seen from camera 2 (used for Z)

        # Load box CSVs and compute mm-per-pixel scales
        box_file_cam1 = self.csv_file_cam1.replace("_locations.csv", "_box.csv")
        box_file_cam2 = self.csv_file_cam2.replace("_locations.csv", "_box.csv")
        (self.box_x_cam1, self.box_y_cam1, self.width_px_cam1,self.height_px_cam1, self.mm_per_pixel_x_cam1,self.mm_per_pixel_y_cam1) = self.load_mm_per_pixel_from_box(box_file_cam1, self.real_box_width_cam1_mm, self.real_box_height_cam1_mm)
        (self.box_x_cam2, self.box_y_cam2,self.width_px_cam2,self.height_px_cam2, self.mm_per_pixel_x_cam2,self.mm_per_pixel_y_cam2) = self.load_mm_per_pixel_from_box(box_file_cam2, self.real_box_width_cam2_mm, self.real_box_height_cam2_mm)

    def load_mm_per_pixel_from_box(self, csv_path, real_width_mm=None, real_height_mm=None):
        """
        Loads a box file and calculates mm-per-pixel scaling based on real-world dimensions.
        Returns (mm_per_pixel_x, mm_per_pixel_y)
        """
        if os.path.exists(csv_path):
            box_data = pd.read_csv(csv_path)
            width_px = float(box_data["Width"][0])
            height_px = float(box_data["Height"][0])
            x = float(box_data["X"][0])
            y = float(box_data["Y"][0])
            mm_per_pixel_x = real_width_mm / width_px if real_width_mm else 1.0
            mm_per_pixel_y = real_height_mm / height_px if real_height_mm else 1.0
            return x,y,width_px,height_px,mm_per_pixel_x, mm_per_pixel_y
        else:
            print(f"[Warning] Box file not found: {csv_path}")
            return 1.0, 1.0, 1.0, 1.0, 1.0, 1.0

    def camera_to_box_distance(self, L_real_mm, L_pixels, focal_length_px):
        L_real_m = L_real_mm / 1000.0
        D_camera_box =(focal_length_px * L_real_m) / L_pixels
        return D_camera_box
    
    def reconstruct(self):
        """Reconstructs the 3D trajectory using mm-per-pixel scaling based on known box dimensions."""
        # Get the focal lengths and the optical centers
        fx_cam1 = self.camera_matrix1[0,0]
        fy_cam1 = self.camera_matrix1[1,1]
        fx_cam2 = self.camera_matrix2[0,0]
        fy_cam2 = self.camera_matrix2[1,1]

        cx_cam1 = self.camera_matrix1[0, 2]
        cy_cam1 = self.camera_matrix1[1, 2]
        cy_cam2 = self.camera_matrix2[1, 2]

        # Initialize the distances and 3d location
        Z1 = np.zeros_like(self.x_cam1, dtype=np.float64)
        Z2 = np.zeros_like(self.x_cam1, dtype=np.float64)
        X_3d = np.zeros_like(self.x_cam1, dtype=np.float64)
        Y_3d = np.zeros_like(self.x_cam1, dtype=np.float64)
        Z_3d = np.zeros_like(self.x_cam1, dtype=np.float64)

        # Calculate the initial distance between the camera and the box
        cam1_to_box_distance = self.camera_to_box_distance(self.real_box_width_cam1_mm,self.width_px_cam1,fx_cam1)
        cam2_to_box_distance = self.camera_to_box_distance(self.real_box_width_cam2_mm,self.width_px_cam2,fx_cam2)
        print(f"The initial distance from camera 1 to the bottom of the box is: {cam1_to_box_distance}m")
        print(f"The initial distance from camera 2 to the nearest side of the box is: {cam2_to_box_distance}m")

        # Find the bottom of the box
        bottom_box_cam1 = self.box_y_cam1+self.height_px_cam1    
        bottom_box_cam2 = self.box_y_cam2+self.height_px_cam2

        # Use the position of the object and the bottom of the box to calculate the position in the box
        initial_y = (bottom_box_cam1-self.y_cam1[0])*(self.mm_per_pixel_y_cam1/1000)
        initial_z = (bottom_box_cam2-self.y_cam2[0])*(self.mm_per_pixel_y_cam2/1000)

        # Calculate the initial distance between the object and the camera's
        Z1[0] = cam1_to_box_distance + initial_z # Distance between object and camera1 at time=0
        Z2[0] = cam2_to_box_distance + initial_y # Distance between object and camera2 at time=0
        print(f"The initial distance from camera 1 to the object is: {Z1[0]}m")
        print(f"The initial distance from camera 2 to the object is: {Z2[0]}m")

        # Loop to calculate the 3d position and update the distances per timestep
        for i, value in enumerate(self.x_cam1):
            X_3d[i] = (self.x_cam1[i] - cx_cam1)*Z1[i]/fx_cam1
            Y_3d[i] = (self.y_cam1[i] - cy_cam1)*Z1[i]/fy_cam1
            Z_3d[i] = -(self.y_cam2[i] - cy_cam2)*Z2[i]/fy_cam2
            if i < len(self.x_cam1) - 1:
                # Adjust future depth estimates based on movement in Y and Z,
                # this is assuming smooth motion and small displacements
                Z1[i+1] = Z1[0]+(Z_3d[i] - Z_3d[0])
                Z2[i+1] = Z2[0]-(Y_3d[i] - Y_3d[0])

        # Make the first position 0,0,0
        X_3d -= X_3d[0]
        Y_3d -= Y_3d[0]
        Z_3d -= Z_3d[0]

        # Convert to millimeter
        X_3d *= 1000
        Z_3d *= 1000
        Y_3d *= 1000

        # Stack the coordinates into a 3D array (X, Y, Z)
        self.points_3d = np.vstack((X_3d, Y_3d, Z_3d))

        # Save the 3D points with timestamps into a DataFrame
        self.points_with_timestamp = pd.DataFrame({
            'Time': self.timestamps,
            'X': X_3d,
            'Y': Y_3d,
            'Z': Z_3d
        })

        # Generate the output file name based on the input file name
        output_file_name = os.path.basename(self.csv_file_cam1)
        output_file_path = os.path.join(self.output_dir, f"{self.base_name}_Trajectory.csv")

        # Save the DataFrame to CSV
        self.points_with_timestamp.to_csv(output_file_path, index=False)

        # Compute velocities in mm/s
        dt = np.diff(self.timestamps)  # Time difference between frames
        dx = np.diff(self.points_3d[0])  # ΔX
        dy = np.diff(self.points_3d[1])  # ΔY
        dz = np.diff(self.points_3d[2])  # ΔZ
        velocities = np.sqrt(dx**2 + dy**2 + dz**2) / dt

        # Save for plotting later (and also filter the velocity with a moving average filter)
        window_size_moving_average = 50
        self.velocities = np.convolve(velocities, np.ones(window_size_moving_average)/window_size_moving_average, mode='valid')
        self.velocity_timestamps_initial = self.timestamps[1:] 
        self.velocity_timestamps=self.velocity_timestamps_initial[window_size_moving_average - 1:]  # adjust time axis

        return self.points_with_timestamp

    def plot_trajectory(self):
        if self.points_3d is None:
            print("No 3D points to plot. Call 'reconstruct()' first.")
            return

        # Extract 3D coordinates
        x_coords = self.points_3d[0, :]
        y_coords = self.points_3d[1, :]
        z_coords = self.points_3d[2, :]

        # Create figure with 3 subplots: 3D and two 2D plots
        fig = plt.figure(figsize=(15, 5))

        # Plot 3D trajectory
        ax_3d = fig.add_subplot(131, projection='3d')
        #ax_3d.scatter(x_coords, y_coords, z_coords, color='r', marker='o', s=50)
        ax_3d.plot(x_coords, y_coords, z_coords, color='b', linestyle='-', linewidth=2)
        ax_3d.set_title("Trajectory")
        ax_3d.set_xlabel("X (mm)")
        ax_3d.set_ylabel("Y (mm)")
        ax_3d.set_zlabel("Z (mm)")

        # Get the limits for each axis
        x_limits = ax_3d.get_xlim()
        y_limits = ax_3d.get_ylim()
        z_limits = ax_3d.get_zlim()

        # Find the largest range among the axes
        max_range = max(
            x_limits[1] - x_limits[0], 
            y_limits[1] - y_limits[0], 
            z_limits[1] - z_limits[0]
        )

        # Set the same range for all axes
        ax_3d.set_xlim([x_limits[0], x_limits[0] + max_range])
        ax_3d.set_ylim([y_limits[0], y_limits[0] + max_range])
        ax_3d.set_zlim([z_limits[0], z_limits[0] + max_range])
        ax_3d.view_init(elev=30, azim=+90)

        # Camera resolution
        cam_width, cam_height = 1920, 1080

        # Plot Camera 1 (X,Y)
        ax_cam1 = fig.add_subplot(132)
        ax_cam1.scatter(self.x_cam1, self.y_cam1, color='g', marker='x')
        ax_cam1.plot(self.x_cam1, self.y_cam1, color='g', linestyle='--')
        ax_cam1.set_title("Camera 1 Tracked Points")
        ax_cam1.set_xlabel("X (pixels)")
        ax_cam1.set_ylabel("Y (pixels)")
        ax_cam1.set_xlim(0, cam_width)
        ax_cam1.set_ylim(cam_height, 0)

        # Plot Camera 2 (X,Z)
        ax_cam2 = fig.add_subplot(133)
        ax_cam2.scatter(self.x_cam2, self.y_cam2, color='m', marker='x')
        ax_cam2.plot(self.x_cam2, self.y_cam2, color='m', linestyle='--')
        ax_cam2.set_title("Camera 2 Tracked Points (X vs Z)")
        ax_cam2.set_xlabel("X (pixels)")
        ax_cam2.set_ylabel("Z (pixels)")
        ax_cam2.set_xlim(0, cam_width)
        ax_cam2.set_ylim(cam_height, 0)

        plt.tight_layout()
        plt.show()

    def plot_velocity(self):
        if not hasattr(self, 'velocities'):
            print("Velocity not computed. Run 'reconstruct()' first.")
            return

        plt.figure(figsize=(8, 4))
        plt.plot(self.velocity_timestamps, self.velocities, color='orange', linewidth=2)
        plt.title("Object Velocity Over Time")
        plt.xlabel("Time (s)")
        plt.ylabel("Velocity (mm/s)")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

# # Used when this class is run seperately 
if __name__ == "__main__":
    # update names if needed
    csv_file_cam1 = r"C:\Users\stijn\OneDrive - University of Twente\Afstuderen\script\Setup\Main\Measurement0105\Recording_cam1_locations.csv"
    csv_file_cam2 = r"C:\Users\stijn\OneDrive - University of Twente\Afstuderen\script\Setup\Main\Measurement0105\Recording_cam2_locations.csv"
    traj_reconstructor = TrajectoryReconstructor(csv_file_cam1, csv_file_cam2)
    traj_reconstructor.reconstruct()
    traj_reconstructor.plot_trajectory()
    traj_reconstructor.plot_velocity()