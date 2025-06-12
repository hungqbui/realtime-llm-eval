# Load model directly
from transformers import AutoImageProcessor, AutoModelForImageClassification
import torch
# from deepface import DeepFace
import numpy as np
# import tensorflow as tf

# Initialize processor and model once at module level
device = "cuda" if torch.cuda.is_available() else "cpu"
processor = AutoImageProcessor.from_pretrained("dima806/facial_emotions_image_detection", use_fast=True)
model = AutoModelForImageClassification.from_pretrained("dima806/facial_emotions_image_detection")

def top_k(arr, k=3):
    """Return the top k elements and their indices from a numpy array."""
    import heapq

    heap = []

    for i, p in enumerate(arr):
        heapq.heappush(heap, (p, i))
        if len(heap) > k:
            heapq.heappop(heap)

    return sorted(heap, key=lambda x: x[0], reverse=True)

def predict(image):
    """Return a classification result for a given image from the webcam image"""
    try:
        inputs = processor(images=image, return_tensors="pt")

        with torch.no_grad():
            logits = model(**inputs, return_dict=True).logits

        top = top_k(logits.softmax(dim=1).squeeze().cpu().numpy(), k=3)

        top = [(prob.item(), model.config.id2label[idx]) for prob, idx in top]

    except Exception as e:
        print(f"Error during prediction: {e}")
        return "Error during prediction"

    return top

# def predict(image):
#     """Return a classification result for a given image from the webcam image"""
    
#     objs = DeepFace.analyze(np.array(image), actions=['emotion'], enforce_detection=False, detector_backend='mediapipe')

#     if objs:
#         emotions = objs[0]["emotion"]
#         formatted = [(prob, emotion) for emotion, prob in emotions.items()]

#         top_3 = sorted(formatted, key=lambda x: x[0], reverse=True)[:3]
#         return [(prob.item(), emotion) for prob, emotion in top_3]  # Filter out low probabilities
#     else:
#         return "NONE"
