#!/usr/bin/env python3

from datetime import date

from app import app
from models import Exercise, Workout, WorkoutExercise, db

with app.app_context():
    WorkoutExercise.query.delete()
    Workout.query.delete()
    Exercise.query.delete()
    db.session.commit()

    back_squat = Exercise(
        name="Back Squat",
        category="strength",
        equipment_needed=True,
    )
    deadlift = Exercise(
        name="Romanian Deadlift",
        category="strength",
        equipment_needed=True,
    )
    bike = Exercise(
        name="Stationary Bike",
        category="cardio",
        equipment_needed=True,
    )
    hip_stretch = Exercise(
        name="Hip Flexor Stretch",
        category="flexibility",
        equipment_needed=False,
    )
    single_leg = Exercise(
        name="Single-Leg Balance",
        category="balance",
        equipment_needed=False,
    )
    db.session.add_all([back_squat, deadlift, bike, hip_stretch, single_leg])
    db.session.commit()

    lower_body = Workout(
        date=date(2026, 9, 22),
        duration_minutes=50,
        notes="Lower body strength. Keep the squat depth even on every rep.",
    )
    recovery = Workout(
        date=date(2026, 9, 24),
        duration_minutes=35,
        notes="Easy cardio and mobility after practice.",
    )
    balance = Workout(
        date=date(2026, 9, 26),
        duration_minutes=40,
        notes="Balance work. Stop the set if the standing knee caves in.",
    )
    db.session.add_all([lower_body, recovery, balance])
    db.session.commit()

    db.session.add_all(
        [
            WorkoutExercise(
                workout=lower_body,
                exercise=back_squat,
                reps=5,
                sets=4,
                duration_seconds=180,
            ),
            WorkoutExercise(
                workout=lower_body,
                exercise=deadlift,
                reps=8,
                sets=3,
                duration_seconds=150,
            ),
            WorkoutExercise(
                workout=recovery,
                exercise=bike,
                reps=1,
                sets=1,
                duration_seconds=1200,
            ),
            WorkoutExercise(
                workout=recovery,
                exercise=hip_stretch,
                reps=1,
                sets=2,
                duration_seconds=45,
            ),
            WorkoutExercise(
                workout=balance,
                exercise=single_leg,
                reps=6,
                sets=3,
                duration_seconds=30,
            ),
            WorkoutExercise(
                workout=balance,
                exercise=hip_stretch,
                reps=1,
                sets=2,
                duration_seconds=40,
            ),
        ]
    )
    db.session.commit()
