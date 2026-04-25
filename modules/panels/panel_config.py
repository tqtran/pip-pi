import copy

import pygame

# (label, section, key, step, min_val, max_val)
_FIELDS = [
    ("WiFi Scan Interval (s)",  "scan_intervals",    "wifi_seconds",             5,  5, 300),
    ("BLE Scan Interval (s)",   "scan_intervals",    "ble_seconds",              5,  5, 300),
    ("BLE First Window (s)",    "scan_behavior",     "ble_first_window_seconds", 5,  5, 120),
    ("BLE Window (s)",          "scan_behavior",     "ble_window_seconds",       5,  5, 120),
    ("BLE Stagger (s)",         "scan_behavior",     "ble_stagger_seconds",      5,  0, 120),
    ("CPU/Mem Refresh (s)",     "refresh_intervals", "load_seconds",             1,  1,  60),
    ("Stats Refresh (s)",       "refresh_intervals", "stats_seconds",            5,  5, 300),
]

_ROW_H   = 44
_ARROW_W = 28
_ARROW_H = 18
_BTN_H   = 44
_BTN_W   = 140
_TITLE_H  = 36   # vertical space the title row occupies


def _action_rects(rect, S):
    """Three buttons right-aligned on the title row."""
    btn_h = S(28)
    btn_y = rect.y + S(8)
    btn_w = S(120)
    gap   = S(8)
    rst_rect = pygame.Rect(rect.right - S(14) - btn_w,          btn_y, btn_w, btn_h)
    upd_rect = pygame.Rect(rst_rect.x  - gap  - btn_w,          btn_y, btn_w, btn_h)
    fs_rect  = pygame.Rect(upd_rect.x  - gap  - btn_w,          btn_y, btn_w, btn_h)
    return fs_rect, upd_rect, rst_rect


def _ensure_draft(data, config):
    if data.get("config_draft") is None:
        data["config_draft"] = copy.deepcopy(config)


def _get_val(draft, section, key):
    return float(draft.get(section, {}).get(key, 0))


def _set_val(draft, section, key, val, mn, mx):
    if section not in draft:
        draft[section] = {}
    draft[section][key] = float(max(mn, min(mx, val)))


def _field_rects(rect, i, S):
    row_h = S(_ROW_H)
    # fields start just below the title row
    row_y = rect.y + S(_TITLE_H) + S(10) + i * row_h
    up_rect = pygame.Rect(rect.right - S(44), row_y + S(4),  S(_ARROW_W), S(_ARROW_H))
    dn_rect = pygame.Rect(rect.right - S(44), row_y + S(24), S(_ARROW_W), S(_ARROW_H))
    return row_y, up_rect, dn_rect


def _btn_rects(rect, S):
    btn_y = rect.bottom - S(58)
    cancel_rect = pygame.Rect(rect.x + S(18),                   btn_y, S(_BTN_W), S(_BTN_H))
    save_rect   = pygame.Rect(rect.right - S(_BTN_W) - S(18),   btn_y, S(_BTN_W), S(_BTN_H))
    return cancel_rect, save_rect


def config_click_action(mx, my, rect, data, config, S):
    _ensure_draft(data, config)
    draft = data["config_draft"]

    fs_rect, upd_rect, rst_rect = _action_rects(rect, S)
    if fs_rect.collidepoint(mx, my):
        return "toggle_fullscreen", None
    if upd_rect.collidepoint(mx, my):
        return "update", None
    if rst_rect.collidepoint(mx, my):
        return "restart", None

    cancel_rect, save_rect = _btn_rects(rect, S)
    if save_rect.collidepoint(mx, my):
        return "save", None
    if cancel_rect.collidepoint(mx, my):
        return "cancel", None

    for i, (label, section, key, step, mn, mx_val) in enumerate(_FIELDS):
        _, up_rect, dn_rect = _field_rects(rect, i, S)
        if up_rect.collidepoint(mx, my):
            _set_val(draft, section, key, _get_val(draft, section, key) + step, mn, mx_val)
            return "changed", None
        if dn_rect.collidepoint(mx, my):
            _set_val(draft, section, key, _get_val(draft, section, key) - step, mn, mx_val)
            return "changed", None

    return None, None


def panel_config(screen, rect, fonts, data, now, config, *, neon_box, text_surf, S, colors):
    CYAN  = colors["CYAN"]
    PINK  = colors["PINK"]
    MUTED = colors["MUTED"]
    TEXT  = colors["TEXT"]

    _ensure_draft(data, config)
    draft = data["config_draft"]

    neon_box(screen, rect, CYAN, pulse=now + 1.0)

    screen.blit(text_surf(fonts["panel_title"], "CONFIG", CYAN), (rect.x + S(18), rect.y + S(10)))

    # --- action buttons (same row as title, right-justified) ---
    VIOLET = (122, 56, 255)
    fs_rect, upd_rect, rst_rect = _action_rects(rect, S)
    for btn_rect, label, border in [
        (fs_rect,  "FULLSCREEN", VIOLET),
        (upd_rect, "UPDATE",     CYAN),
        (rst_rect, "RESTART",    PINK),
    ]:
        pygame.draw.rect(screen, (10, 12, 28), btn_rect, border_radius=S(5))
        pygame.draw.rect(screen, border, btn_rect, 1, border_radius=S(5))
        lbl = text_surf(fonts["top"], label, border)
        screen.blit(lbl, (btn_rect.centerx - lbl.get_width() // 2,
                          btn_rect.centery - lbl.get_height() // 2))

    # divider below title row
    div_y = rect.y + S(_TITLE_H) + S(4)
    pygame.draw.line(screen, (30, 40, 70), (rect.x + S(10), div_y), (rect.right - S(10), div_y), 1)

    row_h = S(_ROW_H)
    for i, (label, section, key, step, mn, mx_val) in enumerate(_FIELDS):
        row_y, up_rect, dn_rect = _field_rects(rect, i, S)

        # zebra stripe
        if i % 2 == 0:
            row_bg = pygame.Rect(rect.x + S(6), row_y, rect.w - S(12), row_h - S(2))
            pygame.draw.rect(screen, (14, 18, 38), row_bg, border_radius=S(4))

        # label
        screen.blit(text_surf(fonts["sm"], label, MUTED), (rect.x + S(18), row_y + S(12)))

        # value — sits just left of the arrows
        val = _get_val(draft, section, key)
        val_surf = text_surf(fonts["panel_title"], str(int(val)), TEXT)
        val_x = up_rect.x - S(14) - val_surf.get_width()
        screen.blit(val_surf, (val_x, row_y + S(9)))

        # up arrow (▲)
        pygame.draw.rect(screen, (20, 30, 60), up_rect, border_radius=S(3))
        pygame.draw.rect(screen, CYAN, up_rect, 1, border_radius=S(3))
        ux, uy = up_rect.centerx, up_rect.centery
        pygame.draw.polygon(screen, CYAN, [
            (ux,        uy - S(4)),
            (ux - S(5), uy + S(4)),
            (ux + S(5), uy + S(4)),
        ])

        # down arrow (▼)
        pygame.draw.rect(screen, (20, 30, 60), dn_rect, border_radius=S(3))
        pygame.draw.rect(screen, PINK, dn_rect, 1, border_radius=S(3))
        dx, dy = dn_rect.centerx, dn_rect.centery
        pygame.draw.polygon(screen, PINK, [
            (dx,        dy + S(4)),
            (dx - S(5), dy - S(4)),
            (dx + S(5), dy - S(4)),
        ])

    # Bottom buttons
    cancel_rect, save_rect = _btn_rects(rect, S)

    pygame.draw.rect(screen, (30, 10, 18), cancel_rect, border_radius=S(6))
    pygame.draw.rect(screen, PINK, cancel_rect, 1, border_radius=S(6))
    ct = text_surf(fonts["sm"], "CANCEL", PINK)
    screen.blit(ct, (cancel_rect.centerx - ct.get_width() // 2,
                     cancel_rect.centery - ct.get_height() // 2))

    pygame.draw.rect(screen, (8, 28, 18), save_rect, border_radius=S(6))
    pygame.draw.rect(screen, CYAN, save_rect, 2, border_radius=S(6))
    st = text_surf(fonts["sm"], "SAVE", CYAN)
    screen.blit(st, (save_rect.centerx - st.get_width() // 2,
                     save_rect.centery - st.get_height() // 2))
