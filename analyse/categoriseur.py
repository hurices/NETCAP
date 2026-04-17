"""
analyse/categoriseur.py
Catégorisation des domaines.
"""

from typing import Dict, Optional
import logging

import config
from api.schemas import CategoryEnum

logger = logging.getLogger(__name__)


class Categoriseur:
    """
    Classe responsable de la catégorisation des domaines.
    Utilise un dictionnaire de règles pour classifier les sites web.

    Règles de catégorisation:
    1. Correspondance exacte
    2. Correspondance par sous-domaine (ex: *.youtube.com)
    3. Correspondance par pattern (ex: podcasts.*)
    4. Par défaut: "Autre / Inconnu"
    """

    def __init__(self):
        """Initialise le catégoriseur avec les règles depuis config."""
        # Règles de catégorisation depuis config.py
        self.rules: Dict[str, str] = config.CATEGORIZATION_RULES.copy()

        # Règles pour sous-domaines
        self.subdomain_rules: Dict[str, str] = {
            "mail.google.com": CategoryEnum.EMAIL,
            "drive.google.com": CategoryEnum.PRODUCTIVITY,
            "calendar.google.com": CategoryEnum.PRODUCTIVITY,
            "docs.google.com": CategoryEnum.PRODUCTIVITY,
        }

        # Patterns génériques (ex: *.podcast.*)
        self.patterns: Dict[str, str] = {
            "podcast": CategoryEnum.STREAMING,
            "blog": CategoryEnum.NEWS,
            "forum": CategoryEnum.SOCIAL,
        }

        logger.info(f"Categoriseur initialisé avec {len(self.rules)} règles")

    def categoriser(self, domain: str) -> CategoryEnum:
        """
        Détermine la catégorie d'un domaine.

        Args:
            domain: Domaine à catégoriser (ex: "www.youtube.com")

        Returns:
            Catégorie correspondante
        """
        normalized = self._normalize_domain(domain)
        
        # 1. Correspondance exacte
        exact = self._check_exact_match(normalized)
        if exact:
            return CategoryEnum(exact)
            
        # 2. Correspondance par sous-domaine
        sub = self._check_subdomain_match(normalized)
        if sub:
            return CategoryEnum(sub)
            
        # 3. Correspondance par pattern
        pattern = self._check_pattern_match(normalized)
        if pattern:
            return CategoryEnum(pattern)
            
        return CategoryEnum.OTHER

    def _normalize_domain(self, domain: str) -> str:
        """Normalise le domaine pour la recherche."""
        domain = domain.lower().strip()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain

    def _check_exact_match(self, domain: str) -> Optional[str]:
        """Vérifie si le domaine correspond exactement à une règle."""
        return self.rules.get(domain)

    def _check_subdomain_match(self, domain: str) -> Optional[str]:
        """Vérifie si le domaine est un sous-domaine d'une règle."""
        for base_domain, category in self.rules.items():
            if domain.endswith(f".{base_domain}") or domain == base_domain:
                return category
        return None

    def _check_pattern_match(self, domain: str) -> Optional[str]:
        """Vérifie si le domaine correspond à un pattern générique."""
        for pattern, category in self.patterns.items():
            if pattern in domain:
                return category
        return None

    def ajouter_regle(self, domaine: str, categorie: CategoryEnum) -> None:
        """Ajoute une nouvelle règle de catégorisation."""
        self.rules[domaine.lower()] = categorie
        logger.info(f"Règle ajoutée: {domaine} -> {categorie}")

    def get_stats(self) -> Dict[str, int]:
        """Retourne des statistiques sur les règles."""
        return {
            "total_rules": len(self.rules),
            "total_patterns": len(self.patterns),
            "total_subdomain_rules": len(self.subdomain_rules)
        }