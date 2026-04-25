def panel_status(screen, rect, fonts, data, now, *, neon_box, text_surf, draw_metric_bar, S, colors):
    VIOLET = colors["VIOLET"]
    MUTED = colors["MUTED"]

    neon_box(screen, rect, VIOLET, pulse=now + 0.8)

    temp_f = (data["temp"] * 9.0 / 5.0) + 32.0
    labels = [
        ("STORE", data["store"], VIOLET),
        ("TEMP", temp_f, VIOLET),
    ]
    col_w = (rect.w - S(24)) // 3
    bar_y = rect.bottom - S(38)
    for i, (name, val, color) in enumerate(labels):
        x = rect.x + S(12) + i * col_w
        label_surf = text_surf(fonts["sm"], f"{name}:", MUTED)
        value_text = f"{int(val)}%" if name != "TEMP" else f"{int(val)}F"
        value_surf = text_surf(fonts["stat_val"], value_text, color)
        value_y = bar_y - S(8) - value_surf.get_height()
        label_y = value_y - S(10) - label_surf.get_height()
        label_y = max(rect.y + S(18), label_y)
        screen.blit(label_surf, (x, label_y))
        screen.blit(value_surf, (x, value_y))
        draw_metric_bar(screen, x, bar_y, val if name != "TEMP" else ((val - 86) * 1.2), color)
        if i < 2:
            import pygame
            pygame.draw.line(screen, (36, 43, 73), (x + col_w - S(8), rect.y + S(38)), (x + col_w - S(8), rect.bottom - S(16)), 1)

    up_x = rect.x + S(12) + 2 * col_w
    up_label = text_surf(fonts["sm"], "UPTIME:", MUTED)
    up_value = text_surf(fonts["stat_val"], data["uptime"], VIOLET)
    up_value_y = bar_y - S(8) - up_value.get_height()
    up_label_y = max(rect.y + S(18), up_value_y - S(10) - up_label.get_height())
    screen.blit(up_label, (up_x, up_label_y))
    screen.blit(up_value, (up_x, up_value_y))
