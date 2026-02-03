import asyncio
import getpass
import os

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError


async def main() -> None:
    api_id = os.getenv("TG_API_ID")
    api_hash = os.getenv("TG_API_HASH")
    phone = os.getenv("TG_PHONE_NUMBER")
    if not api_id or not api_hash or not phone:
        raise SystemExit("Missing TG_API_ID, TG_API_HASH, or TG_PHONE_NUMBER.")

    session_dir = os.getenv("TG_SESSION_DIR", os.path.join(os.getcwd(), "session"))
    session_name = os.getenv("TG_SESSION_NAME", "telegram")
    os.makedirs(session_dir, exist_ok=True)
    session_path = os.path.join(session_dir, session_name)

    client = TelegramClient(session_path, int(api_id), api_hash)
    await client.connect()
    if await client.is_user_authorized():
        print("Already authorized.")
        await client.disconnect()
        return

    await client.send_code_request(phone)
    code = os.getenv("TG_CODE") or input("Enter the login code: ").strip()
    try:
        await client.sign_in(phone=phone, code=code)
    except SessionPasswordNeededError:
        password = os.getenv("TG_PASSWORD") or getpass.getpass("Two-step password: ")
        await client.sign_in(password=password)

    print("Login successful.")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
