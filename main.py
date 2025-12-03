from flask import Flask, request, jsonify, url_for
from google.cloud import datastore, storage
from error_handling import *

import requests
import logging
import os

from authlib.integrations.flask_client import OAuth

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')
app.logger.setLevel(logging.DEBUG)

client = datastore.Client()

USERS = "users"
COURSES = "courses"
AVATAR_BUCKET = os.getenv('AVATAR_BUCKET',)

CLIENT_ID = os.getenv('AUTH0_CLIENT_ID')
CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET')
DOMAIN = os.getenv('AUTH0_DOMAIN')

if not all([CLIENT_ID, CLIENT_SECRET, DOMAIN]):
    raise ValueError('Auth0 environment variables (AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_DOMAIN) must be set')


ALGORITHMS = ["RS256"]

oauth = OAuth(app)

auth0 = oauth.register(
    'auth0',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    api_base_url="https://" + DOMAIN,
    access_token_url="https://" + DOMAIN + "/oauth/token",
    authorize_url="https://" + DOMAIN + "/authorize",
    client_kwargs={
        'scope': 'openid profile email',
    },
)

@app.route('/')
def index():
    return "Please navigate to /users/login to use this API"

def query_by_role(role):
    query = client.query(kind=USERS)
    query.add_filter(filter=datastore.query.PropertyFilter("role", "=", role))
    users = list(query.fetch())
    return users

@app.route('/users/login', methods=['POST'])
def login_user():
    content = request.get_json()

    try:
        username = content["username"]
        password = content["password"]
    except KeyError:
        return {"Error": "The request body is invalid"}, 400

    body = {'grant_type':'password','username':username,
            'password':password,
            'client_id':CLIENT_ID,
            'client_secret':CLIENT_SECRET
           }
    headers = { 'content-type': 'application/json' }
    url = 'https://' + DOMAIN + '/oauth/token'
    r = requests.post(url, json=body, headers=headers)

    try:
        token = r.json()['id_token']
    except KeyError:
        return {"Error": "Unauthorized"}, 401

    return {"token": token}, 200, {'Content-Type':'application/json'}

#Get all users
@app.route('/' + USERS, methods=['GET'])
def get_users():

    #Verify jwt exists and is valid
    payload = validate_jwt(request)

    #Query datastore to find the admin. Cross-reference with JWT provided in the request
    query_properties = {'role': 'admin'}
    validate_users(USERS, query_properties, payload)

    #Create a list of users and return
    query = client.query(kind=USERS)
    results = list(query.fetch())
    sanitized_results = []
    for r in results:
        sanitized_r = dict(r)
        sanitized_r.pop('avatar_file_name', None)
        sanitized_r['id'] = r.key.id
        sanitized_results.append(sanitized_r)
    return jsonify(sanitized_results), 200, {'Content-Type':'application/json'}

#Get a user
@app.route('/' + USERS + '/<int:id>', methods=['GET'])
def get_user(id):
    user, user_key = fetch_entity(USERS, id)

    payload = validate_jwt(request)

    query_properties = {'role': 'admin', '__key__': user_key}
    validate_users(USERS, query_properties, payload)

    course_query = client.query(kind=COURSES)
    courses = list(course_query.fetch())
    user_courses = []

    if user['role'] == 'student':
        for c in courses:
            try:
                if id in c['enrolled']:
                    user_courses.append(url_for('get_course', course_id=c.key.id, _external=True))
            except KeyError:
                continue
    elif user['role'] == 'instructor':
        for c in courses:
            if id == c['instructor_id']:
                user_courses.append(url_for('get_course', course_id=c.key.id, _external=True))
    else:
        del user['avatar_file_name']
        user['id'] = user.key.id
        return user

    if user.get('avatar_file_name'):
        user['avatar_url'] = url_for('get_avatar', id=user.key.id, _external=True)
    del user['avatar_file_name']
    user['courses'] = user_courses
    user['id'] = user.key.id
    return user


@app.route('/' + USERS + '/<int:id>/avatar', methods=['POST', 'GET', 'DELETE'])
def route_avatar(id):
    if request.method == "GET":
        return get_avatar(id)
    elif request.method == "POST":
        return update_avatar(id)
    else:
        return delete_avatar(id)


#Create/update user's avatar
@app.route('/' + USERS + '/<int:id>/avatar', methods=['POST'])
def update_avatar(id):
    if 'file' not in request.files:
        return {"Error": "The request body is invalid"}, 400

    payload = validate_jwt(request)

    user, user_key = fetch_entity(USERS, id)

    query_properties = {'role': 'admin', '__key__': user_key}
    validate_users(USERS, query_properties, payload)

    file_obj = request.files['file']

    storage_client = storage.Client()
    bucket = storage_client.bucket(AVATAR_BUCKET, 'assignment-6-tarpaulin')
    if user.get('avatar_file_name'):
        blob = bucket.blob(user['avatar_file_name'])
        blob.delete()
    blob = bucket.blob(file_obj.filename)
    file_obj.seek(0)
    blob.upload_from_file(file_obj)

    user.update({'avatar_file_name': file_obj.filename})
    client.put(user)

    return ({"avatar_url": url_for('get_avatar', id=user.key.id, _external=True)}, 200)

#Get a user's avatar
@app.route('/' + USERS + '/<int:id>/avatar', methods=['GET'])
def get_avatar(id):
    payload = validate_jwt(request)

    user, user_key = fetch_entity(USERS, id)

    query_properties = {'__key__': user_key}
    validate_users(USERS, query_properties, payload)

    if not user.get('avatar_file_name'):
        return {"Error": "Not found"}, 404

    return ({"avatar_url": url_for('get_avatar', id=user.key.id, _external=True)}, 200)

@app.route('/' + USERS + '/<int:id>/avatar', methods=['DELETE'])
def delete_avatar(id):
    payload = validate_jwt(request)

    user, user_key = fetch_entity(USERS, id)

    query_properties = {'__key__': user_key}
    validate_users(USERS, query_properties, payload)

    if not user.get('avatar_file_name'):
        return {"Error": "Not found"}, 404

    storage_client = storage.Client()
    bucket = storage_client.bucket(AVATAR_BUCKET, 'assignment-6-tarpaulin')
    blob = bucket.blob(user['avatar_file_name'])
    blob.delete()
    user['avatar_file_name'] = None
    client.put(user)
    return '',204

# Courses API ----------------------------------------------------------------------

#Create a course
@app.route('/' + COURSES, methods=['POST'])
def create_course():
    content = request.get_json()
    new_course = datastore.Entity(key=client.key(COURSES))

    payload = validate_jwt(request)

    query_properties = {'role': 'admin'}
    validate_users(USERS, query_properties, payload)

    instructors = query_by_role('instructor')
    for inst in instructors:
        inst["id"] = inst.key.id
    instructor_ids = [x["id"] for x in instructors]
    if content['instructor_id'] not in instructor_ids:
        return {"Error": "The request body is invalid"}, 400

    try:
        new_course.update({
            'subject': content['subject'],
            'number': int(content['number']),
            'title': content['title'],
            'term': content['term'],
            'instructor_id': content['instructor_id']
        })
    except KeyError:
        return {"Error": "The request body is invalid"}, 400

    new_course.update({'enrolled': []})

    #Remove 'enrolled' from the response returned
    client.put(new_course)
    response_course = {}
    for key, value in new_course.items():
        if key != 'enrolled':
            response_course[key] = value
    response_course['id'] = new_course.key.id
    response_course['self'] = url_for('get_course', course_id=new_course.key.id, _external=True)
    return (response_course, 201)

#Get, update, or delete a course
@app.route('/' + COURSES + '/<int:course_id>', methods=["PATCH","GET", "DELETE"])
def route_course(course_id):
    if request.method == "GET":
        return get_course(course_id)
    elif request.method == "PATCH":
        return update_course(course_id)
    else:
        return delete_course(course_id)

#Get a course
@app.route('/' + COURSES + '/<int:course_id>', methods=["GET"])
def get_course(course_id):
    course = fetch_entity(COURSES, course_id)[0]
    response_course = {}
    for key, value in course.items():
        if key != 'enrolled':
            response_course[key] = value
    response_course['id'] = course.key.id
    response_course['self'] = url_for('get_course', course_id=course.key.id, _external=True)
    return response_course

#Update a course
@app.route('/' + COURSES + '/<int:course_id>', methods=["PATCH"])
def update_course(course_id):
    content = request.get_json()

    payload = validate_jwt(request)

    query_properties = {'role': 'admin'}
    validate_users(USERS, query_properties, payload)

    course = fetch_entity(COURSES, course_id)[0]

    instructors = query_by_role('instructor')
    for inst in instructors:
        inst["id"] = inst.key.id
    instructor_ids = [x["id"] for x in instructors]

    for key, value in content.items():
        if key == "instructor_id" and value not in instructor_ids:
            return {"Error": "The request body is invalid"}, 400
        if key in course:
            course.update({key: value})

    client.put(course)
    response_course = {}
    for key, value in course.items():
        if key != 'enrolled':
            response_course[key] = value
    response_course['id'] = course.key.id
    response_course['self'] = url_for('get_course', course_id=course.key.id, _external=True)
    return response_course, 200

#Delete a course
@app.route('/' + COURSES + '/<int:course_id>', methods=["DELETE"])
def delete_course(course_id):

    payload = validate_jwt(request)

    query_properties = {'role': 'admin'}
    validate_users(USERS, query_properties, payload)

    course_key = fetch_entity(COURSES, course_id)[1]

    client.delete(course_key)
    return ('', 204)

#Get all courses
@app.route('/' + COURSES, methods=['GET'])
def get_all_courses():
    limit = int(request.args.get('limit', default = 3))
    offset = int(request.args.get('offset', default=0))

    query = client.query(kind=COURSES)
    query.order = ['subject']
    courses = list(query.fetch(offset=offset, limit=limit))

    for c in courses:
        del c['enrolled']
        c['id'] = c.key.id
        c['self'] = url_for('get_course', course_id=c.key.id, _external=True)

    new_offset = limit + offset
    next = url_for('get_all_courses', limit=limit, offset=new_offset, _external = True)

    return jsonify({
    "courses": courses,
    "next": next
    }), 200

#Update or get enrollment
@app.route('/' + COURSES + '/<int:course_id>/students', methods=["PATCH","GET"])
def route_enrollment(course_id):
    if request.method == "GET":
        return get_enrollment(course_id)
    else:
        return update_enrollment(course_id)

#Get enrollment
@app.route('/' + COURSES + '/<int:course_id>/students', methods=["GET"])
def get_enrollment(course_id):
    course = fetch_entity(COURSES, course_id)[0]

    payload = validate_jwt(request)

    query_properties = {'role': 'admin', '__key__': client.key(USERS, course['instructor_id'])}
    validate_users(USERS, query_properties, payload)

    return course['enrolled'], 200


#Update enrollment
@app.route('/' + COURSES + '/<int:course_id>/students', methods=["PATCH"])
def update_enrollment(course_id):

    payload = validate_jwt(request)

    content = request.get_json()

    course = fetch_entity(COURSES, course_id)[0]

    query_properties = {'role': 'admin', '__key__': client.key(USERS, course['instructor_id'])}
    validate_users(USERS, query_properties, payload)

    students = query_by_role('student')
    student_ids = [std.key.id for std in students]

    enrolled_list = course['enrolled']
    for student in content['add']:
        if student in content['remove'] or student not in student_ids:
            return {"Error": "Enrollment data is invalid"}, 409
        elif student in enrolled_list:
            continue
        else:
            enrolled_list.append(student)

    for student in content['remove']:
        if student not in student_ids:
            return {"Error": "Enrollment data is invalid"}, 409
        if student not in course['enrolled']:
            continue
        enrolled_list.remove(student)

    course.update({'enrolled': enrolled_list})
    client.put(course)

    return ('', 200)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)