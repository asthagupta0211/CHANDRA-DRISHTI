import io
import base64
import torch
import numpy as np
import cv2
from PIL import Image
from flask import Flask, request, jsonify
from flask_cors import CORS
from torchvision.models.detection import fasterrcnn_mobilenet_v3_large_fpn, faster_rcnn
from torchvision.transforms import functional as F

app = Flask(__name__)
CORS(app)

# --- CONSTANTS ---
CLASSES = ['background', 'crater']
NUM_CLASSES = 2
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'trained_model.pth')

# Global model instance
model = None

def load_model():
    global model
    if model is None:
        print("Loading AI Model...")
        model = fasterrcnn_mobilenet_v3_large_fpn(weights=None)
        in_features = model.roi_heads.box_predictor.cls_score.in_features
        model.roi_heads.box_predictor = faster_rcnn.FastRCNNPredictor(in_features, NUM_CLASSES)
        
        try:
            state_dict = torch.load(MODEL_PATH, map_location=torch.device('cpu'))
            model.load_state_dict(state_dict)
        except RuntimeError as e:
            model.load_state_dict(state_dict, strict=False)
            
        model.eval()
        print("Model loaded successfully.")

# Load model on startup
load_model()

# --- PROCESSING FUNCTIONS ---
def draw_boxes(image_np, boxes, labels, scores, threshold=0.3, scale=1):
    img = image_np.copy()
    for box, label, score in zip(boxes, labels, scores):
        if score > threshold:
            xmin, ymin, xmax, ymax = map(lambda v: int(v * scale), box)
            class_name = CLASSES[label] if label < len(CLASSES) else f'Class {label}'
            
            color = (0, 255, 0) if class_name == 'crater' else (0, 0, 255)
            # Scale text size and thickness based on resolution
            thickness = 2 if scale == 1 else 3
            font_scale = 0.5 if scale == 1 else 1.0
            
            cv2.rectangle(img, (xmin, ymin), (xmax, ymax), color, thickness)
            cv2.putText(img, f'{class_name}: {score:.2f}', (xmin, ymin - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
    return img

def apply_super_resolution(image, scale=5):
    """Upscale image 5x using Lanczos4 and Unsharp Masking (Algorithmic Super Resolution)."""
    h, w = image.shape[:2]
    new_w, new_h = w * scale, h * scale
    upscaled = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    # Unsharp mask for edge recovery
    gaussian = cv2.GaussianBlur(upscaled, (0, 0), 2.0)
    super_resolved = cv2.addWeighted(upscaled, 1.5, gaussian, -0.5, 0)
    return super_resolved

def preprocess_dem(dem):
    max_val = np.max(dem)
    if max_val == 0:
        return np.zeros_like(dem, dtype=np.uint8)
    normalized_dem = dem / max_val
    scaled_dem = (normalized_dem * 255).astype(np.uint8)
    return scaled_dem

def identify_slopes(dem, slope_threshold=10):
    # Blur to reduce optical texture noise if this is a standard image fallback
    blurred = cv2.GaussianBlur(dem, (5, 5), 0)
    gradient_x = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3)
    gradient_y = cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = np.sqrt(gradient_x**2 + gradient_y**2)
    angle = np.arctan2(gradient_y, gradient_x) * (180 / np.pi)

    steep_slope_mask = np.zeros_like(dem)
    # Must have both steep angle AND a significant gradient magnitude
    steep_slope_mask[(np.abs(angle) > slope_threshold) & (magnitude > 20)] = 255
    return steep_slope_mask

def detect_shadows(image, threshold_value=150):
    # Cap the threshold at the 5th percentile of brightness to prevent 100% shadow flags on optical images
    p5 = np.percentile(image, 5)
    effective_thresh = min(threshold_value, p5)
    _, thresh = cv2.threshold(image, effective_thresh, 255, cv2.THRESH_BINARY)
    return thresh

def image_to_base64(img_np):
    """Convert numpy RGB or BGR image to base64 jpeg string"""
    # Convert RGB to BGR for cv2 if it's a 3 channel image and came from PIL
    if len(img_np.shape) == 3 and img_np.shape[2] == 3:
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    else:
        img_bgr = img_np
    _, buffer = cv2.imencode('.jpg', img_bgr)
    b64_str = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{b64_str}"

import os
import random

@app.route('/random_sample', methods=['GET'])
def random_sample():
    try:
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'lunar_coco', 'test')
        if not os.path.exists(data_dir):
            return jsonify({"success": False, "error": "Sample data directory not found"}), 404
            
        images = [f for f in os.listdir(data_dir) if f.endswith('.jpg') or f.endswith('.png')]
        if not images:
            return jsonify({"success": False, "error": "No images found in sample data"}), 404
            
        random_img = random.choice(images)
        img_path = os.path.join(data_dir, random_img)
        
        with open(img_path, "rb") as f:
            b64_str = base64.b64encode(f.read()).decode('utf-8')
            
        ext = 'jpeg' if random_img.endswith('.jpg') else 'png'
        return jsonify({
            "success": True,
            "filename": random_img,
            "data": f"data:image/{ext};base64,{b64_str}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Get threshold values from form
        confidence_thresh = float(request.form.get('confidence_threshold', 0.3))
        slope_thresh = float(request.form.get('slope_threshold', 10.0))
        shadow_thresh = float(request.form.get('shadow_threshold', 150.0))
        use_sr = request.form.get('use_sr', 'false') == 'true'
        
        SR_SCALE = 5 if use_sr else 1

        results = {}
        
        has_objects, has_slopes, has_shadows = False, False, False
        result_img = None
        slope_mask = None
        shadow_mask = None

        # 1. Process Standard Image for Craters
        if 'standard_image' in request.files and request.files['standard_image'].filename != '':
            file = request.files['standard_image']
            image = Image.open(file.stream).convert("RGB")
            image_np = np.array(image)
            
            img_tensor = F.to_tensor(image).unsqueeze(0)
            with torch.no_grad():
                predictions = model(img_tensor)[0]
            
            boxes = predictions['boxes'].cpu().numpy()
            labels = predictions['labels'].cpu().numpy()
            scores = predictions['scores'].cpu().numpy()
            
            # If SR is enabled, upscale the base image BEFORE drawing scaled boxes
            display_img = apply_super_resolution(image_np, scale=SR_SCALE) if use_sr else image_np
            
            result_img = draw_boxes(display_img, boxes, labels, scores, threshold=confidence_thresh, scale=SR_SCALE)
            results['object_detection'] = image_to_base64(result_img)
            
            valid_detections = scores > confidence_thresh
            results['num_hazards'] = int(np.sum(valid_detections))
            has_objects = True

        # 2. Process DEM Image for Slopes
        dem_file = request.files.get('dem_image')
        if not dem_file or dem_file.filename == '':
            dem_file = request.files.get('standard_image')
            
        if dem_file and dem_file.filename != '':
            dem_file.stream.seek(0)
            dem_pil = Image.open(dem_file.stream)
            dem_array = np.array(dem_pil)
            if len(dem_array.shape) > 2:
                dem_array = dem_array[:,:,0] # Take first channel if multi
            
            if use_sr:
                print("Applying 5x Super Resolution to DEM for 1m Grid Spacing...")
                dem_array = apply_super_resolution(dem_array, scale=SR_SCALE)
                
            preprocessed_dem = preprocess_dem(dem_array)
            slope_mask = identify_slopes(preprocessed_dem, slope_threshold=slope_thresh)
            results['slope_map'] = image_to_base64(slope_mask)
            has_slopes = True

        # 3. Process ORTHO Image for Shadows
        ortho_file = request.files.get('ortho_image')
        if not ortho_file or ortho_file.filename == '':
            ortho_file = request.files.get('standard_image')

        if ortho_file and ortho_file.filename != '':
            ortho_file.stream.seek(0)
            orth_pil = Image.open(ortho_file.stream)
            orth_array = np.array(orth_pil)
            if len(orth_array.shape) > 2:
                orth_array = orth_array[:,:,0]
                
            if orth_array.dtype != np.uint8:
                orth_max = np.max(orth_array)
                if orth_max == 0:
                    orth_array = np.zeros_like(orth_array, dtype=np.uint8)
                else:
                    normalized_orth = orth_array / orth_max
                    orth_array = (normalized_orth * 255).astype(np.uint8)
            
            if use_sr:
                print("Applying 5x Super Resolution to Orthophoto for 1m Grid Spacing...")
                orth_array = apply_super_resolution(orth_array, scale=SR_SCALE)
                
            shadow_mask = detect_shadows(orth_array, threshold_value=shadow_thresh)
            results['shadow_map'] = image_to_base64(shadow_mask)
            has_shadows = True

        # 4. Generate Master Combined Map & Safe Landing Zone
        if has_objects or has_slopes or has_shadows:
            base_h, base_w = 600, 600
            if has_objects:
                master_img = result_img.copy()
                base_h, base_w = master_img.shape[:2]
            else:
                if has_shadows:
                    base_h, base_w = shadow_mask.shape[:2]
                elif has_slopes:
                    base_h, base_w = slope_mask.shape[:2]
                master_img = np.zeros((base_h, base_w, 3), dtype=np.uint8)

            # Create an empty hazard mask for the safe landing algorithm
            hazard_mask = np.zeros((base_h, base_w), dtype=np.uint8)

            if has_objects:
                # Add crater bounding boxes to hazard mask
                for box, score in zip(boxes, scores):
                    if score > confidence_thresh:
                        xmin, ymin, xmax, ymax = map(int, box)
                        cv2.rectangle(hazard_mask, (xmin, ymin), (xmax, ymax), 255, -1)

            if has_slopes:
                resized_slope = cv2.resize(slope_mask, (base_w, base_h))
                red_overlay = np.zeros_like(master_img)
                red_overlay[resized_slope == 255] = [255, 0, 0]
                master_img = cv2.addWeighted(master_img, 1.0, red_overlay, 0.5, 0)
                
                # Add to hazard mask
                hazard_mask = cv2.bitwise_or(hazard_mask, resized_slope)
                
            if has_shadows:
                resized_shadow = cv2.resize(shadow_mask, (base_w, base_h))
                blue_overlay = np.zeros_like(master_img)
                blue_overlay[resized_shadow == 0] = [0, 0, 255]
                master_img = cv2.addWeighted(master_img, 1.0, blue_overlay, 0.5, 0)
                
                # Add to hazard mask (shadows are 0 in resized_shadow, so we invert)
                shadow_hazard = cv2.bitwise_not(resized_shadow)
                hazard_mask = cv2.bitwise_or(hazard_mask, shadow_hazard)

            # --- Safe Landing Zone Algorithm ---
            # Invert hazard mask to get safe areas (safe = 255, hazard = 0)
            safe_mask = cv2.bitwise_not(hazard_mask)
            
            # Calculate safe percentage
            total_pixels = base_w * base_h
            safe_pixels = cv2.countNonZero(safe_mask)
            safe_percentage = round((safe_pixels / total_pixels) * 100, 1)

            # Compute Euclidean distance transform
            dist_transform = cv2.distanceTransform(safe_mask, cv2.DIST_L2, 5)
            
            # Find the point with maximum distance (the center of the largest safe circle)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(dist_transform)
            
            # A lander needs a minimum physical space to land safely. 
            # We use a forgiving threshold (5px radius on base, multiplied by SR_SCALE for 1m grid).
            MIN_SAFE_RADIUS = 5 * SR_SCALE

            # Always return safe_percentage and alt_zones array
            results['landing_zone'] = {
                'safe_percentage': safe_percentage,
                'alt_zones': []
            }

            if max_val >= MIN_SAFE_RADIUS and safe_percentage >= 75.0: 
                radius = int(max_val)
                center = max_loc
                
                # Draw the primary landing zone circle (Glowing Green)
                cv2.circle(master_img, center, radius, (0, 255, 0), 2)
                # Draw a crosshair
                cv2.drawMarker(master_img, center, (0, 255, 0), markerType=cv2.MARKER_CROSS, markerSize=20, thickness=2)
                
                results['landing_zone']['x'] = center[0]
                results['landing_zone']['y'] = center[1]
                results['landing_zone']['radius'] = radius

                # ROVER PATHFINDING TO NEAREST CRATER
                if has_objects and len(boxes) > 0:
                    nearest_crater = None
                    min_dist = float('inf')

                    # Iterate over all valid detected craters
                    for box, score in zip(boxes, scores):
                        if score > confidence_thresh:
                            xmin, ymin, xmax, ymax = map(lambda v: int(v * SR_SCALE), box)
                            
                            # Find the closest point on the bounding box to the landing zone
                            closest_x = max(xmin, min(center[0], xmax))
                            closest_y = max(ymin, min(center[1], ymax))
                            
                            dist = np.sqrt((center[0] - closest_x)**2 + (center[1] - closest_y)**2)
                            if dist < min_dist:
                                min_dist = dist
                                nearest_crater = (closest_x, closest_y)
                    
                    if nearest_crater is not None:
                        # Draw stylized trajectory (Cyan Line)
                        color = (255, 255, 0) # Cyan in BGR
                        thickness = max(1, 2 * SR_SCALE)
                        
                        # Calculate distance in meters (1 pixel = 1m in SR, or 5m in standard)
                        physical_dist_meters = round(min_dist * (1 if use_sr else 5), 1)
                        results['landing_zone']['rover_path'] = {
                            'target_x': nearest_crater[0],
                            'target_y': nearest_crater[1],
                            'distance_meters': physical_dist_meters
                        }
                        
                        # Draw a dotted line by sampling points
                        line_length = int(np.sqrt((center[0]-nearest_crater[0])**2 + (center[1]-nearest_crater[1])**2))
                        num_segments = max(5, line_length // (15 * SR_SCALE))
                        
                        for i in range(num_segments):
                            if i % 2 == 0: # Only draw every other segment
                                pt1 = (
                                    int(center[0] + (nearest_crater[0] - center[0]) * (i / num_segments)),
                                    int(center[1] + (nearest_crater[1] - center[1]) * (i / num_segments))
                                )
                                pt2 = (
                                    int(center[0] + (nearest_crater[0] - center[0]) * ((i+1) / num_segments)),
                                    int(center[1] + (nearest_crater[1] - center[1]) * ((i+1) / num_segments))
                                )
                                cv2.line(master_img, pt1, pt2, color, thickness)
                        
                        # Draw a target marker at the crater edge
                        cv2.circle(master_img, nearest_crater, 5 * SR_SCALE, color, -1)
                        cv2.circle(master_img, nearest_crater, 8 * SR_SCALE, color, 2)
            else:
                # ABORT STATE: Either no primary zone found, or safety < 75%
                # Find the top 3 "sub-optimal" or contingency zones
                working_dist = dist_transform.copy()
                for i in range(3):
                    alt_min_val, alt_max_val, alt_min_loc, alt_max_loc = cv2.minMaxLoc(working_dist)
                    
                    if alt_max_val > 0: # As long as it is somewhat safe
                        alt_radius = int(alt_max_val)
                        alt_center = alt_max_loc
                        
                        # Draw alternative zone in Yellow/Orange
                        cv2.circle(master_img, alt_center, alt_radius, (0, 165, 255), 2)
                        cv2.circle(master_img, alt_center, 2, (0, 165, 255), -1)
                        
                        results['landing_zone']['alt_zones'].append({
                            'x': alt_center[0],
                            'y': alt_center[1],
                            'radius': alt_radius
                        })
                        
                        # Clear it out so we find the next biggest
                        cv2.circle(working_dist, alt_center, alt_radius * 2 + 5, 0, -1)
                    else:
                        break
            # -----------------------------------
                
            results['master_map'] = image_to_base64(master_img)

        return jsonify({"success": True, "data": results})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    # Listen on 0.0.0.0 so that mobile phones on the same Wi-Fi can connect
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', debug=False, port=port)
