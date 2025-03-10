import os
import requests
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080/auth")
REALM_NAME = os.getenv("REALM_NAME", "master")


class KeycloakBearerAuth(HTTPBearer):
    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        credentials = await super().__call__(request)
        if credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=403, detail="Invalid auth. Bearer token required.")

        token = credentials.credentials
        userinfo_url = f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/userinfo"
        try:
            resp = requests.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=5
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")

            user_info = resp.json()
            request.state.user = user_info
        except requests.RequestException:
            raise HTTPException(status_code=503, detail="Keycloak not available")

        return credentials
