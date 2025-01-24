This is a REST API for a course management application. The API is wrtten in Python 3 and was deployed on Google Cloud Platform using Google App Engine and Datastore. Auth0 was used to register users with a JWT for user authentication. The API has 13 endpoints, most of which were protected and required a valid JWT to access. Below is a summary of the endpoints:


|Endpoint Number|Functionality|Endpoint|Protection|Description|
|---------------|-------------|--------|----------|-----------|
|1.|User login|POST /users/login|Pre-created Auth0 users with username and password|Use Auth0 to issue JWTs|
|2.|Get all users|GET /users|Admin only|Summary information of all users. No info about avatar or courses|
|3.|Get a user|GET /users/:id|Admin. Or user with JWT matching id|Detailed info about the user, including avatar (if any) and courses (for instructors and students)|
|4.|Create/update a user’s avatar|POST /users/:id/avatar|User with JWT matching id|Upload file to Google Cloud Storage|
|5.|Get a user’s avatar|GET /users/:id/avatar|User with JWT matching id|Read and return file from Google Cloud Storage|
|6.|Delete a user’s avatar|DELETE /users/:id/avatar|User with JWT matching id|Delete file from Google Cloud Storage|
|7.|Create a course|POST /courses|Admin only|Create a course|
|8.|Get all courses|GET /courses|Unprotected|Paginated using offset/limit. Page size is 3. Ordered by "subject."  Doesn’t return info on course enrollment|
|9.|Get a course|GET /courses/:id|Unprotected|Doesn’t return info on course enrollment|
|10.|Update a course|PATCH /courses/:id|Admin only|Partial update|
|11.|Delete a course|DELETE /courses/:id|Admin only|Delete course and delete enrollment info about the course|
|12.|Update enrollment in a course|PATCH /courses/:id/students|Admin. Or instructor of the course|Enroll or disenroll students from the course|
|13.|Get enrollment for a course|GET /courses/:id/students|Admin. Or instructor of the course|All students enrolled in the course|

All endpoints are handled by the main.py file. The error_handling.py file is used to verfiy if a JWT is present and valid in the request, validate the identity of users sending a request using the request JWT, gathering entities from Datastore, and sending error messages and status codes as necessary.
