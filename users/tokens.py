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


class PasswordResetTokenGenerator(PasswordResetTokenGenerator):
    """
    Strategy object used to generate and check tokens for password reset.
    Single-use tokens that expire after password change.
    """
    def _make_hash_value(self, user, timestamp):
        """
        Hash the user's pk, password hash, and last_login to produce a token
        that invalidates when the password is changed or user logs in.
        """
        # Include password hash and last_login so token becomes invalid after password change
        login_timestamp = '' if user.last_login is None else user.last_login.replace(microsecond=0, tzinfo=None)
        return f"{user.pk}{user.password}{login_timestamp}{timestamp}"


# Token generators
email_verification_token = EmailVerificationTokenGenerator()
password_reset_token = PasswordResetTokenGenerator()
