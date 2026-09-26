from datetime import date, datetime

from flask_sqlalchemy import SQLAlchemy
from marshmallow import EXCLUDE, Schema, ValidationError, fields
from marshmallow import validates as schema_validates
from marshmallow.validate import Length, OneOf, Range
from sqlalchemy import CheckConstraint, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import validates

db = SQLAlchemy()

# Categories a trainer can assign. Table, model, and schema checks all use this list.
ALLOWED_CATEGORIES = ("strength", "cardio", "flexibility", "balance")


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    """SQLite ignores foreign keys unless this pragma is turned on per connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _positive_int(value, label, maximum):
    """Reject booleans and anything that is not a whole number in range."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be a whole number.")
    if value < 1 or value > maximum:
        raise ValueError(f"{label} must be between 1 and {maximum}.")
    return value


class Exercise(db.Model):
    __tablename__ = "exercises"

    __table_args__ = (
        db.UniqueConstraint("name", name="uq_exercises_name"),
        CheckConstraint(
            "category IN ('strength', 'cardio', 'flexibility', 'balance')",
            name="ck_exercises_category",
        ),
        CheckConstraint(
            "length(name) >= 1 AND length(name) <= 80",
            name="ck_exercises_name_length",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    category = db.Column(db.String, nullable=False)
    equipment_needed = db.Column(db.Boolean, nullable=False)

    workout_exercises = db.relationship(
        "WorkoutExercise",
        back_populates="exercise",
        cascade="all, delete-orphan",
        order_by="WorkoutExercise.id",
    )
    # An exercise has many workouts through the join table.
    workouts = association_proxy("workout_exercises", "workout")

    @validates("name")
    def validate_name(self, _key, name):
        """Require a non-blank name that no other exercise already uses."""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Exercise must have a name.")
        cleaned = name.strip()
        if len(cleaned) > 80:
            raise ValueError("Exercise name must be 80 characters or fewer.")

        with db.session.no_autoflush:
            existing = Exercise.query.filter(Exercise.name == cleaned).first()
        if existing is not None and existing is not self:
            raise ValueError("Exercise name must be unique.")
        return cleaned

    @validates("category")
    def validate_category(self, _key, category):
        """Allow only the trainer categories stored in the table check."""
        if category not in ALLOWED_CATEGORIES:
            raise ValueError(
                "Category must be strength, cardio, flexibility, or balance."
            )
        return category

    @validates("equipment_needed")
    def validate_equipment_needed(self, _key, equipment_needed):
        """Store a real boolean. SQLite may hand back 0 or 1 when a row is loaded."""
        if equipment_needed is True or equipment_needed is False:
            return equipment_needed
        if equipment_needed in (0, 1) and not isinstance(equipment_needed, bool):
            return bool(equipment_needed)
        raise ValueError("Equipment needed must be true or false.")

    def __repr__(self):
        return f"<Exercise {self.id}, {self.name}>"


class Workout(db.Model):
    __tablename__ = "workouts"

    __table_args__ = (
        CheckConstraint(
            "duration_minutes >= 1 AND duration_minutes <= 300",
            name="ck_workouts_duration_minutes",
        ),
        CheckConstraint(
            "notes IS NULL OR (length(notes) >= 1 AND length(notes) <= 500)",
            name="ck_workouts_notes_length",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text)

    workout_exercises = db.relationship(
        "WorkoutExercise",
        back_populates="workout",
        cascade="all, delete-orphan",
        order_by="WorkoutExercise.id",
    )
    # A workout has many exercises through the join table.
    exercises = association_proxy("workout_exercises", "exercise")

    @validates("date")
    def validate_date(self, _key, workout_date):
        """Require a calendar date. A datetime is not a workout date."""
        if isinstance(workout_date, datetime) or not isinstance(workout_date, date):
            raise ValueError("Workout date must be a date.")
        return workout_date

    @validates("duration_minutes")
    def validate_duration_minutes(self, _key, duration_minutes):
        """Keep a session between 1 and 300 minutes."""
        return _positive_int(duration_minutes, "Duration", 300)

    @validates("notes")
    def validate_notes(self, _key, notes):
        """Notes are optional, but a provided note has to be real text within 500 characters."""
        if notes is None:
            return None
        if not isinstance(notes, str):
            raise ValueError("Notes must be text.")
        if notes.strip() == "":
            raise ValueError("Notes cannot be blank.")
        if len(notes) > 500:
            raise ValueError("Notes must be 500 characters or fewer.")
        return notes

    def __repr__(self):
        return f"<Workout {self.id}, {self.date}>"


class WorkoutExercise(db.Model):
    """One row in the WorkoutExercises join table.

    The row belongs to one workout and one exercise and records how that
    exercise was performed: reps, sets, and duration.
    """

    __tablename__ = "workout_exercises"

    __table_args__ = (
        CheckConstraint(
            "reps >= 1 AND reps <= 100",
            name="ck_workout_exercises_reps",
        ),
        CheckConstraint(
            "sets >= 1 AND sets <= 50",
            name="ck_workout_exercises_sets",
        ),
        CheckConstraint(
            "duration_seconds >= 1 AND duration_seconds <= 7200",
            name="ck_workout_exercises_duration_seconds",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(
        db.Integer,
        db.ForeignKey("workouts.id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise_id = db.Column(
        db.Integer,
        db.ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
    )
    reps = db.Column(db.Integer, nullable=False)
    sets = db.Column(db.Integer, nullable=False)
    duration_seconds = db.Column(db.Integer, nullable=False)

    workout = db.relationship("Workout", back_populates="workout_exercises")
    exercise = db.relationship("Exercise", back_populates="workout_exercises")

    @validates("reps")
    def validate_reps(self, _key, reps):
        return _positive_int(reps, "Reps", 100)

    @validates("sets")
    def validate_sets(self, _key, sets):
        return _positive_int(sets, "Sets", 50)

    @validates("duration_seconds")
    def validate_duration_seconds(self, _key, duration_seconds):
        return _positive_int(duration_seconds, "Duration", 7200)

    def __repr__(self):
        return (
            f"<WorkoutExercise {self.id}, workout={self.workout_id}, "
            f"exercise={self.exercise_id}>"
        )


class ExerciseSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=Length(min=1, max=80))
    category = fields.Str(required=True, validate=OneOf(list(ALLOWED_CATEGORIES)))
    equipment_needed = fields.Bool(required=True)
    workouts = fields.List(
        fields.Nested(
            lambda: WorkoutSchema(only=("id", "date", "duration_minutes", "notes"))
        ),
        dump_only=True,
    )
    workout_exercises = fields.List(
        fields.Nested(lambda: WorkoutExerciseSchema(exclude=("exercise",))),
        dump_only=True,
    )

    @schema_validates("name")
    def validate_name(self, value, **_kwargs):
        if not value.strip():
            raise ValidationError("Exercise name cannot be blank.")

    @schema_validates("category")
    def validate_category(self, value, **_kwargs):
        if value not in ALLOWED_CATEGORIES:
            raise ValidationError(
                "Category must be strength, cardio, flexibility, or balance."
            )


class WorkoutSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int(dump_only=True)
    date = fields.Date(required=True)
    duration_minutes = fields.Int(required=True, validate=Range(min=1, max=300))
    notes = fields.Str(validate=Length(max=500), allow_none=True)
    exercises = fields.List(
        fields.Nested(
            lambda: ExerciseSchema(only=("id", "name", "category", "equipment_needed"))
        ),
        dump_only=True,
    )
    workout_exercises = fields.List(
        fields.Nested(lambda: WorkoutExerciseSchema(exclude=("workout",))),
        dump_only=True,
    )

    @schema_validates("duration_minutes")
    def validate_duration_minutes(self, value, **_kwargs):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError("Duration must be a whole number of minutes.")
        if value < 1 or value > 300:
            raise ValidationError("Duration must be between 1 and 300 minutes.")

    @schema_validates("notes")
    def validate_notes(self, value, **_kwargs):
        if value is not None and value.strip() == "":
            raise ValidationError("Notes cannot be blank.")


class WorkoutExerciseSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int(dump_only=True)
    workout_id = fields.Int(dump_only=True)
    exercise_id = fields.Int(dump_only=True)
    reps = fields.Int(required=True, validate=Range(min=1, max=100))
    sets = fields.Int(required=True, validate=Range(min=1, max=50))
    duration_seconds = fields.Int(required=True, validate=Range(min=1, max=7200))
    exercise = fields.Nested(
        lambda: ExerciseSchema(only=("id", "name", "category", "equipment_needed")),
        dump_only=True,
    )
    workout = fields.Nested(
        lambda: WorkoutSchema(only=("id", "date", "duration_minutes", "notes")),
        dump_only=True,
    )

    @schema_validates("reps")
    def validate_reps(self, value, **_kwargs):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValidationError("Reps must be a whole number of at least 1.")

    @schema_validates("sets")
    def validate_sets(self, value, **_kwargs):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValidationError("Sets must be a whole number of at least 1.")

    @schema_validates("duration_seconds")
    def validate_duration_seconds(self, value, **_kwargs):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValidationError("Duration must be a whole number of seconds.")
