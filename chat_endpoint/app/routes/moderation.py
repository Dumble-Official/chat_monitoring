from fastapi import APIRouter, Request, Depends, HTTPException
from app.models.schemas import (
    ModerateRequest,
    ModerateResponse,
    UserStatusResponse,
    ResetUserRequest,
)
from app.models.db_models import BanStatus
from app.services.mongo_service import MongoService
from app.auth import verify_jwt

router = APIRouter(tags=["Moderation"])

# Single shared MongoService instance
_mongo = MongoService()


async def get_mongo() -> MongoService:
    return _mongo


# ─────────────────────────────────────────────────────────────
# POST /moderate  ← main endpoint your backend will call
# ─────────────────────────────────────────────────────────────
@router.post("/moderate", response_model=ModerateResponse)
async def moderate_message(
    body: ModerateRequest,
    request: Request,
    _token=Depends(verify_jwt),
    mongo: MongoService = Depends(get_mongo),
):
    model_service = request.app.state.model_service

    # 1. Check if user is already banned
    user = await mongo.get_or_create_user(body.user_id)
    is_banned, ban_msg = await mongo.is_banned(user)

    if is_banned:
        # Refresh user doc after potential ban-lift check
        user = await mongo.get_user(body.user_id)
        return ModerateResponse(
            user_id=body.user_id,
            label="Warning",
            confidence=1.0,
            action=_ban_action(user["ban_status"]),
            warning_count=user["warning_count"],
            ban_status=user["ban_status"],
            ban_expires_at=user.get("ban_expires_at"),
            message_to_user=ban_msg,
        )

    # 2. Run model inference
    label, confidence = model_service.predict(body.message)

    # 3. Safe message → allow
    if label == "Safe":
        await mongo.save_log(
            user_id=body.user_id,
            message=body.message,
            label=label,
            confidence=confidence,
            warning_count_after=user.get("warning_count", 0),
            ban_applied=None,
        )
        return ModerateResponse(
            user_id=body.user_id,
            label="Safe",
            confidence=confidence,
            action="allow",
            warning_count=user.get("warning_count", 0),
            ban_status=BanStatus.NONE,
            ban_expires_at=None,
            message_to_user=None,
        )

    # 4. Warning message → apply ban logic
    new_count, ban_status, ban_expires, msg_to_user = await mongo.apply_warning(body.user_id)

    await mongo.save_log(
        user_id=body.user_id,
        message=body.message,
        label=label,
        confidence=confidence,
        warning_count_after=new_count,
        ban_applied=ban_status,
    )

    return ModerateResponse(
        user_id=body.user_id,
        label="Warning",
        confidence=confidence,
        action=_ban_action(ban_status),
        warning_count=new_count,
        ban_status=ban_status,
        ban_expires_at=ban_expires,
        message_to_user=msg_to_user,
    )


# ─────────────────────────────────────────────────────────────
# GET /user/{user_id}/status
# ─────────────────────────────────────────────────────────────
@router.get("/user/{user_id}/status", response_model=UserStatusResponse)
async def get_user_status(
    user_id: str,
    _token=Depends(verify_jwt),
    mongo: MongoService = Depends(get_mongo),
):
    user = await mongo.get_or_create_user(user_id)
    # Auto-lift expired bans
    await mongo.is_banned(user)
    user = await mongo.get_user(user_id)

    return UserStatusResponse(
        user_id=user_id,
        warning_count=user.get("warning_count", 0),
        ban_status=user.get("ban_status", BanStatus.NONE),
        ban_expires_at=user.get("ban_expires_at"),
        last_warning_at=user.get("last_warning_at"),
    )


# ─────────────────────────────────────────────────────────────
# POST /user/reset  (admin utility)
# ─────────────────────────────────────────────────────────────
@router.post("/user/reset")
async def reset_user(
    body: ResetUserRequest,
    _token=Depends(verify_jwt),
    mongo: MongoService = Depends(get_mongo),
):
    await mongo.reset_user(body.user_id)
    return {"message": f"User {body.user_id} has been reset successfully."}


# ─────────────────────────────────────────────────────────────
def _ban_action(ban_status: BanStatus) -> str:
    mapping = {
        BanStatus.NONE:      "allow",
        BanStatus.DAY:       "ban_day",
        BanStatus.WEEK:      "ban_week",
        BanStatus.PERMANENT: "ban_permanent",
    }
    return mapping.get(ban_status, "allow")
