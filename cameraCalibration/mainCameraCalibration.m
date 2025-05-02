clear;
close all;
clc;

%% Camera 1
% Define image directory for Camera 1
imageDir = 'cameraCalibration/Cam2Bottom';
images = imageDatastore(imageDir);

% Detect checkerboard corners
[imagePoints, boardSize, imagesUsed] = detectCheckerboardPoints(images.Files);

% Define the actual size of checkerboard squares (e.g., 25 mm)
squareSize = 9.2;  % in millimeters (adjust this to your board size)

worldPoints = patternWorldPoints('checkerboard',boardSize,squareSize);

% Get the model parameters
I = readimage(images,1); 
imageSize = [size(I,1),size(I,2)];
params = estimateCameraParameters(imagePoints,worldPoints,ImageSize=imageSize);
[intrinsicMatrix_cam1,distortionCoefficients_cam1] = cameraIntrinsicsToOpenCV(params);

% Check calibration accuracy
figure; showReprojectionErrors(params);
figure; showExtrinsics(params, 'CameraCentric');

%%
% Define image directory for Camera 2
imageDir2 = 'calibration_images';
images2 = imageDatastore(imageDir);

% Detect checkerboard corners
[imagePoints2, boardSize2, imagesUsed2] = detectCheckerboardPoints(images2.Files);

% Define the actual size of checkerboard squares (e.g., 25 mm)
squareSize = 9.2;  % in millimeters (adjust this to your board size)

worldPoints = patternWorldPoints('checkerboard',boardSize2,squareSize2);

% Get the model parameters
I = readimage(images2,1); 
imageSize2 = [size(I,1),size(I,2)];
params = estimateCameraParameters(imagePoints2,worldPoints2,ImageSize=imageSize2);
[intrinsicMatrix_cam2,distortionCoefficients_cam2] = cameraIntrinsicsToOpenCV(params2);

% Check calibration accuracy
figure; showReprojectionErrors(cameraParams2);
figure; showExtrinsics(cameraParams2, 'CameraCentric');