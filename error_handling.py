from flask import jsonify, abort, Response
import json
from google.cloud import datastore
from google.cloud.datastore import query

from json import dumps
from six.moves.urllib.request import urlopen #type: ignore
from jose import jwt

client = datastore.Client()

ALGORITHMS = ["RS256"]
CLIENT_ID = 'dlzxwx2juCnK4yJc1u85FV9jXxM2wv6O'
DOMAIN = 'dev-k8akkp1zy7xhtz4p.us.auth0.com'

# This code is adapted from https://auth0.com/docs/quickstart/backend/python/01-authorization?_ga=2.46956069.349333901.1589042886-466012638.1589042885#create-the-jwt-validation-decorator
class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

# Decode the JWT supplied in the Authorization header
def decode_jwt(request):
    payload = verify_jwt(request)
    return payload 

def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response

# Verify the JWT in the request's Authorization header
def verify_jwt(request):
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization'].split()
        token = auth_header[1]
    else:
        raise AuthError({"code": "no auth header",
                            "description":
                                "Authorization header is missing"}, 401)
    
    jsonurl = urlopen("https://"+ DOMAIN+"/.well-known/jwks.json")
    jwks = json.loads(jsonurl.read())
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.JWTError:
        raise AuthError({"code": "invalid_header",
                        "description":
                            "Invalid header. "
                            "Use an RS256 signed JWT Access Token"}, 401)
    if unverified_header["alg"] == "HS256":
        raise AuthError({"code": "invalid_header",
                        "description":
                            "Invalid header. "
                            "Use an RS256 signed JWT Access Token"}, 401)
    rsa_key = {}
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }
    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=CLIENT_ID,
                issuer="https://"+ DOMAIN+"/"
            )
        except jwt.ExpiredSignatureError:
            raise AuthError({"code": "token_expired",
                            "description": "token is expired"}, 401)
        except jwt.JWTClaimsError:
            raise AuthError({"code": "invalid_claims",
                            "description":
                                "incorrect claims,"
                                " please check the audience and issuer"}, 401)
        except Exception:
            raise AuthError({"code": "invalid_header",
                            "description":
                                "Unable to parse authentication"
                                " token."}, 401)

        return payload
    else:
        raise AuthError({"code": "no_rsa_key",
                            "description":
                                "No RSA key in JWKS"}, 401)
    
def validate_jwt(request):
    try:
        payload = verify_jwt(request)
    except AuthError:
        error_message = {"Error": "Unauthorized"}
        abort(Response(dumps(error_message), status = 401))
    return payload

def validate_users(kind, properties, payload):
    valid_user_query = client.query(kind=kind)
    
    query_filters = []

    for key, val in properties.items():
        query_filters.append(query.PropertyFilter(key, "=", val))

    valid_user_filter = query.Or(query_filters)
    valid_user_query.add_filter(filter=valid_user_filter)
    valid_users = list(valid_user_query.fetch())
    valid_users_subs = [x['sub'] for x in valid_users]
    if payload['sub'] not in valid_users_subs:
        error_message = dumps({"Error": "You don't have permission on this resource"})
        abort(Response(error_message, status = 403))
    else:
        return

def fetch_entity(kind, id):
    entity_key = client.key(kind, id)
    entity = client.get(key=entity_key)
    if entity is None:
        error_message = dumps({"Error": "Not found"})
        abort(Response(error_message, status = 404))
    else:
        return entity, entity_key
