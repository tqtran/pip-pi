import pygame


def _blit_clipped(screen, surf, pos, clip_rect):
    prev_clip = screen.get_clip()
    screen.set_clip(clip_rect)
    screen.blit(surf, pos)
    screen.set_clip(prev_clip)


def _fit_font(fonts, text, max_width, keys):
    for key in keys:
        font = fonts[key]
        if font.size(text)[0] <= max_width:
            return font
    return fonts[keys[-1]]


def panel_cpu_mem(screen, rect, fonts, data, now, *, neon_box, text_surf, draw_metric_bar, S, colors, items=None):
    CYAN = colors["CYAN"]

    neon_box(screen, rect, CYAN, pulse=now + 1.7)

    render_items = items if items is not None else [("CPU", data["cpu"], CYAN, "%"), ("MEM", data["mem"], CYAN, "%")]
    col_w = (rect.w - S(24)) // max(1, len(render_items))
    for i, (name, val, color, suffix) in enumerate(render_items):
        x = rect.x + S(12) + i * col_w
        clip_rect = pygame.Rect(x, rect.y + S(8), col_w - S(12), rect.h - S(16))
        label_text = name
        value_text = f"{int(val)}{suffix}"
        label_font = _fit_font(fonts, label_text, max(20, clip_rect.w - S(6)), ["panel_title", "menu", "sm"])
        value_font = _fit_font(fonts, value_text, max(20, clip_rect.w - S(6)), ["load_val_big", "load_val", "load_line_big", "load_line", "panel_title"])
        label_surf = text_surf(label_font, label_text, color)
        value_surf = text_surf(value_font, value_text, color)

        bar_y = rect.bottom - S(22)
        label_y = rect.y + S(14)
        value_y = label_y + label_surf.get_height() + S(6)
        max_value_bottom = bar_y - S(8)
        if value_y + value_surf.get_height() > max_value_bottom:
            value_y = max(label_y + S(4), max_value_bottom - value_surf.get_height())

        _blit_clipped(screen, label_surf, (x, label_y), clip_rect)
        value_x = clip_rect.right - value_surf.get_width() - S(4)
        value_x = max(x, value_x)
        _blit_clipped(screen, value_surf, (value_x, value_y), clip_rect)
        bar_val = val if suffix != "F" else ((val - 86) * 1.2)
        draw_metric_bar(screen, x, bar_y, bar_val, color, blocks=10)
        if i < len(render_items) - 1:
            pygame.draw.line(screen, (36, 43, 73), (x + col_w - S(8), rect.y + S(16)), (x + col_w - S(8), rect.bottom - S(16)), 1)
