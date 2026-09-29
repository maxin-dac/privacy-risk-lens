
RECO = {
    "email":    ("reco.action.anonymiser", "reco.desc.email"),
    "phone":    ("reco.action.anonymiser", "reco.desc.phone"),
    "name":     ("reco.action.supprimer",  "reco.desc.name"),
    "address":  ("reco.action.agreger",    "reco.desc.address"),
    "id":       ("reco.action.chiffrer",   "reco.desc.id"),
    "health":   ("reco.action.supprimer",  "reco.desc.health"),
    "quasi_id": ("reco.action.agreger",    "reco.desc.quasi_id"),
    "none":     ("reco.action.conserver",  "reco.desc.none"),
}

def recommend_for(category, is_qi):
    if is_qi and category != "quasi_id":
        return "reco.action.agreger"
    return RECO.get(category, RECO["none"])[0]

def reco_detail(category):
    return RECO.get(category, RECO["none"])