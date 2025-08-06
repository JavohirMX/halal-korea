from django.contrib.auth.tokens import PasswordResetTokenGenerator

class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Strategy object used to generate and check tokens for email verification.
    """
    def _make_hash_value(self, user, timestamp):
        """
        Hash the user's pk, email, and some user state that's sure to change
        after email verification to produce a token that invalidated when it's used.
        """
        # Include the user's email_verified status in the hash so that
        # the token becomes invalid once the email is verified
        return f"{user.pk}{user.email}{user.email_verified}{timestamp}" # type: ignore

email_verification_token = EmailVerificationTokenGenerator()
