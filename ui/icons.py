# Icones SVG inline (stroke = currentColor, donc heritent de la couleur du conteneur).
# Aucune emoji dans toute l'app : logo, page_icon, alertes = SVG.

def svg(name, size=18):
    p = PATHS.get(name, PATHS["shield"])
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{p}</svg>')

PATHS = {
    "shield":   '<path d="M12 2l8 3v6c0 5-3.4 8.8-8 11-4.6-2.2-8-6-8-11V5z"/>',
    "info":     '<circle cx="12" cy="12" r="9"/><line x1="12" y1="11" x2="12" y2="16"/><line x1="12" y1="8" x2="12" y2="8"/>',
    "success":  '<circle cx="12" cy="12" r="9"/><path d="M8.5 12.5l2.5 2.5 4.5-5"/>',
    "warning":  '<path d="M12 3l9 16H3z"/><line x1="12" y1="10" x2="12" y2="14"/><line x1="12" y1="17" x2="12" y2="17"/>',
    "error":    '<circle cx="12" cy="12" r="9"/><line x1="9" y1="9" x2="15" y2="15"/><line x1="15" y1="9" x2="9" y2="15"/>',
}

# page_icon : data-URI SVG (couleur encodee, currentColor ne s'applique pas hors DOM)
PAGE_ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
             "viewBox='0 0 24 24' fill='%234f46e5'%3E%3Cpath d='M12 2l8 3v6c0 "
             "5-3.4 8.8-8 11-4.6-2.2-8-6-8-11V5z'/%3E%3C/svg%3E")