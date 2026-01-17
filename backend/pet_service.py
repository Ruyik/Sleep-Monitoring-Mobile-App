from datetime import datetime

class PetService:
    """
    Handles the logic for the virtual sleep pet based on consistency scores.
    """

    def calculate_pet_state(self, consistency_score, last_login_str=None):
        """
        Determines the pet's state based on score and optionally time since last login.
        Returns: (image_path, status_text, text_color_rgba)
        """
        # Ensure score is a float just in case
        try:
            score = float(consistency_score)
        except (ValueError, TypeError):
            score = 0.0

        # --- 1. Check Inactivity (Dead State) ---
        # (Optional implementation for later: Check if last_login > 3 days ago)
        # if last_login_str:
        #      last_login = datetime.fromisoformat(last_login_str)
        #      days_away = (datetime.now() - last_login).days
        #      if days_away >= 3:
        #          return ("UI/images/pet_dead.png", "Oh no! Pet passed away due to inactivity.", (0.5, 0.5, 0.5, 1))

        # --- 2. Determine State based on Consistency Score ---
        # Green Tier (>= 95%)
        if score >= 95:
            return (
                "UI/images/pet_full.gif",
                "Your pet is thriving! Excellent consistency.",
                (0.2, 0.7, 0.2, 1)  # Green text
            )
        # Yellow Tier (85% - 95%)
        elif score >= 85:
            return (
                "UI/images/pet_neutral.gif",
                "Your pet is okay, but could use better sleep.",
                (0.7, 0.7, 0.2, 1)  # Yellow/Gold text
            )
        # Red Tier (< 85%)
        else:
            return (
                "UI/images/pet_hungry.gif",
                "Your pet is sad and hungry. Improve consistency!",
                (0.8, 0.3, 0.3, 1)  # Red text
            )