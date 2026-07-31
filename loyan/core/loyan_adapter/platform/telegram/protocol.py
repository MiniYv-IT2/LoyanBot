import logging
from typing import Optional

from telegram import Update

from loyan.core.loyan_adapter.event import LoyanEvent
from loyan.core.loyan_adapter.identity import IdentityTag
from loyan.core.loyan_adapter.message import (
    LoyanText, LoyanImage, LoyanVoice, LoyanFile,
    LoyanVideo, LoyanAt, LoyanReply,
)

_logger = logging.getLogger("Adapter.Telegram.protocol")


def _extract_entities(msg):
    mentioned = set()
    if not msg.entities:
        return mentioned
    for e in msg.entities:
        if e.type in ("mention", "text_mention") and e.user:
            mentioned.add(str(e.user.id))
    return mentioned


def _parse_message(msg):
    segments = []
    text_content = msg.text or msg.caption or ""
    if text_content:
        segments.append(LoyanText(text=text_content))
    if msg.photo:
        segments.append(LoyanImage(file_path=msg.photo[-1].file_id))
    if msg.video:
        segments.append(LoyanVideo(file_path=msg.video.file_id))
    if msg.audio:
        segments.append(LoyanVoice(file_path=msg.audio.file_id))
    if msg.voice:
        segments.append(LoyanVoice(file_path=msg.voice.file_id))
    if msg.document:
        segments.append(LoyanFile(file_path=msg.document.file_id))
    if msg.sticker:
        segments.append(LoyanImage(file_path=msg.sticker.file_id))
    if msg.animation:
        segments.append(LoyanVideo(file_path=msg.animation.file_id))
    if msg.video_note:
        segments.append(LoyanVideo(file_path=msg.video_note.file_id))
    if msg.location:
        lat = msg.location.latitude
        lon = msg.location.longitude
        segments.append(LoyanText(text=f"location:{lat},{lon}"))
    if msg.venue:
        v = msg.venue
        segments.append(LoyanText(text=f"venue:{v.title}|{v.address}"))
    if msg.contact:
        c = msg.contact
        segments.append(LoyanText(text=f"contact:{c.phone_number}|{c.first_name}"))
    if msg.poll:
        segments.append(LoyanText(text=f"poll:{msg.poll.question}"))
    if msg.dice:
        segments.append(LoyanText(text=f"dice:{msg.dice.value}"))
    if msg.game:
        segments.append(LoyanText(text=f"game:{msg.game.title}"))
    if msg.invoice:
        segments.append(LoyanText(text=f"invoice:{msg.invoice.title}/{msg.invoice.total_amount}"))
    if msg.passport_data:
        segments.append(LoyanText(text="[passport_data]"))
    mentioned = _extract_entities(msg)
    for uid in mentioned:
        segments.append(LoyanAt(target_id=uid))
    if msg.reply_to_message and msg.reply_to_message.message_id:
        reply_id = str(msg.reply_to_message.message_id)
        segments.append(LoyanReply(message_id=reply_id))
    if msg.is_topic_message:
        pass
    if msg.forward_origin:
        pass
    return text_content, segments


def _build_event(sender_id, target_id, chat_type, segments, raw_text, message_id, nickname, raw_data, tag):
    if not sender_id or sender_id == "0":
        raise ValueError(f"invalid sender_id: {sender_id}")
    if not target_id:
        raise ValueError("target_id is empty")
    return LoyanEvent(
        sender_id=sender_id, target_id=target_id, chat_type=chat_type,
        segments=segments, raw_text=raw_text, message_id=message_id,
        nickname=nickname, is_at_bot=False, raw_data=raw_data, source=tag,
    )


def update_to_loyan(update: Update, tag: IdentityTag) -> Optional[LoyanEvent]:
    if update is None:
        return None

    msg = update.effective_message
    if msg:
        chat_type = "private" if msg.chat.type == "private" else "group"
        text, segs = _parse_message(msg)
        sid = str(msg.from_user.id) if msg.from_user else "0"
        tid = str(msg.chat.id)
        nick = msg.from_user.full_name if msg.from_user else ""
        mid = str(msg.message_id)
        return _build_event(sid, tid, chat_type, segs, text, mid, nick, update.to_dict(), tag)

    em = update.edited_message
    if em:
        chat_type = "private" if em.chat.type == "private" else "group"
        text, segs = _parse_message(em)
        sid = str(em.from_user.id) if em.from_user else "0"
        tid = str(em.chat.id)
        nick = em.from_user.full_name if em.from_user else ""
        mid = str(em.message_id)
        return _build_event(sid, tid, chat_type, segs, text, mid, nick, update.to_dict(), tag)

    cbq = update.callback_query
    if cbq and cbq.message:
        chat_type = "private" if cbq.message.chat.type == "private" else "group"
        sid = str(cbq.from_user.id)
        tid = str(cbq.message.chat.id)
        nick = cbq.from_user.full_name or ""
        mid = str(cbq.message.message_id)
        data = cbq.data or cbq.id
        segs = [LoyanText(text=data)]
        return _build_event(sid, tid, chat_type, segs, data, mid, nick, update.to_dict(), tag)

    iq = update.inline_query
    if iq:
        sid = str(iq.from_user.id)
        tid = str(iq.from_user.id)
        nick = iq.from_user.full_name or ""
        query = iq.query or ""
        segs = [LoyanText(text=query)]
        return _build_event(sid, tid, "private", segs, query, "", nick, update.to_dict(), tag)

    cq = update.chosen_inline_result
    if cq:
        sid = str(cq.from_user.id)
        tid = str(cq.from_user.id)
        nick = cq.from_user.full_name or ""
        text = cq.query or cq.result_id or ""
        segs = [LoyanText(text=text)]
        return _build_event(sid, tid, "private", segs, text, "", nick, update.to_dict(), tag)

    cm = update.chat_member or update.my_chat_member
    if cm:
        chat_type = "private" if cm.chat.type == "private" else "group"
        user = cm.from_user
        sid = str(user.id) if user else "0"
        tid = str(cm.chat.id)
        nick = user.full_name if user else ""
        return _build_event(sid, tid, chat_type, [], "", "", nick, update.to_dict(), tag)

    cjr = update.chat_join_request
    if cjr:
        sid = str(cjr.from_user.id) if cjr.from_user else "0"
        tid = str(cjr.chat.id)
        nick = cjr.from_user.full_name if cjr.from_user else ""
        segs = [LoyanText(text="join_request")]
        return _build_event(sid, tid, "group", segs, "join_request", "", nick, update.to_dict(), tag)

    cp = update.channel_post or update.edited_channel_post
    if cp:
        chat_type = "group"
        text, segs = _parse_message(cp)
        sid = str(cp.sender_chat.id) if cp.sender_chat else "0"
        tid = str(cp.chat.id)
        nick = cp.sender_chat.title if cp.sender_chat else ""
        mid = str(cp.message_id)
        return _build_event(sid, tid, chat_type, segs, text, mid, nick, update.to_dict(), tag)

    pa = update.poll_answer
    if pa:
        sid = str(pa.user.id) if pa.user else "0"
        tid = sid
        nick = pa.user.full_name if pa.user else ""
        poll_str = pa.poll_id
        if pa.option_ids:
            poll_str = f"{pa.poll_id}:{','.join(str(o) for o in pa.option_ids)}"
        segs = [LoyanText(text=poll_str)]
        return _build_event(sid, tid, "private", segs, poll_str, "", nick, update.to_dict(), tag)

    pq = update.pre_checkout_query
    if pq:
        sid = str(pq.from_user.id) if pq.from_user else "0"
        tid = sid
        nick = pq.from_user.full_name if pq.from_user else ""
        segs = [LoyanText(text=f"checkout:{pq.invoice_payload}")]
        return _build_event(sid, tid, "private", segs, pq.invoice_payload or "", "", nick, update.to_dict(), tag)

    return None
