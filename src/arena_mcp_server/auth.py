"""Authentication providers with domain restrictions."""

import logging
from fastmcp.server.auth.oauth_proxy import OAuthProxy
from fastmcp.server.auth.providers.google import GoogleTokenVerifier
from fastmcp.server.auth.auth import AccessToken

logger = logging.getLogger(__name__)

ALLOWED_DOMAIN = "carbonrobotics.com"


class CarbonRoboticsTokenVerifier(GoogleTokenVerifier):
    """Google token verifier enforcing @carbonrobotics.com domain."""


    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify token and enforce domain restriction.

        Args:
            token: Google OAuth access token

        Returns:
            AccessToken if valid and from allowed domain, None otherwise
        """
        # Call parent verification first (validates with Google)
        access_token = await super().verify_token(token)

        if access_token is None:
            return None

        # Check email domain
        email = access_token.claims.get("email", "")
        if not email.endswith(f"@{ALLOWED_DOMAIN}"):
            logger.warning(
                f"Rejected authentication from {email} - "
                f"not a @{ALLOWED_DOMAIN} account"
            )
            return None

        logger.info(f"Authenticated user: {email}")
        return access_token


class RestrictedGoogleProvider(OAuthProxy):
    """Google OAuth provider restricted to @carbonrobotics.com.

    This provider uses Google OAuth 2.0 with domain-restricted token verification,
    allowing only @carbonrobotics.com email addresses.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        base_url: str,
        required_scopes: list[str] | None = None,
        timeout_seconds: int = 10,
        extra_authorize_params: dict | None = None,
        **kwargs,
    ):
        """Initialize restricted Google provider.

        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            base_url: Public URL where this server is accessible
            required_scopes: OAuth scopes to request (defaults to openid and email)
            timeout_seconds: Token verification timeout (default 10)
            extra_authorize_params: Additional OAuth authorization parameters
            **kwargs: Additional arguments passed to OAuthProxy
        """
        # Set default scopes if not provided
        if required_scopes is None:
            required_scopes = [
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
            ]

        # Create domain-restricted token verifier
        token_verifier = CarbonRoboticsTokenVerifier(
            required_scopes=required_scopes,
            timeout_seconds=timeout_seconds,
        )

        # Merge extra_authorize_params
        extra_authorize_params = {} if extra_authorize_params is None else extra_authorize_params

        # Initialize OAuth proxy with Google endpoints
        super().__init__(
            upstream_authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
            upstream_token_endpoint="https://oauth2.googleapis.com/token",
            upstream_client_id=client_id,
            upstream_client_secret=client_secret,
            token_verifier=token_verifier,
            base_url=base_url,
            extra_authorize_params=extra_authorize_params,
            **kwargs,
        )
