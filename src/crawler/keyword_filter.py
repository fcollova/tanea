"""
Keyword Filter - Algoritmi di filtraggio per rilevanza contenuti
Modulo dedicato al filtraggio multi-livello basato su keywords di dominio
"""

from typing import List, Optional, Dict, Any
from core.log import get_news_logger

logger = get_news_logger(__name__)

class KeywordFilter:
    """
    Filtro avanzato per keywords con algoritmi di scoring multi-livello
    """
    
    def __init__(self, debug: bool = False):
        """
        Inizializza il filtro keywords
        
        Args:
            debug: Abilita logging dettagliato per debug
        """
        self.debug = debug
        
        # Configurazione scoring
        self.TITLE_WEIGHT = 0.4      # Peso per match nel titolo (40%)
        self.CONTENT_WEIGHT = 0.1    # Peso base per match nel contenuto (10%)
        self.CONTENT_MAX_WEIGHT = 0.3 # Peso massimo per contenuto (30%)
        self.LONG_KEYWORD_BONUS = 0.1 # Bonus per keywords lunghe/specifiche
        self.MIN_RELEVANCE_THRESHOLD = 0.1  # Soglia minima rilevanza (10%)
        self.MAX_REALISTIC_SCORE = 3.0 # Score massimo realistico per normalizzazione
    
    def title_matches_keywords(self, title: str, keywords: List[str]) -> bool:
        """
        LIVELLO 1: Verifica se il titolo contiene keywords del dominio
        
        Args:
            title: Titolo del link/articolo
            keywords: Keywords del dominio da cercare
            
        Returns:
            bool: True se il titolo contiene almeno una keyword
        """
        if not keywords:
            if self.debug:
                logger.debug("[FILTER L1] Nessuna keyword fornita, accetto tutto")
            return True
        
        if not title:
            if self.debug:
                logger.debug("[FILTER L1] Titolo vuoto, rifiuto")
            return False
        
        title_lower = title.lower()
        
        # Verifica se almeno una keyword è presente nel titolo
        for keyword in keywords:
            if keyword.lower() in title_lower:
                if self.debug:
                    logger.debug(f"[FILTER L1] ✅ Keyword '{keyword}' trovata in titolo: {title[:50]}...")
                return True
        
        if self.debug:
            logger.debug(f"[FILTER L1] ❌ Nessuna keyword trovata in titolo: {title[:50]}...")
        return False
    
    def metadata_matches_keywords(self, title: str, description: str, keywords: List[str]) -> bool:
        """
        LIVELLO 2: Pre-filtraggio sui metadati (titolo + descrizione)
        
        Args:
            title: Titolo dell'articolo
            description: Descrizione/sommario dell'articolo
            keywords: Keywords del dominio da cercare
            
        Returns:
            bool: True se i metadati contengono almeno una keyword
        """
        if not keywords:
            if self.debug:
                logger.debug("[FILTER L2] Nessuna keyword fornita, accetto tutto")
            return True
        
        # Testo combinato da controllare
        check_text = ""
        if title:
            check_text += title.lower()
        if description:
            check_text += " " + description.lower()
        
        if not check_text.strip():
            if self.debug:
                logger.debug("[FILTER L2] Nessun testo nei metadati, rifiuto")
            return False
        
        # Verifica keywords nel testo combinato
        for keyword in keywords:
            if keyword.lower() in check_text:
                if self.debug:
                    logger.debug(f"[FILTER L2] ✅ Keyword '{keyword}' trovata nei metadati")
                return True
        
        if self.debug:
            logger.debug(f"[FILTER L2] ❌ Nessuna keyword trovata nei metadati: {check_text[:100]}...")
        return False
    
    def calculate_keyword_relevance(self, title: str, content: str, keywords: List[str]) -> float:
        """
        LIVELLO 3: Calcola score di rilevanza basato sulle keywords del dominio
        
        Args:
            title: Titolo articolo
            content: Contenuto completo articolo
            keywords: Keywords del dominio
            
        Returns:
            float: Score da 0.0 a 1.0 che indica rilevanza per il dominio
        """
        if not keywords:
            if self.debug:
                logger.debug("[FILTER L3] Nessuna keyword fornita, score = 1.0")
            return 1.0
        
        if not title and not content:
            if self.debug:
                logger.debug("[FILTER L3] Nessun testo fornito, score = 0.0")
            return 0.0
        
        text_full = f"{title} {content}".lower()
        title_lower = title.lower() if title else ""
        content_lower = content.lower() if content else ""
        
        score = 0.0
        matched_keywords = []
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            keyword_score = 0.0
            
            # Peso maggiore per match nel titolo
            if keyword_lower in title_lower:
                keyword_score += self.TITLE_WEIGHT
                if self.debug:
                    logger.debug(f"[FILTER L3] Keyword '{keyword}' in titolo: +{self.TITLE_WEIGHT}")
            
            # Peso per match nel contenuto
            if keyword_lower in content_lower:
                # Conta le occorrenze per valutare rilevanza
                occurrences = content_lower.count(keyword_lower)
                content_score = min(self.CONTENT_MAX_WEIGHT, self.CONTENT_WEIGHT * occurrences)
                keyword_score += content_score
                if self.debug:
                    logger.debug(f"[FILTER L3] Keyword '{keyword}' in contenuto ({occurrences}x): +{content_score:.2f}")
            
            # Bonus per keyword lunghe/specifiche (più di 2 parole)
            if len(keyword_lower.split()) > 2 and keyword_lower in text_full:
                keyword_score += self.LONG_KEYWORD_BONUS
                if self.debug:
                    logger.debug(f"[FILTER L3] Keyword lunga '{keyword}': +{self.LONG_KEYWORD_BONUS}")
            
            if keyword_score > 0:
                matched_keywords.append(keyword)
                score += keyword_score
        
        # Normalizza il score in modo realistico
        normalized_score = min(1.0, score / self.MAX_REALISTIC_SCORE)
        
        if self.debug:
            logger.debug(f"[FILTER L3] Score finale: {normalized_score:.3f} (raw: {score:.3f})")
            logger.debug(f"[FILTER L3] Keywords matched: {matched_keywords}")
        
        return normalized_score
    
    def is_content_relevant(self, title: str, content: str, keywords: List[str], 
                          threshold: Optional[float] = None) -> tuple[bool, float]:
        """
        Verifica completa di rilevanza contenuto con score dettagliato
        
        Args:
            title: Titolo articolo
            content: Contenuto articolo
            keywords: Keywords del dominio
            threshold: Soglia personalizzata (default: self.MIN_RELEVANCE_THRESHOLD)
            
        Returns:
            tuple: (is_relevant: bool, score: float)
        """
        if threshold is None:
            threshold = self.MIN_RELEVANCE_THRESHOLD
        
        score = self.calculate_keyword_relevance(title, content, keywords)
        is_relevant = score >= threshold
        
        if self.debug:
            status = "✅ RILEVANTE" if is_relevant else "❌ NON RILEVANTE"
            logger.debug(f"[FILTER L3] {status} - Score: {score:.3f} (soglia: {threshold:.3f})")
        
        return is_relevant, score
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """
        Statistiche configurazione filtro
        
        Returns:
            dict: Configurazione e parametri del filtro
        """
        return {
            "title_weight": self.TITLE_WEIGHT,
            "content_weight": self.CONTENT_WEIGHT,
            "content_max_weight": self.CONTENT_MAX_WEIGHT,
            "long_keyword_bonus": self.LONG_KEYWORD_BONUS,
            "min_threshold": self.MIN_RELEVANCE_THRESHOLD,
            "max_realistic_score": self.MAX_REALISTIC_SCORE,
            "debug_enabled": self.debug
        }
    
    def update_thresholds(self, **kwargs):
        """
        Aggiorna soglie e pesi del filtro
        
        Args:
            **kwargs: Parametri da aggiornare (title_weight, content_weight, etc.)
        """
        if "title_weight" in kwargs:
            self.TITLE_WEIGHT = kwargs["title_weight"]
        if "content_weight" in kwargs:
            self.CONTENT_WEIGHT = kwargs["content_weight"]
        if "content_max_weight" in kwargs:
            self.CONTENT_MAX_WEIGHT = kwargs["content_max_weight"]
        if "long_keyword_bonus" in kwargs:
            self.LONG_KEYWORD_BONUS = kwargs["long_keyword_bonus"]
        if "min_threshold" in kwargs:
            self.MIN_RELEVANCE_THRESHOLD = kwargs["min_threshold"]
        if "max_realistic_score" in kwargs:
            self.MAX_REALISTIC_SCORE = kwargs["max_realistic_score"]
        
        logger.info(f"Parametri filtro aggiornati: {kwargs}")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_domain_filter(keywords: List[str], debug: bool = False) -> KeywordFilter:
    """
    Factory function per creare filtro ottimizzato per un dominio specifico
    
    Args:
        keywords: Keywords del dominio
        debug: Abilita debug logging
        
    Returns:
        KeywordFilter: Filtro configurato per il dominio
    """
    filter_instance = KeywordFilter(debug=debug)
    
    # Ottimizzazioni basate sul numero di keywords
    keyword_count = len(keywords)
    
    if keyword_count > 20:
        # Molte keywords: soglia più permissiva
        filter_instance.update_thresholds(min_threshold=0.08)
    elif keyword_count < 5:
        # Poche keywords: soglia più restrittiva
        filter_instance.update_thresholds(min_threshold=0.15)
    
    logger.info(f"Filtro dominio creato con {keyword_count} keywords, soglia: {filter_instance.MIN_RELEVANCE_THRESHOLD}")
    return filter_instance


def quick_keyword_check(text: str, keywords: List[str]) -> bool:
    """
    Check rapido per almeno una keyword nel testo (case-insensitive)
    
    Args:
        text: Testo da controllare
        keywords: Keywords da cercare
        
    Returns:
        bool: True se almeno una keyword è presente
    """
    if not keywords or not text:
        return False
    
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in keywords)


def extract_matched_keywords(text: str, keywords: List[str]) -> List[str]:
    """
    Estrae le keywords effettivamente trovate nel testo
    
    Args:
        text: Testo da analizzare
        keywords: Keywords da cercare
        
    Returns:
        list: Keywords trovate nel testo
    """
    if not keywords or not text:
        return []
    
    text_lower = text.lower()
    return [kw for kw in keywords if kw.lower() in text_lower]