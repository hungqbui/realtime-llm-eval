# Load model directly
from transformers import AutoImageProcessor, AutoModelForImageClassification

processor = AutoImageProcessor.from_pretrained("mo-thecreator/vit-Facial-Expression-Recognition")
model = AutoModelForImageClassification.from_pretrained("mo-thecreator/vit-Facial-Expression-Recognition")

