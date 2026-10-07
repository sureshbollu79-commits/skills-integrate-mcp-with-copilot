# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Teachers can sign up or unregister students after signing in
- Students can browse activities and participants without signing in

## Getting Started

1. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Configure a session-signing key and add a teacher account. The account file stores password hashes and is ignored by Git:

   ```
   export SESSION_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
   python -m src.auth teacher1
   ```

   The command prompts for the teacher password twice and writes `src/teachers.json`. Set `TEACHER_CREDENTIALS_FILE` to use another path. For HTTPS deployments, set `COOKIE_SECURE=true`.

3. From the repository root, run the application:

   ```
   uvicorn src.app:app --reload
   ```

4. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| GET    | `/auth/session`                                                   | Get the current teacher sign-in state                               |
| POST   | `/auth/login`                                                     | Sign in a teacher using a username and password JSON body           |
| POST   | `/auth/logout`                                                    | Sign out the current teacher                                        |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Teacher-only student signup                                         |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Teacher-only student removal                                     |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activity and participant data is stored in memory, which means it resets when the server restarts. Teacher password hashes are stored separately in the local credentials JSON file.
