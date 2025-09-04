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

import cairo
import cv2
import numpy as np

import gi
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo

import math

_MAX_DIM_SUM = 10_000
_MIN_RATIO = 0.05 # 1:20

def _fix_ratio_if_needed(surface: cairo.ImageSurface) -> cairo.ImageSurface:
    w, h = surface.get_width(), surface.get_height()
    if w <= 0 or h <= 0:
        return surface
    r = w / h
    min_r = _MIN_RATIO
    max_r = 1.0 / _MIN_RATIO

    if min_r <= r <= max_r:
        return surface

    # Нужно дорисовать поля
    if r < min_r:
        new_w = int(math.ceil(h * min_r))
        new_h = h
    else:
        new_w = w
        new_h = int(math.ceil(w * min_r))

    # Чёрный фон
    fmt = surface.get_format()
    out = cairo.ImageSurface(fmt, new_w, new_h)
    ctx = cairo.Context(out)
    ctx.set_source_rgb(0, 0, 0)
    ctx.rectangle(0, 0, new_w, new_h)
    ctx.fill()

    # Рисуем исходное изображение по центру
    offset_x = (new_w - w) / 2.0
    offset_y = (new_h - h) / 2.0
    ctx.set_source_surface(surface, offset_x, offset_y)
    ctx.paint()

    return out

def _fix_dim_sum_if_needed(surface: cairo.ImageSurface) -> cairo.ImageSurface:
    w = surface.get_width()
    h = surface.get_height()
    dim_sum = w + h
    if dim_sum <= _MAX_DIM_SUM:
        return surface

    r = w / h  # > 0 для корректных изображений

    # Решение системы:
    # w + h = _MAX_DIM_SUM, w / h = r
    # h = _MAX_DIM_SUM / (r + 1), w = _MAX_DIM_SUM - h
    new_h = _MAX_DIM_SUM / (r + 1.0)
    new_w = _MAX_DIM_SUM - new_h

    # округляем к целым и страхуемся от нулей
    new_w_i = max(1, int(round(new_w)))
    new_h_i = max(1, int(round(new_h)))

    fmt = surface.get_format()
    out = cairo.ImageSurface(fmt, new_w_i, new_h_i)
    ctx = cairo.Context(out)

    sx = new_w_i / w
    sy = new_h_i / h
    ctx.scale(sx, sy)

    pattern = cairo.SurfacePattern(surface)
    pattern.set_filter(cairo.FILTER_BILINEAR)
    ctx.set_source(pattern)
    ctx.paint()

    return out

def scale_for_tg(surface: cairo.ImageSurface) -> cairo.ImageSurface:
    surface = _fix_ratio_if_needed(surface)
    surface = _fix_dim_sum_if_needed(surface)
    return surface


def image_surface_from_cv2_img(cv2img: cv2.typing.MatLike) -> cairo.ImageSurface:
    if cv2img is None:
        raise ValueError("cv2img is None")
    if len(cv2img.shape) == 2:
        cv2img = cv2.cvtColor(cv2img, cv2.COLOR_GRAY2BGRA)
    elif cv2img.shape[2] == 3:
        cv2img = cv2.cvtColor(cv2img, cv2.COLOR_BGR2BGRA)
    elif cv2img.shape[2] == 4:
        pass
    else:
        raise ValueError("Unsupported image format")
    h, w = cv2img.shape[:2]
    if not cv2img.flags["C_CONTIGUOUS"]:
        cv2img = cv2img.copy()
    stride = w * 4
    data = cv2img.tobytes()
    surf = cairo.ImageSurface.create_for_data(bytearray(data), cairo.FORMAT_ARGB32, w, h, stride)
    return surf

def layout_text(cr: cairo.Context, text: str, font_family: str, font_size: float, width: int | None = None, alignment: int = Pango.Alignment.LEFT) -> tuple[Pango.Layout, int, int]:
    layout = PangoCairo.create_layout(cr)
    fd = Pango.FontDescription()
    if font_family:
        fd.set_family(font_family)
    fd.set_size(int(font_size * Pango.SCALE))
    layout.set_font_description(fd)
    layout.set_text(text, -1)
    layout.set_alignment(alignment)
    if width is not None and width > 0:
        layout.set_width(width * Pango.SCALE)
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
    w, h = layout.get_pixel_size()
    return layout, w, h

def scale_dims(surface: cairo.ImageSurface, min_dim: int = 512) -> tuple[cairo.ImageSurface, float]:
    w, h = surface.get_width(), surface.get_height()
    img_dim = min(w, h)
    scale = 1.0
    if img_dim * scale < min_dim:
        scale *= min_dim / (img_dim * scale)
    else:
        return surface, scale
    
    scaled_w = max(1, int(w * scale))
    scaled_h = max(1, int(h * scale))

    # рабочая поверхность: рисуем отмасштабированное изображение на ней
    work_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, scaled_w, scaled_h)
    work_cr = cairo.Context(work_surf)
    work_cr.save()
    work_cr.scale(scale, scale)
    work_cr.set_source_surface(surface, 0, 0)
    work_cr.paint()
    work_cr.restore()
    return work_surf, scale