from typing import Optional

from pydantic import BaseModel


class StyleOut(BaseModel):
    id: int
    nom: str
    idParent: Optional[int] = None
    principal: Optional[bool] = None


class ProjectStyleEntry(BaseModel):
    styleId: int
    principal: bool = False


class ProjectStylesUpdateRequest(BaseModel):
    styles: list[ProjectStyleEntry]
