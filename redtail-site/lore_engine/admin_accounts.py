"""Admin-only account management: list every account (built-in + created),
create new ones. Lets admin-tier users (lore, admin) onboard teammates
themselves instead of needing a code change + redeploy for every new login.
"""
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import accounts


class AdminListRequest(BaseModel):
    username: str
    password: str


class AdminCreateRequest(BaseModel):
    adminUsername: str
    adminPassword: str
    username: str
    password: str
    displayName: str = ""
    tier: str = "member"


def _list_accounts(req: AdminListRequest):
    if not accounts.is_admin(req.username, req.password):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    rows = accounts.list_all_accounts()
    return {"accounts": [
        {"username": r["username"], "password": r["password"], "displayName": r.get("displayName") or r["username"],
         "tier": r.get("tier", "member"), "source": r.get("source"), "createdAt": r.get("createdAt")}
        for r in rows
    ]}


def _create_account(req: AdminCreateRequest):
    if not accounts.is_admin(req.adminUsername, req.adminPassword):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        row = accounts.create_account(req.username, req.password, req.displayName, req.tier)
        return {"account": row}
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


def install(app):
    app.post("/api/lore/admin/accounts/list")(_list_accounts)
    app.post("/api/lore/admin/accounts/create")(_create_account)
