# Load model directly
from transformers import AutoImageProcessor, ViTForImageClassification
import torch

def predict(image):
    processor = AutoImageProcessor.from_pretrained("mo-thecreator/vit-Facial-Expression-Recognition")
    model = ViTForImageClassification.from_pretrained("mo-thecreator/vit-Facial-Expression-Recognition").to("cuda" if torch.cuda.is_available() else "cpu")
    inputs = processor(images=image, return_tensors="pt")

    with torch.no_grad():
        logits = model(**inputs, return_dict=True).logits

    predicted_class_idx = logits.argmax(dim=1).item()

    return model.config.id2label[predicted_class_idx]
