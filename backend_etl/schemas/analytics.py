from pydantic import BaseModel, Field


class AnalyticsProjectOption(BaseModel):
    id: int
    nom: str


class MetabaseEmbedResponse(BaseModel):
    url: str
    projects: list[AnalyticsProjectOption] = Field(default_factory=list)