import math

class AnalysisEngine:
    @staticmethod
    def calculate_player_rating(stats: dict) -> float:
        """
        Calculates player rating (3.5 - 9.5) based on AI stats.
        stats: {speed: float, distance: float, passes: int, goals: int, cards: int}
        """
        # Base rating
        rating = 5.0
        
        # Performance modifiers
        rating += (stats.get('goals', 0) * 1.5)
        rating += (stats.get('passes', 0) * 0.1)
        rating += (stats.get('distance', 0) / 1000) * 0.5 # 0.5 per km
        
        # Penalties
        rating -= (stats.get('cards_yellow', 0) * 0.5)
        rating -= (stats.get('cards_red', 0) * 2.0)
        
        # Clamp between 3.5 and 9.5
        rating = max(3.5, min(9.5, rating))
        return round(rating, 1)

    @staticmethod
    def get_star_ranking(rating: float) -> str:
        if rating >= 9.0: return "Elite (5 Stars)"
        if rating >= 8.0: return "Professional (4 Stars)"
        if rating >= 7.0: return "Solid (3 Stars)"
        if rating >= 5.0: return "developing (2 Stars)"
        return "Rookie (1 Star)"
