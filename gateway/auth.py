import json
import os
import random
import string
import time
from gateway.models import MsgContext
from gateway.models import MsgContext, ReplyPayload


# Define a global variable to store pending OTP pairs
pending_pairs: dict = {}


BASE_DIR = os.path.dirname(__file__)  # thư mục chứa auth.py
ALLOWLIST_PATH = os.path.join(
    BASE_DIR, "..", "..", "workspace", "auth", "allowlist.json")


def is_allowed(sender_id: str, channel: str) -> bool:
    if not os.path.exists(ALLOWLIST_PATH):
        return False
    with open(ALLOWLIST_PATH, 'r') as f:
        data = json.load(f)
    lst_allowed_channel = data.get(channel, [])
    return sender_id in lst_allowed_channel


OTP_CHARS = string.ascii_uppercase + string.digits
OTP_CHARS = OTP_CHARS.replace("O", "").replace(
    "0", "").replace("1", "").replace("I", "")


def generate_otp(sender_id: str, channel: str) -> str:
    # create otp
    otp = ''.join(random.choices(OTP_CHARS, k=8))
    key = f"{channel}:{sender_id}"

    pending_pairs[key] = {
        "otp": otp,
        "expires_at": time.time() + 3600
    }
    return otp


def approve(sender_id: str, channel: str, otp: str) -> bool:
    key = f"{channel}:{sender_id}"
    if key not in pending_pairs:
        return False
    entry = pending_pairs[key]
    if entry["expires_at"] < time.time():
        del pending_pairs[key]
        return False
    if entry["otp"] != otp:
        return False

    if os.path.exists(ALLOWLIST_PATH):
        with open(ALLOWLIST_PATH, 'r') as f:
            data = json.load(f)
    else:
        data = {}
    lst_allowed_channel = data.get(channel, [])
    if sender_id not in lst_allowed_channel:
        lst_allowed_channel.append(sender_id)
        data[channel] = lst_allowed_channel
        os.makedirs(os.path.dirname(ALLOWLIST_PATH), exist_ok=True)
        with open(ALLOWLIST_PATH, 'w') as f:
            json.dump(data, f, indent=4)
    del pending_pairs[key]
    return True


def check(msg: MsgContext) -> tuple[bool, str]:

    channel = msg.channel
    sender_id = msg.sender_id
    key = f"{channel}:{sender_id}"

    # HTTP requests bypass pairing
    if channel == "http":
        return True, ""

    # allowlist
    if is_allowed(sender_id, channel):
        return True, ""

    # check existing OTP
    if key in pending_pairs and pending_pairs[key]["expires_at"] > time.time():
        otp = pending_pairs[key]["otp"]
    else:
        otp = generate_otp(sender_id, channel)

    # send OTP to user
    if msg.reply_fn:
        msg.reply_fn(ReplyPayload(
            text=f"Your OTP is {otp}. Please use it to pair your account."))

    return False, "pairing_required"
