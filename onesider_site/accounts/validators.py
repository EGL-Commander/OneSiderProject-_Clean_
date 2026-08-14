"""
Thin wrappers around Django's built-in password validators.

These do NOT change validation behavior - min length, common-password
list, numeric-only check, and username/email similarity are all still
enforced exactly as Django defines them. Only the messages shown to
the user are replaced, to match OneSider's tone instead of Django's
generic defaults.
"""

from django.contrib.auth.password_validation import (
    CommonPasswordValidator as _CommonPasswordValidator,
    MinimumLengthValidator as _MinimumLengthValidator,
    NumericPasswordValidator as _NumericPasswordValidator,
    UserAttributeSimilarityValidator as _UserAttributeSimilarityValidator,
)
from django.core.exceptions import ValidationError


class MinimumLengthValidator(_MinimumLengthValidator):
    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                f"Your password needs at least {self.min_length} characters.",
                code="password_too_short",
            )

    def get_help_text(self):
        return f"At least {self.min_length} characters."


class CommonPasswordValidator(_CommonPasswordValidator):
    def validate(self, password, user=None):
        try:
            super().validate(password, user)
        except ValidationError:
            raise ValidationError(
                "That password is too easy to guess. Choose something less common.",
                code="password_too_common",
            )

    def get_help_text(self):
        return "Not something easily guessed."


class NumericPasswordValidator(_NumericPasswordValidator):
    def validate(self, password, user=None):
        try:
            super().validate(password, user)
        except ValidationError:
            raise ValidationError(
                "Your password can't be entirely numbers.",
                code="password_entirely_numeric",
            )

    def get_help_text(self):
        return "Can't be entirely numeric."


class UserAttributeSimilarityValidator(_UserAttributeSimilarityValidator):
    def validate(self, password, user=None):
        try:
            super().validate(password, user)
        except ValidationError:
            raise ValidationError(
                "Your password is too close to your username or email.",
                code="password_too_similar",
            )

    def get_help_text(self):
        return "Shouldn't be too close to your username or email."
