"""
VideoTracker Class

This class tracks an object in a video file by selecting a Region of Interest (ROI) and using contour-based 
tracking (with Otsu's thresholding) to track the object across frames. The object's position, orientation, 
and timestamp are recorded and saved to a CSV file. The user can manually select the physical box (environment 
container) in the first frame, which is saved separately for later use in world scaling. The class supports 
interactive ROI re-selection during tracking.

Main Workflow:
- A video file is loaded, and the user first selects the physical box (for world scaling) and then the object ROI.
- A contour-based tracking method (using Otsu's thresholding) is used to track the selected object across the video frames.
- The position (X, Y), orientation angle, and timestamp of the object are recorded and saved to a CSV file.
- The selected physical box (X, Y, Width, Height) is saved separately in a CSV file for use in world scaling.
- An annotated video showing the tracked object, its center, and orientation is saved as a new video file.

Methods:
- __init__(video_path): Initializes the VideoTracker object with the path to the video file and sets up necessary attributes.
- select_roi(): Lets the user select a region of interest (ROI) in the first frame for tracking.
- select_and_save_box(): Allows manual selection of the full environment box in the first frame and saves its dimensions to CSV.
- update_roi_center(frame, roi): Updates the position of the ROI based on the largest contour found in the thresholded region.
- track_and_save(): Tracks the selected object, saves the tracking data to a CSV file, allows interactive ROI re-selection, 
  and outputs an annotated video.

Author: Stijn Kolkman (s.y.kolkman@student.utwente.nl)
Date: April 2025
"""

import cv2
import numpy as np
import csv
import os
import re

class VideoTracker:
    def __init__(self, video_path):
        # Load the video using the video_path
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise IOError("Cannot open the video file.")
        
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        #base_filename = os.path.splitext(os.path.basename(video_path))[0]

        # New: Folder and base name
        self.output_dir = os.path.dirname(video_path)
        self.base_name = os.path.basename(video_path).replace(".avi", "").replace(".avi", "")
        self.csv_filename = os.path.join(self.output_dir, f"{self.base_name}_locations.csv")
        self.output_video_filename = os.path.join(self.output_dir, f"{self.base_name}_tracking.avi")
        self.out_video = None  # This will be the VideoWriter object for saving the tracked video

        # Load the timestamps
        self.base_name_timestamp = re.sub(r'_cam\d\.avi$', '', os.path.basename(video_path))
        timestamp_file = os.path.join(self.output_dir, f"{self.base_name_timestamp}_timestamps.csv")
        self.timestamps = []

        if os.path.exists(timestamp_file):
            with open(timestamp_file, newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.timestamps.append(float(row["Timestamp (s)"]))
            print(f"[INFO] Loaded {len(self.timestamps)} timestamps from {timestamp_file}")
        else:
            print(f"[WARNING] Timestamp file not found: {timestamp_file}")
    """
    def preprocess_frame(self, frame):
        #Applies preprocessing to enhance contrast and reduce noise.

        # Convert to LAB color space for CLAHE
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE to the L-channel
        clahe = cv2.createCLAHE(clipLimit=1.0, tileGridSize=(20, 20))
        cl = clahe.apply(l)

        # Merge channels back and convert to BGR
        lab = cv2.merge((cl, a, b))
        frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # Mild Gaussian blur to reduce noise
        frame = cv2.GaussianBlur(frame, (5, 5), 0)
        return frame
    """
    def select_roi(self):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = self.cap.read()
        if not ret:
            print("Cannot read from the video.")
            self.cap.release()
            cv2.destroyAllWindows()
            raise RuntimeError("Video reading error.")

        roi = cv2.selectROI("Select the ROI", frame, fromCenter=False, showCrosshair=True)
        cv2.destroyWindow("Select the ROI")
        return frame, roi

    def select_and_save_box(self):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Go to the first frame
        ret, frame = self.cap.read()
        if not ret:
            print("Cannot read from the video.")
            self.cap.release()
            cv2.destroyAllWindows()
            raise RuntimeError("Video reading error during box selection.")

        print("Select the FULL box/container used for world scale reference")
        box_roi = cv2.selectROI("Select the Box", frame, fromCenter=False, showCrosshair=True)
        cv2.destroyWindow("Select the Box")

        box_csv_name = os.path.join(self.output_dir, f"{self.base_name}_box.csv")
        with open(box_csv_name, mode='w', newline='') as box_file:
            writer = csv.writer(box_file)
            writer.writerow(["X", "Y", "Width", "Height"])
            writer.writerow(box_roi)

        print(f"Box region saved to: {box_csv_name}")

    def update_roi_center(self, frame, roi):
            # Crop the ROI from the frame
            x, y, w, h = [int(v) for v in roi]

            # Ensure that the ROI coordinates are within the frame's dimensions
            height, width = frame.shape[:2]
            if x + w > width:
                w = width - x
            if y + h > height:
                h = height - y

            roi_frame = frame[y:y+h, x:x+w]

            # Convert to grayscale and apply Otsu's thresholding
            gray_roi = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
            _, threshold = cv2.threshold(gray_roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            # Debug: Show the thresholded image
            cv2.imshow("Thresholded Image", threshold)

            # Add a short delay to give you time to inspect the thresholded image
            #time.sleep(3)  # Adjust the time as needed (0.5 sec for example)

            # Find contours in the thresholded image
            contours, _ = cv2.findContours(threshold, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                # Get the largest contour by area
                largest_contour = max(contours, key=cv2.contourArea)

                # Get the bounding box of the largest contour
                #x_contour, y_contour, w_contour, h_contour = cv2.boundingRect(largest_contour)
                rect = cv2.minAreaRect(largest_contour)
                box = cv2.boxPoints(rect)
                box = np.int32(box)

                # Compute the object's center (account for ROI offset)
                center_x_, center_y_ = rect[0]
                center_x_ += x
                center_y_ += y
                center_x_, center_y_ = int(center_x_), int(center_y_)
                angle = rect[2]

                # Update the ROI center based on the object's new center
                # Keep the original size (w, h) but adjust its position
                new_x = center_x_ - w // 2
                new_y = center_y_ - h // 2

                # Ensure the new ROI is within the bounds of the frame
                new_x = max(new_x, 0)
                new_y = max(new_y, 0)

                # Ensure the ROI does not go out of bounds
                if new_x + w > width:
                    new_x = width - w
                if new_y + h > height:
                    new_y = height - h

                # Update the ROI
                roi = (new_x, new_y, w, h)

                # Draw the contour and center on the frame for debugging
                cv2.circle(frame, (center_x_, center_y_), 5, (0, 0, 255), -1)
                # Adjust drawn contours by the top-left ROI offset (x, y)
                cv2.drawContours(frame, [box + (x, y)], 0, (0, 0, 255), 2)
                cv2.putText(frame, f"Orientation: {angle:.2f} deg", (x, y - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                print("No contours found.")

            return frame, roi

    def track_and_save(self):
            # Manually select box 
            self.select_and_save_box()

            # Select ROI and initialize variables
            frame, roi = self.select_roi()

            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.out_video = cv2.VideoWriter(self.output_video_filename, fourcc, self.fps, (frame.shape[1], frame.shape[0]))

            with open(self.csv_filename, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Time (seconds)", "X", "Y", "angle (degrees)"])

                frame_number = 0
                while True:
                    ret, frame = self.cap.read()
                    if not ret:
                        break

                    if frame_number < len(self.timestamps):
                        time_seconds = self.timestamps[frame_number]
                    else:
                        raise IndexError(f"No timestamp for frame {frame_number}")

                    # Update ROI based on object position
                    frame, roi = self.update_roi_center(frame, roi)

                    # Get center of the updated ROI
                    x, y, w, h = [int(v) for v in roi]
                    center_x = x + w // 2
                    center_y = y + h // 2
                    #print(center_x)
                    #print(center_y)
                    # Calculate the orientation (assuming square ROI, otherwise, use angle of bounding box)
                    angle = 0  # We can skip angle computation for this simple case

                    # Write data to CSV
                    writer.writerow([time_seconds, center_x, center_y, angle])

                    # Write the frame to the output video
                    self.out_video.write(frame)

                    # Display the frame
                    cv2.imshow("Tracking", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

                    frame_number += 1

            self.cap.release()
            self.out_video.release()
            cv2.destroyAllWindows()
            print(f"Tracking data saved to {self.csv_filename}")
            print(f"Tracking video saved to {self.output_video_filename}")

# Used when this class is run seperately 
if __name__ == "__main__":
    video_file = r'C:\Users\stijn\OneDrive - University of Twente\Afstuderen\script\Setup\Main\Measurement0105\Recording_cam1.avi'
    tracker = VideoTracker(video_file)
    tracker.track_and_save()
