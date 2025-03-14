import random
import string
import logging

logger = logging.getLogger(__name__)

class ResetCodeService:
    def __init__(self):
        # Store codes in memory (you might want to use Redis or database in production)
        self._reset_codes = {}

    def generate_reset_code(self, email: str) -> str:
        """Generate a 6-digit reset code"""
        code = ''.join(random.choices(string.digits, k=6))
        self._reset_codes[email] = code
        logger.info(f"Reset code generated for {email}")
        return code

    def verify_reset_code(self, email: str, code: str) -> bool:
        """Verify if the reset code is valid"""
        stored_code = self._reset_codes.get(email)
        if stored_code and stored_code == code:
            # Remove the code once used
            del self._reset_codes[email]
            return True
        return False 