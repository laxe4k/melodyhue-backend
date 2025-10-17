from __future__ import annotations

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Iterable
from sqlalchemy.orm import Session

from app.utils.database import SessionLocal
from app.models.user import (
    User,
    UserBan,
    UserSession,
    Overlay,
    TwoFA,
    SpotifySecret,
    SpotifyToken,
    UserWarning,
    PasswordReset,
    TwoFADisable,
    LoginChallenge,
    UserSetting,
)


CLEANUP_INTERVAL_SECONDS = 24 * 3600  # 1 jour
PERMA_BAN_RETENTION_DAYS = 180


def _delete_user_full(db: Session, user_id: str) -> None:
    """Supprime un utilisateur et toutes ses données liées (sans compter sur ON DELETE CASCADE)."""
    # Ordre de suppression pour éviter les contraintes de clés étrangères
    db.query(UserSession).filter(UserSession.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(Overlay).filter(Overlay.owner_id == user_id).delete(
        synchronize_session=False
    )
    db.query(TwoFA).filter(TwoFA.user_id == user_id).delete(synchronize_session=False)
    db.query(SpotifySecret).filter(SpotifySecret.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(SpotifyToken).filter(SpotifyToken.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(UserWarning).filter(UserWarning.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(UserWarning).filter(UserWarning.moderator_id == user_id).delete(
        synchronize_session=False
    )
    db.query(UserBan).filter(UserBan.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(PasswordReset).filter(PasswordReset.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(TwoFADisable).filter(TwoFADisable.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(LoginChallenge).filter(LoginChallenge.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(UserSetting).filter(UserSetting.user_id == user_id).delete(
        synchronize_session=False
    )
    # Enfin, supprimer l'utilisateur
    db.query(User).filter(User.id == user_id).delete(synchronize_session=False)


def purge_permanent_banned_users(now: datetime | None = None) -> int:
    """Supprime tous les comptes bannis sans date de fin depuis >= 180 jours.

    Retourne le nombre d'utilisateurs supprimés.
    """
    cutoff = (now or datetime.utcnow()) - timedelta(days=PERMA_BAN_RETENTION_DAYS)
    db = SessionLocal()
    deleted_users = 0
    try:
        # Sélectionner les bans permanents (until IS NULL), non révoqués, plus vieux que le cutoff
        bans: Iterable[UserBan] = (
            db.query(UserBan)
            .filter(
                UserBan.until.is_(None),
                UserBan.revoked_at.is_(None),
                UserBan.created_at <= cutoff,
            )
            .all()
        )
        user_ids = {b.user_id for b in bans}
        for uid in user_ids:
            try:
                _delete_user_full(db, uid)
                deleted_users += 1
            except Exception:
                logging.exception(
                    "Erreur lors de la suppression complète de l'utilisateur %s", uid
                )
        db.commit()
        return deleted_users
    except Exception:
        db.rollback()
        logging.exception(
            "Erreur pendant la purge des utilisateurs bannis de manière permanente"
        )
        return deleted_users
    finally:
        db.close()


async def cleanup_scheduler(stop_event: asyncio.Event | None = None) -> None:
    """Tâche asynchrone qui exécute la purge chaque jour."""
    while True:
        try:
            n = purge_permanent_banned_users()
            if n:
                logging.info("Purge perma-ban: %d utilisateur(s) supprimé(s)", n)
        except Exception:
            logging.exception("cleanup_scheduler: exception inattendue")
        # Attendre l'intervalle ou un ordre d'arrêt
        try:
            if stop_event is None:
                await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
            else:
                try:
                    await asyncio.wait_for(
                        stop_event.wait(), timeout=CLEANUP_INTERVAL_SECONDS
                    )
                    # stop_event déclenché
                    break
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            break
