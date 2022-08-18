import random
import string
from uuid import uuid4

import fastapi
import passlib.hash as _hash
import sqlalchemy.orm as orm
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request, status
from starlette.config import Config

from bigfastapi.db.database import get_db
from bigfastapi.services import auth_service
from bigfastapi.utils import settings

from .models import user_models

app = APIRouter(tags=["Social_Auth"])


# OAuth settings
GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
if GOOGLE_CLIENT_ID is None or GOOGLE_CLIENT_SECRET is None:
    raise BaseException("Missing env variables")

# Set up OAuth
config_data = {
    "GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID,
    "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET,
}
starlette_config = Config(environ=config_data)
oauth = OAuth(starlette_config)
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# Set up the middleware to read the request session
SECRET_KEY = settings.JWT_SECRET
BASE_URL = settings.BASE_URL

# Error
CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Google oauth error",
    headers={"WWW-Authenticate": "Bearer"},
)


@app.get("/google/generate_url")
async def google_login(request: Request):
    # This creates the url for our /auth endpoint
    redirect_uri = f"{settings.API_URL}/google/token"
    google_auth_uri = await oauth.google.authorize_redirect(request, redirect_uri)

    return {"data": google_auth_uri}


@app.get("/google/token")
async def google_auth(request: Request, db: orm.Session = fastapi.Depends(get_db)):

    access_token = await oauth.google.authorize_access_token(request)
    user_data = await oauth.google.parse_id_token(request, access_token)

    check_user = auth_service.valid_email_from_db(user_data["email"], db)

    if check_user:
        # user_id = str(check_user.id)
        # access_token = await create_access_token(data={"user_id": check_user.id}, db=db)
        # response = f"{BASE_URL}/app/google/authenticate?token={access_token}&user_id={user_id}"

        return {"data": check_user, "access_token": access_token}

    S = 10
    ran = "".join(random.choices(string.ascii_uppercase + string.digits, k=S))
    n = str(ran)

    user_obj = user_models.User(
        id=uuid4().hex,
        email=user_data.email,
        password=_hash.sha256_crypt.hash(n),
        first_name=user_data.given_name,
        last_name=user_data.family_name,
        phone_number=n,
        is_active=True,
        is_verified=True,
        country_code="",
        is_deleted=False,
        country="",
        state="",
        google_id="",
        google_image=user_data.picture,
        image=user_data.picture,
        device_id="",
    )

    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)

    access_token["id_token"]
    # response = f"{BASE_URL}/app/google/authenticate?token={token}&user_id={user_obj.id}"

    return {"data": user_obj, "access_token": access_token}
