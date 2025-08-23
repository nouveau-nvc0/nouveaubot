import numpy as np
import insightface
import cv2
from dataclasses import dataclass

_detector = insightface.app.FaceAnalysis(providers=['CPUExecutionProvider'])
_detector.prepare(ctx_id=0, det_size=(640, 640))

@dataclass
class Box:
    x1: int
    y1: int
    x2: int
    y2: int

def detect_faces(img_data: bytes) -> list[Box]:
    nparr = np.frombuffer(img_data, np.uint8)
    cv2img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    faces = _detector.get(cv2img)
    return [Box(*face.bbox.astype(int)) for face in faces]
