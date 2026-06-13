"""
vinhlong360 — Auth dependencies for FastAPI.

Usage in routes:
  from auth_middleware import get_current_user, require_user, require_role

  @router.get("/feed")
  async def feed(user=Depends(get_current_user)):  # user or None
      ...

  @router.post("/posts")
  async def create_post(user=Depends(require_user)):  # must be logged in
      ...

  @router.delete("/admin/ban")
  async def ban(user=Depends(require_role("admin"))):
      ...
"""

from fastapi import Depends, HTTPException, Request

from auth import _get_current_user_or_none


async def get_current_user(request: Request) -> dict | None:
    """Returns current user or None. Does NOT raise."""
    return await _get_current_user_or_none(request)


async def require_user(request: Request) -> dict:
    """Requires authenticated user. Raises 401 if not logged in."""
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Vui lòng đăng nhập để thực hiện thao tác này")
    return user


def require_role(*roles: str):
    """Factory: requires user with one of the given roles."""
    async def dep(request: Request) -> dict:
        user = await _get_current_user_or_none(request)
        if not user:
            raise HTTPException(401, "Vui lòng đăng nhập")
        if user.get("role") not in roles:
            raise HTTPException(403, "Bạn không có quyền thực hiện thao tác này")
        return user
    return dep
