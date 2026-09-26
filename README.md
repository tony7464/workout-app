# Workout Application Backend

A Flask, SQLAlchemy, and Marshmallow API for a workout tracker used by personal trainers. A workout is a dated session. Exercises are reusable across workouts. Each time a trainer adds an exercise to a workout, the join row records reps, sets, and duration in seconds.

There is no update route, and there is no route that removes an exercise from a workout. Deleting a workout or an exercise also deletes the join rows that belong to it.

## Setup

Python 3.8.13 or newer is required. This project runs on Python 3.10.

```console
pipenv install
pipenv shell
cd server
flask db upgrade
python seed.py
```

`pipenv install` creates the virtual environment from the Pipfile. From the `server` directory, `flask db upgrade` applies the migrations and creates `server/instance/app.db`. `python seed.py` loads example exercises, workouts, and workout exercises.

## Run

From the `server` directory, with the virtual environment active:

```console
flask run
```

The API listens on http://127.0.0.1:5000.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/workouts` | List every workout |
| GET | `/workouts/<id>` | Show one workout with its exercises, including reps, sets, and duration from each join row |
| POST | `/workouts` | Create a workout. JSON body: `date` (`YYYY-MM-DD`), `duration_minutes`, optional `notes` |
| DELETE | `/workouts/<id>` | Delete a workout and its workout exercises |
| GET | `/exercises` | List every exercise |
| GET | `/exercises/<id>` | Show one exercise and the workouts that use it |
| POST | `/exercises` | Create an exercise. JSON body: `name`, `category`, `equipment_needed` |
| DELETE | `/exercises/<id>` | Delete an exercise and its workout exercises |
| POST | `/workouts/<workout_id>/exercises/<exercise_id>/workout_exercises` | Add an exercise to a workout. JSON body: `reps`, `sets`, `duration_seconds` |

The add-exercise path is the assignment route `workouts/<workout_id>/exercises/<exercise_id>/workout_exercises`.

## Validations

The assignment does not list field rules. These checks are the ones this API enforces. Each layer has more than one rule.

### Table constraints

- Exercise name is unique, required, and between 1 and 80 characters.
- Exercise category must be `strength`, `cardio`, `flexibility`, or `balance`.
- Workout duration must be from 1 to 300 minutes.
- Workout notes, when present, must be from 1 to 500 characters.
- Workout exercise reps are 1 to 100, sets are 1 to 50, and duration is 1 to 7200 seconds.
- `workout_id` and `exercise_id` are required foreign keys. Deleting a workout or exercise deletes the join rows.

### Model validations

- Exercise name is required, trimmed, limited to 80 characters, and unique.
- Exercise category must be one of the four categories above.
- `equipment_needed` must be true or false.
- Workout date must be a date, and duration must be a whole number from 1 to 300.
- Notes are optional, and a provided note cannot be blank or longer than 500 characters.
- Reps, sets, and duration on a workout exercise must be whole numbers inside the ranges above.

### Schema validations

- Exercise name length is 1 to 80 characters and cannot be blank. Category must be one of the four allowed values.
- Workout duration must be a whole number from 1 to 300. Notes cannot be blank and cannot exceed 500 characters. `date` must be `YYYY-MM-DD`.
- Reps, sets, and duration on the add-exercise request must be whole numbers inside the ranges above.

Invalid JSON returns `400` with an `errors` object. A missing workout or exercise returns `404`.
