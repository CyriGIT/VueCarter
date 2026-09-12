from typing import Optional

from pydantic import BaseModel, Field


class EtlSyncRequest(BaseModel):
    projectId: int


class SyncedMetricResponse(BaseModel):
    type: str
    value: int


class EtlSyncResponse(BaseModel):
    platform: str
    syncedAt: str
    metrics: list[SyncedMetricResponse]


class ConnectorMetricResponse(BaseModel):
    type: str
    value: int
    date: str


class ConnectorStatusResponse(BaseModel):
    connected: bool
    profileUrl: Optional[str] = None
    externalId: Optional[str] = None
    metrics: list[ConnectorMetricResponse] = Field(default_factory=list)
    metricValue: Optional[int] = None
    metricType: Optional[str] = None
    lastSync: Optional[str] = None


class ProjectConnectorsResponse(BaseModel):
    spotify: ConnectorStatusResponse
    mx3: ConnectorStatusResponse


class Mx3Band(BaseModel):
    id: int
    name: str
    city: Optional[str] = None
    profileUrl: Optional[str] = None
    imageUrl: Optional[str] = None


class Mx3BandSearchResponse(BaseModel):
    bands: list[Mx3Band]


class Mx3ConnectRequest(BaseModel):
    bandId: int


class Mx3ConnectResponse(BaseModel):
    connected: bool
    band: Mx3Band


class Mx3Gig(BaseModel):
    name: str
    date: str
    bandName: Optional[str] = None
    stageName: Optional[str] = None
    location: Optional[str] = None
    locationUrl: Optional[str] = None
    ticketUrl: Optional[str] = None


class Mx3GigsResponse(BaseModel):
    bandId: int
    gigs: list[Mx3Gig]


class SpotifyTrack(BaseModel):
    id: str
    name: str
    track_number: int
    duration_ms: int
    release_date: str


class SpotifyAlbum(BaseModel):
    id: str
    name: str
    release_date: str
    album_type: str
    tracks: list[SpotifyTrack]


class SpotifyCatalogResponse(BaseModel):
    artist_id: str
    artist_name: str
    followers: int
    popularity: int
    genres: list[str]
    albums: list[SpotifyAlbum]


class SpotifyConnectRequest(BaseModel):
    artistId: str


class SpotifyConnectResponse(BaseModel):
    connected: bool
    artistId: str
    artistName: str
    followers: int


class SpotifyImportTrackRequest(BaseModel):
    spotifyId: str
    titre: str
    durationMs: int
    releaseDate: Optional[str] = None


class SpotifyImportAlbumRequest(BaseModel):
    spotifyId: str
    titre: str
    releaseDate: Optional[str] = None


class SpotifyImportRequest(BaseModel):
    tracks: list[SpotifyImportTrackRequest] = []
    albums: list[SpotifyImportAlbumRequest] = []


class SpotifyImportResponse(BaseModel):
    tracksImported: int
    albumsImported: int


class SpotifyImportImageResponse(BaseModel):
    avatarUrl: str
