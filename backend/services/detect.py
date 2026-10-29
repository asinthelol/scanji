"""
Speech bubble text detection.
"""
from PIL import Image

from ..config import DETECTOR_REPO
from .reading_order import reading_order

_detector = None

PAD_PX = 4  # small margin around detected text; manga-ocr reads better with some


def get_detector():
    global _detector
    if _detector is None:
        from transformers import AutoImageProcessor, RTDetrV2ForObjectDetection

        processor = AutoImageProcessor.from_pretrained(DETECTOR_REPO)
        model = RTDetrV2ForObjectDetection.from_pretrained(DETECTOR_REPO).eval()
        _detector = (processor, model)
    return _detector


def detect_text(img: Image.Image, threshold: float = 0.5, include_free: bool = False) -> list[dict]:
    """
    Detects text regions in pixels, in reading order.

    Uses the model's text_bubble class (tight text inside bubbles). text_free (SFX, captions,
    page furniture) is opt-in because it also picks up a lot of non-dialogue text.
    """
    import torch

    processor, model = get_detector()
    inputs = processor(images=img, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    result = processor.post_process_object_detection(
        outputs, target_sizes=torch.tensor([img.size[::-1]]), threshold=threshold
    )[0]

    wanted = {"text_bubble"} | ({"text_free"} if include_free else set())
    found = []
    for score, label, box in zip(result["scores"], result["labels"], result["boxes"]):
        kind = model.config.id2label[int(label)]
        if kind not in wanted:
            continue
        x0, y0, x1, y1 = (float(v) for v in box)
        x0, y0 = max(0, x0 - PAD_PX), max(0, y0 - PAD_PX)
        x1, y1 = min(img.width, x1 + PAD_PX), min(img.height, y1 + PAD_PX)
        found.append({"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0, "kind": kind, "score": round(float(score), 3)})

    order = reading_order([(f["x"], f["y"], f["w"], f["h"]) for f in found])
    return [found[i] for i in order]
