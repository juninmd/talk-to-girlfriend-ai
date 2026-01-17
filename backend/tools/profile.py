from telethon import functions
from backend.client import client
from backend.utils import log_and_format_error

async def update_profile(first_name: str = None, last_name: str = None, about: str = None) -> str:
    try:
        await client(functions.account.UpdateProfileRequest(first_name=first_name, last_name=last_name, about=about))
        return "Profile updated."
    except Exception as e:
        return log_and_format_error("update_profile", e)

async def set_profile_photo(file_path: str) -> str:
    try:
        await client(functions.photos.UploadProfilePhotoRequest(file=await client.upload_file(file_path)))
        return "Profile photo updated."
    except Exception as e:
        return log_and_format_error("set_profile_photo", e)
