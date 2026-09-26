from flask import Flask, jsonify, request
from flask_migrate import Migrate
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from models import (
    Exercise,
    ExerciseSchema,
    Workout,
    WorkoutExercise,
    WorkoutExerciseSchema,
    WorkoutSchema,
    db,
)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.json.sort_keys = False

migrate = Migrate(app, db)
db.init_app(app)

exercise_schema = ExerciseSchema()
exercises_schema = ExerciseSchema(
    many=True, exclude=("workouts", "workout_exercises")
)
workout_schema = WorkoutSchema()
workouts_schema = WorkoutSchema(many=True, exclude=("exercises", "workout_exercises"))
workout_exercise_schema = WorkoutExerciseSchema()


def _json_object():
    """Return the request JSON when it is an object. Otherwise None."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None
    return data


def _validation_response(error):
    db.session.rollback()
    if isinstance(error, ValidationError):
        return jsonify({"errors": error.messages}), 400
    return jsonify({"errors": [str(error)]}), 400


@app.route("/workouts", methods=["GET"])
def get_workouts():
    """List every workout without the nested exercise graph."""
    workouts = Workout.query.order_by(Workout.date, Workout.id).all()
    return jsonify(workouts_schema.dump(workouts)), 200


@app.route("/workouts/<int:workout_id>", methods=["GET"])
def get_workout(workout_id):
    """Show one workout, its exercises, and the reps, sets, and duration on each link."""
    workout = db.session.get(Workout, workout_id)
    if workout is None:
        return jsonify({"error": "Workout not found."}), 404
    return jsonify(workout_schema.dump(workout)), 200


@app.route("/workouts", methods=["POST"])
def create_workout():
    """Create a workout from a date, a duration, and optional notes."""
    data = _json_object()
    if data is None:
        return jsonify({"errors": ["Request body must be a JSON object."]}), 400

    try:
        payload = WorkoutSchema(exclude=("exercises", "workout_exercises")).load(data)
        workout = Workout(
            date=payload["date"],
            duration_minutes=payload["duration_minutes"],
            notes=payload.get("notes"),
        )
        db.session.add(workout)
        db.session.commit()
    except (ValidationError, ValueError) as error:
        return _validation_response(error)
    except IntegrityError:
        db.session.rollback()
        return jsonify({"errors": ["Workout could not be saved."]}), 400

    return jsonify(workout_schema.dump(workout)), 201


@app.route("/workouts/<int:workout_id>", methods=["DELETE"])
def delete_workout(workout_id):
    """Delete a workout and the WorkoutExercises rows that belong to it."""
    workout = db.session.get(Workout, workout_id)
    if workout is None:
        return jsonify({"error": "Workout not found."}), 404

    db.session.delete(workout)
    db.session.commit()
    return jsonify({"message": "Workout deleted."}), 200


@app.route("/exercises", methods=["GET"])
def get_exercises():
    """List every exercise without the nested workout graph."""
    exercises = Exercise.query.order_by(Exercise.name).all()
    return jsonify(exercises_schema.dump(exercises)), 200


@app.route("/exercises/<int:exercise_id>", methods=["GET"])
def get_exercise(exercise_id):
    """Show one exercise and the workouts that use it."""
    exercise = db.session.get(Exercise, exercise_id)
    if exercise is None:
        return jsonify({"error": "Exercise not found."}), 404
    return jsonify(exercise_schema.dump(exercise)), 200


@app.route("/exercises", methods=["POST"])
def create_exercise():
    """Create a reusable exercise."""
    data = _json_object()
    if data is None:
        return jsonify({"errors": ["Request body must be a JSON object."]}), 400

    try:
        payload = ExerciseSchema(exclude=("workouts", "workout_exercises")).load(data)
        exercise = Exercise(
            name=payload["name"],
            category=payload["category"],
            equipment_needed=payload["equipment_needed"],
        )
        db.session.add(exercise)
        db.session.commit()
    except (ValidationError, ValueError) as error:
        return _validation_response(error)
    except IntegrityError:
        db.session.rollback()
        return jsonify({"errors": ["An exercise with that name already exists."]}), 400

    return jsonify(exercise_schema.dump(exercise)), 201


@app.route("/exercises/<int:exercise_id>", methods=["DELETE"])
def delete_exercise(exercise_id):
    """Delete an exercise and the WorkoutExercises rows that belong to it."""
    exercise = db.session.get(Exercise, exercise_id)
    if exercise is None:
        return jsonify({"error": "Exercise not found."}), 404

    db.session.delete(exercise)
    db.session.commit()
    return jsonify({"message": "Exercise deleted."}), 200


@app.route(
    "/workouts/<int:workout_id>/exercises/<int:exercise_id>/workout_exercises",
    methods=["POST"],
)
def add_exercise_to_workout(workout_id, exercise_id):
    """Add an exercise to a workout and record reps, sets, and duration."""
    workout = db.session.get(Workout, workout_id)
    if workout is None:
        return jsonify({"error": "Workout not found."}), 404
    exercise = db.session.get(Exercise, exercise_id)
    if exercise is None:
        return jsonify({"error": "Exercise not found."}), 404

    data = _json_object()
    if data is None:
        return jsonify({"errors": ["Request body must be a JSON object."]}), 400

    try:
        payload = WorkoutExerciseSchema(exclude=("exercise", "workout")).load(data)
        workout_exercise = WorkoutExercise(
            workout=workout,
            exercise=exercise,
            reps=payload["reps"],
            sets=payload["sets"],
            duration_seconds=payload["duration_seconds"],
        )
        db.session.add(workout_exercise)
        db.session.commit()
    except (ValidationError, ValueError) as error:
        return _validation_response(error)
    except IntegrityError:
        db.session.rollback()
        return jsonify({"errors": ["Exercise could not be added to the workout."]}), 400

    return jsonify(workout_exercise_schema.dump(workout_exercise)), 201
