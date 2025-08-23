# Copyright (C) 2025 basilbot contributors

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
