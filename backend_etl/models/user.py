from sqlalchemy import Boolean, Column, Integer, String

from database.database import Base


class Utilisateur(Base):
    __tablename__ = "CompteUtilisateur"

    id_utilisateur = Column(Integer, primary_key=True)
    email = Column(String(150), nullable=False)
    nom_affichage = Column(String(200), nullable=True)
    mot_de_passe_hash = Column(String(255), nullable=False)
    id_role = Column(Integer, nullable=False)
    id_personne = Column(Integer, nullable=True)
    est_actif = Column(Boolean, nullable=False, default=True)

    @property
    def is_active(self) -> bool:
        return self.est_actif

    @property
    def role(self) -> str:
        return {
            1: "admin",
            2: "gestionnaire_case",
            3: "expert_jury",
            4: "artiste",
            5: "accompagnant",
        }.get(self.id_role, "unknown")
