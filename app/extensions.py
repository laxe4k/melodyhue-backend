#!/usr/bin/env python3
"""
Extensions partagées (DB, migrations, sécurité)
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from argon2 import PasswordHasher, Type

db = SQLAlchemy()
migrate = Migrate()

# Argon2id (Type.ID)
password_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=102400,
    parallelism=8,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)
