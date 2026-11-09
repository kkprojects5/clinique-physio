"""Exercise library, programs and check-offs (B-EXE-01 to 04).

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-09 12:20:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Starter library: general exercises, no patient data (reference data, like a lookup table).
EXERCISES = [
    (
        "Pont fessier",
        "Glute bridge",
        "Renforce les fessiers et le bas du dos.",
        "Strengthens the glutes and lower back.",
        "Couché sur le dos, genoux pliés, soulevez le bassin jusqu'à aligner épaules, hanches et "
        "genoux. Tenez 2 secondes, redescendez lentement.",
        "Lie on your back, knees bent. Lift your hips until shoulders, hips and knees are in "
        "line. Hold 2 seconds, lower slowly.",
        3,
        12,
    ),
    (
        "Squat au mur",
        "Wall sit",
        "Renforce les quadriceps sans impact.",
        "Strengthens the thighs without impact.",
        "Dos contre le mur, descendez jusqu'à ce que les genoux soient pliés à environ 60 degrés. "
        "Tenez 20 à 30 secondes.",
        "Back against a wall, slide down until your knees are bent about 60 degrees. "
        "Hold 20 to 30 seconds.",
        3,
        5,
    ),
    (
        "Mollets debout",
        "Standing calf raise",
        "Renforce les mollets et améliore l'équilibre.",
        "Strengthens the calves and balance.",
        "Debout, tenez-vous à une chaise. Montez sur la pointe des pieds, puis redescendez "
        "lentement.",
        "Stand holding a chair. Rise onto your toes, then lower slowly.",
        3,
        15,
    ),
    (
        "Rotation externe de l'épaule",
        "Shoulder external rotation",
        "Renforce la coiffe des rotateurs.",
        "Strengthens the rotator cuff.",
        "Coude collé au corps et plié à 90 degrés, tirez un élastique vers l'extérieur sans "
        "décoller le coude, puis revenez lentement.",
        "Elbow at your side, bent 90 degrees. Pull an elastic band outwards without moving the "
        "elbow, then return slowly.",
        3,
        12,
    ),
    (
        "Chat-vache",
        "Cat-cow",
        "Assouplit la colonne vertébrale.",
        "Loosens the spine.",
        "À quatre pattes, arrondissez le dos en rentrant le menton, puis creusez le dos en "
        "regardant devant. Bougez lentement avec la respiration.",
        "On hands and knees, round your back and tuck your chin, then arch your back and look "
        "ahead. Move slowly with your breathing.",
        2,
        10,
    ),
    (
        "Étirement des ischio-jambiers",
        "Hamstring stretch",
        "Assouplit l'arrière de la cuisse.",
        "Stretches the back of the thigh.",
        "Assis, une jambe tendue devant vous, penchez-vous doucement vers l'avant, dos droit, "
        "jusqu'à sentir l'étirement. Tenez 30 secondes.",
        "Sitting with one leg straight in front, lean forward gently with a straight back until "
        "you feel the stretch. Hold 30 seconds.",
        2,
        3,
    ),
    (
        "Équilibre sur une jambe",
        "Single-leg balance",
        "Améliore la stabilité de la cheville et du genou.",
        "Improves ankle and knee stability.",
        "Près d'un appui, tenez-vous sur une jambe 30 secondes. Changez de jambe.",
        "Near a support, stand on one leg for 30 seconds. Switch legs.",
        3,
        2,
    ),
    (
        "Extension de genou assis",
        "Seated knee extension",
        "Renforce le quadriceps après une blessure au genou.",
        "Strengthens the thigh after a knee injury.",
        "Assis sur une chaise, tendez lentement une jambe à l'horizontale, tenez 3 secondes, "
        "puis redescendez.",
        "Sitting on a chair, slowly straighten one leg, hold 3 seconds, then lower it.",
        3,
        10,
    ),
]


def upgrade() -> None:
    op.create_table(
        "exercises",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name_fr", sa.Text(), nullable=False),
        sa.Column("name_en", sa.Text(), nullable=False),
        sa.Column("description_fr", sa.Text(), nullable=False),
        sa.Column("description_en", sa.Text(), nullable=False),
        sa.Column("instructions_fr", sa.Text(), nullable=False),
        sa.Column("instructions_en", sa.Text(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("default_sets", sa.SmallInteger(), nullable=False),
        sa.Column("default_reps", sa.SmallInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.CheckConstraint("default_reps BETWEEN 1 AND 100", name="ck_exercises_reps"),
        sa.CheckConstraint("default_sets BETWEEN 1 AND 10", name="ck_exercises_sets"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "programs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("therapist_id", sa.UUID(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("weeks", sa.SmallInteger(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("weeks BETWEEN 1 AND 26", name="ck_programs_weeks"),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
        ),
        sa.ForeignKeyConstraint(
            ["therapist_id"],
            ["therapists.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_programs_patient_id"), "programs", ["patient_id"], unique=False)
    op.create_table(
        "program_items",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("program_id", sa.UUID(), nullable=False),
        sa.Column("exercise_id", sa.UUID(), nullable=False),
        sa.Column("sets", sa.SmallInteger(), nullable=False),
        sa.Column("reps", sa.SmallInteger(), nullable=False),
        sa.Column("times_per_week", sa.SmallInteger(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint("reps BETWEEN 1 AND 100", name="ck_program_items_reps"),
        sa.CheckConstraint("sets BETWEEN 1 AND 10", name="ck_program_items_sets"),
        sa.CheckConstraint("times_per_week BETWEEN 1 AND 14", name="ck_program_items_frequency"),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["programs.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_program_items_program_id"), "program_items", ["program_id"], unique=False
    )
    op.create_table(
        "exercise_logs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("program_item_id", sa.UUID(), nullable=False),
        sa.Column("done_on", sa.Date(), nullable=False),
        sa.Column(
            "done_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("pain_level", sa.SmallInteger(), nullable=True),
        sa.CheckConstraint("pain_level BETWEEN 0 AND 10", name="ck_exercise_logs_pain"),
        sa.ForeignKeyConstraint(
            ["program_item_id"],
            ["program_items.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("program_item_id", "done_on", name="uq_exercise_logs_once_per_day"),
    )
    op.create_index(
        op.f("ix_exercise_logs_program_item_id"), "exercise_logs", ["program_item_id"], unique=False
    )

    exercises = sa.table(
        "exercises",
        sa.column("name_fr"),
        sa.column("name_en"),
        sa.column("description_fr"),
        sa.column("description_en"),
        sa.column("instructions_fr"),
        sa.column("instructions_en"),
        sa.column("default_sets"),
        sa.column("default_reps"),
    )
    op.bulk_insert(
        exercises,
        [
            dict(
                zip(
                    (
                        "name_fr",
                        "name_en",
                        "description_fr",
                        "description_en",
                        "instructions_fr",
                        "instructions_en",
                        "default_sets",
                        "default_reps",
                    ),
                    row,
                    strict=True,
                )
            )
            for row in EXERCISES
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_exercise_logs_program_item_id"), table_name="exercise_logs")
    op.drop_table("exercise_logs")
    op.drop_index(op.f("ix_program_items_program_id"), table_name="program_items")
    op.drop_table("program_items")
    op.drop_index(op.f("ix_programs_patient_id"), table_name="programs")
    op.drop_table("programs")
    op.drop_table("exercises")
