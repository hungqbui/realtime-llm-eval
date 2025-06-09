# Load model directly
from transformers import AutoImageProcessor, ViTForImageClassification
import torch

# Initialize processor and model once at module level
device = "cuda" if torch.cuda.is_available() else "cpu"
processor = AutoImageProcessor.from_pretrained("mo-thecreator/vit-Facial-Expression-Recognition", use_fast=True)
model = ViTForImageClassification.from_pretrained("mo-thecreator/vit-Facial-Expression-Recognition")

def predict(image):
    try:
        inputs = processor(images=image, return_tensors="pt")

        with torch.no_grad():
            logits = model(**inputs, return_dict=True).logits

        predicted_class_idx = logits.argmax(dim=1).item()
        max_prob = logits.softmax(dim=1).max().item()
    except Exception as e:
        print(f"Error during prediction: {e}")
        return "Error during prediction"

    return model.config.id2label[predicted_class_idx], max_prob
