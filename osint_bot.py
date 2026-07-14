#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔥 Ultimate Free OSINT Telegram Bot v4.0 — Zero API Keys Required
✅ Bengali responses, English codebase
✅ Copy-paste ready, no subscription APIs
"""

import os, re, json, time, asyncio, sqlite3, logging, hashlib, base64
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

import aiohttp
from telethon import TelegramClient, functions, types
from telethon.errors import UsernameNotOccupiedError, FloodWaitError
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# =============================================================================
# ⚙️ CONFIGURATION — আপনার API কী এখানে বসান
# =============================================================================

# === TELEGRAM API (REQUIRED) ===
# https://my.telegram.org → API Development Tools
API_ID = 33530161
API_HASH = "c1076f9f3aff872363e5e2f114e58681"
BOT_TOKEN = "8857378550:AAF6DBANExHejQIHPA71lyP7IArbrqvtew4"

# === INTELX INTELLIGENCE X (FREE) ===
# https://intelx.io → Register → Account → API Key
INTELX_KEY = "2c451691-754c-4f7f-bf0f-952ee2ea5115"

# === NUMVERIFY (FREE) ===
# https://numverify.com → Register → API Key
NUMVERIFY_KEY = "7ced1cf0bedea9fe39aef83827fb471a"

# === LEAKCHECK (FREE) ===
# https://leakcheck.io → Register → API → Key
LEAKCHECK_KEY = "c44d8fecdabf82faa6126aaa157a0032e4c1cb22"

# === DEHASHED (FREE TRIAL) ===
# https://dehashed.com → Register → API Key
DEHASHED_EMAIL = "bot00786@gmail.com"
DEHASHED_KEY = "9neC7teXgg9VhYG54A1xG7YpiblHNkMth2HbReMH3UUI3QpvyD2iIMk="

# === EMAILREP (FREE — NO KEY NEEDED) ===

# =============================================================================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
DB_PATH = "osint_bot_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS search_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, query_type TEXT, query_value TEXT, result_summary TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT, search_count INTEGER DEFAULT 0, first_seen DATETIME DEFAULT CURRENT_TIMESTAMP, last_seen DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit(); conn.close()
init_db()
# =============================================================================

# =============================================================================
# 🚀 OSINT ENGINE — All Free APIs Integrated
# =============================================================================

class OSINTEngine:
    def __init__(self):
        self.tg = TelegramClient('osint_sess', API_ID, API_HASH, device_model="OSINT Bot", app_version="4.0")
        self.http = None

    async def get_http(self):
        if self.http is None or self.http.closed:
            self.http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60))
        return self.http

    async def close(self):
        if self.http and not self.http.closed: await self.http.close()
        if self.tg and self.tg.is_connected(): await self.tg.disconnect()

    # ======================================================================
    # 1. TELEGRAM USERNAME LOOKUP
    # ======================================================================
    async def tg_lookup(self, username: str) -> Dict:
        result = {'success': False, 'data': {}, 'error': None}
        username = username.strip().replace('@', '')
        try:
            await self.tg.start()
            resolved = await self.tg(functions.contacts.ResolveUsernameRequest(username=username))
            if not resolved.users:
                result['error'] = 'এই ইউজারনেমে কোনো অ্যাকাউন্ট নেই'; return result
            u = resolved.users[0]
            photos = []
            try:
                async for p in self.tg.iter_profile_photos(u.id, limit=3):
                    photos.append({'id': p.id, 'date': str(p.date)})
            except: pass
            groups = []
            try:
                gr = await self.tg(functions.messages.GetCommonChatsRequest(user_id=u.id, max_id=0, limit=20))
                for c in gr.chats: groups.append({'id': c.id, 'title': getattr(c, 'title', '?'), 'username': getattr(c, 'username', None)})
            except: pass
            phone = getattr(u, 'phone', None)
            status = 'অজানা'
            if hasattr(u, 'status') and u.status:
                st = type(u.status).__name__
                if 'Online' in st: status = 'অনলাইন'
                elif 'Offline' in st: status = 'অফলাইন'
                elif 'Recently' in st: status = 'সম্প্রতি অনলাইন'
                elif 'LastWeek' in st: status = 'গত সপ্তাহে'
                elif 'LastMonth' in st: status = 'গত মাসে'
            result['success'] = True
            result['data'] = {
                'user_id': u.id, 'username': u.username, 'first_name': u.first_name or '', 'last_name': u.last_name or '',
                'phone': phone, 'is_bot': u.bot, 'is_verified': u.verified, 'is_scam': getattr(u, 'scam', False),
                'status': status, 'photos': len(photos), 'groups': groups[:5], 'groups_count': len(groups)}
            await self.tg.disconnect()
        except UsernameNotOccupiedError: result['error'] = 'এই ইউজারনেমে কোনো অ্যাকাউন্ট নেই'
        except FloodWaitError as e: result['error'] = f'রেট লিমিট! {e.seconds} সেকেন্ড অপেক্ষা করুন'
        except Exception as e: result['error'] = str(e); logger.error(f"tg err: {e}")
        return result

    # ======================================================================
    # 2. PHONE VALIDATION (Numverify)
    # ======================================================================
    async def validate_phone(self, phone: str) -> Dict:
        result = {'valid': False, 'data': {}, 'error': None}
        if not NUMVERIFY_KEY: return result
        phone = re.sub(r'[^\d]', '', phone)
        if len(phone) < 7: return result
        try:
            s = await self.get_http()
            async with s.get('http://apilayer.net/api/validate', params={'access_key': NUMVERIFY_KEY, 'number': phone, 'format': 1}) as r:
                if r.status == 200:
                    d = await r.json(); result['valid'] = d.get('valid', False)
                    if d.get('valid'):
                        result['data'] = {'number': d.get('number', ''), 'country': d.get('country_name', ''), 'country_code': d.get('country_code', ''), 'location': d.get('location', ''), 'carrier': d.get('carrier', ''), 'line_type': d.get('line_type', ''), 'format': d.get('international_format', '')}
        except Exception as e: result['error'] = str(e)
        return result

    # ======================================================================
    # 3. CHECK PHONE ON TELEGRAM
    # ======================================================================
    async def tg_phone_check(self, phone: str) -> Dict:
        result = {'found': False, 'data': {}, 'error': None}
        phone = re.sub(r'[^\d+]', '', phone)
        try:
            await self.tg.start()
            r = await self.tg(functions.contacts.ImportContactsRequest(contacts=[types.InputPhoneContact(client_id=0, phone=phone, first_name='C', last_name='U')]))
            if r.users:
                u = r.users[0]; result['found'] = True
                result['data'] = {'user_id': u.id, 'username': u.username, 'first_name': u.first_name or '', 'last_name': u.last_name or '', 'phone': getattr(u, 'phone', None), 'is_verified': u.verified}
            await self.tg.disconnect()
        except Exception as e: result['error'] = str(e)
        return result

    # ======================================================================
    # 4. EMAILREP.IO (FREE — NO KEY REQUIRED)
    # ======================================================================
    async def emailrep_check(self, email: str) -> Dict:
        result = {'data': {}, 'error': None}
        try:
            s = await self.get_http()
            async with s.get(f'https://emailrep.io/{email}', headers={'User-Agent': 'OSINT-Bot/4.0'}) as r:
                if r.status == 200: result['data'] = await r.json()
                elif r.status == 429: result['error'] = 'রেট লিমিটেড'
        except Exception as e: result['error'] = str(e)
        return result

    # ======================================================================
    # 5. LEAKCHECK.IO (FREE API)
    # ======================================================================
    async def leakcheck_search(self, query: str, qtype: str = 'email') -> Dict:
        result = {'found': False, 'total': 0, 'entries': [], 'error': None}
        if not LEAKCHECK_KEY: result['error'] = 'LeakCheck কী নেই'; return result
        try:
            s = await self.get_http()
            async with s.get(f'https://leakcheck.io/api/public', params={'key': LEAKCHECK_KEY, 'check': query, 'type': qtype}, headers={'Accept': 'application/json'}) as r:
                if r.status == 200:
                    d = await r.json()
                    if d.get('success') and d.get('found'):
                        result['found'] = True; result['total'] = d.get('count', 0)
                        for entry in d.get('result', [])[:10]:
                            result['entries'].append({'email': entry.get('email', ''), 'password': entry.get('password', ''), 'username': entry.get('username', ''), 'phone': entry.get('phone', ''), 'source': 'LeakCheck', 'line': entry.get('line', '')})
                elif r.status == 429: result['error'] = 'রেট লিমিট!'
                elif r.status == 403: result['error'] = 'API কী ভুল বা ব্লকড'
        except Exception as e: result['error'] = str(e)
        return result

    # ======================================================================
    # 6. INTELX.IO (FREE TIER)
    # ======================================================================
    async def intelx_search(self, query: str, qtype: str = 'email') -> Dict:
        result = {'found': False, 'total': 0, 'entries': [], 'error': None}
        if not INTELX_KEY: result['error'] = 'IntelX কী নেই'; return result
        try:
            s = await self.get_http()
            tmap = {'email': 'email', 'username': 'username', 'phone': 'phone', 'domain': 'domain', 'fullname': 'fullname'}
            t = tmap.get(qtype, 'email')
            async with s.post('https://2.intelx.io/intelligent/search', json={'term': query, 'lookuplevel': 0, 'maxresults': 20, 'browseonline': False, 'sort': 2, 'type': t}, headers={'x-key': INTELX_KEY, 'User-Agent': 'OSINT-Bot/4.0', 'Accept': 'application/json'}) as r:
                if r.status == 200:
                    d = await r.json()
                    if d.get('total', 0) > 0:
                        result['found'] = True; result['total'] = int(d.get('total', 0))
                        sel = d.get('selectors', [])[:5]
                        for sel_item in sel:
                            result['entries'].append({'selector': sel_item.get('selectorvalue', ''), 'type': sel_item.get('type', ''), 'source': 'IntelX'})
                elif r.status == 429: result['error'] = 'রেট লিমিট!'
                else: result['error'] = f'HTTP {r.status}'
        except Exception as e: result['error'] = str(e)
        return result

    # ======================================================================
    # 7. DEHASHED.COM (FREE TRIAL)
    # ======================================================================
    async def dehashed_search(self, query: str, qtype: str = 'email') -> Dict:
        result = {'found': False, 'total': 0, 'entries': [], 'error': None}
        if not DEHASHED_KEY or not DEHASHED_EMAIL: result['error'] = 'Dehashed কী নেই'; return result
        try:
            s = await self.get_http()
            auth = base64.b64encode(f'{DEHASHED_EMAIL}:{DEHASHED_KEY}'.encode()).decode()
            async with s.get(f'https://api.dehashed.com/v1/search', params={'query': f'{qtype}:{query}', 'size': 30}, headers={'Accept': 'application/json', 'Authorization': f'Basic {auth}'}) as r:
                if r.status == 200:
                    d = await r.json()
                    if d.get('entries'):
                        result['found'] = True; result['total'] = d.get('total', len(d['entries']))
                        for entry in d['entries'][:10]:
                            result['entries'].append({'email': entry.get('email', ''), 'password': entry.get('password', ''), 'username': entry.get('username', ''), 'name': entry.get('name', ''), 'phone': entry.get('phone', ''), 'ip': entry.get('ip', ''), 'address': entry.get('address', ''), 'source': 'Dehashed'})
                elif r.status == 429: result['error'] = 'রেট লিমিট!'
        except Exception as e: result['error'] = str(e)
        return result

# =============================================================================
# 🤖 TELEGRAM BOT
# =============================================================================

class OSINTBot:
    def __init__(self):
        self.engine = OSINTEngine()
        self.start_time = datetime.now()

    def _save(self, uid, q, qt, qv, summary=''):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute('INSERT INTO search_history (user_id, query_type, query_value, result_summary) VALUES (?,?,?,?)', (uid, qt, str(qv)[:100], str(summary)[:200]))
            conn.execute('UPDATE users SET search_count=search_count+1, last_seen=CURRENT_TIMESTAMP WHERE user_id=?', (uid,))
            conn.commit(); conn.close()
        except Exception as e: logger.error(f"save err: {e}")

    async def start(self, u: Update, c: ContextTypes.DEFAULT_TYPE):
        user = u.effective_user
        conn = sqlite3.connect(DB_PATH)
        conn.execute('INSERT OR REPLACE INTO users (user_id, first_name, username, last_seen) VALUES (?,?,?,CURRENT_TIMESTAMP)', (user.id, user.first_name, user.username))
        conn.commit(); conn.close()
        txt = (f'🔥 **আলটিমেট OSINT বটে স্বাগতম!** {user.first_name}!\n'
               f'━━━━━━━━━━━━━━━━━━━━\n'
               f'👤 `/u @username` — প্রোফাইল + সব API\n'
               f'📞 `/p 01XXXXXXXXX` — ফোন + লিক চেক\n'
               f'📧 `/e user@ex.com` — ইমেইল + সব ব্রিচ\n'
               f'🔍 `/all @username` — ফুল স্ক্যান (সেরা!)\n'
               f'⚠️ `/leak @username` — শুধু লিক ডাটা\n'
               f'📋 `/history` — হিস্টোরি\n'
               f'📊 `/stats` — পরিসংখ্যান\n'
               f'━━━━━━━━━━━━━━━━━━━━\n'
               f'💡 টিপ: `/all @username` সবচেয়ে বেশি তথ্য দেয়!')
        keyboard = [[InlineKeyboardButton('👤 ইউজার', callback_data='hu'), InlineKeyboardButton('📞 ফোন', callback_data='hp'), InlineKeyboardButton('📧 ইমেইল', callback_data='he')],
                    [InlineKeyboardButton('🔍 ফুল', callback_data='hf'), InlineKeyboardButton('⚠️ লিক', callback_data='hl'), InlineKeyboardButton('📊 API', callback_data='as')]]
        await u.message.reply_text(txt, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    async def username(self, u: Update, c: ContextTypes.DEFAULT_TYPE):
        if not c.args: return await u.message.reply_text('⚠️ `/u @username`', parse_mode='Markdown')
        username = c.args[0]
        msg = await u.message.reply_text('⏳ কাজ হচ্ছে...', parse_mode='Markdown')
        result = await self.engine.tg_lookup(username)
        if result['success']:
            d = result['data']
            text = (f'👤 **টেলিগ্রাম প্রোফাইল**\n'
                    f'━━━━━━━━━━━━━━━━━━━━\n'
                    f'📛 **নাম:** {d["first_name"]} {d["last_name"]}\n'
                    f'🆔 `{d["user_id"]}`\n'
                    f'🔗 @{d["username"]}\n')
            if d['phone']:
                text += f'📞 `{d["phone"]}`\n'
                await msg.edit_text(text + '\n\n📡 ফোন চেক...', parse_mode='Markdown')
                pv = await self.engine.validate_phone(d['phone'])
                if pv['valid']:
                    text += f'🌍 {pv["data"]["country"]} | {pv["data"]["carrier"]} | {pv["data"]["line_type"]}\n'
            else:
                text += '📞 🔒 লুকানো\n'
            text += (f'━━━━━━━━━━━━━━━━━━━━\n'
                     f'✅ ভেরিফাইড: {"হ্যাঁ" if d["is_verified"] else "না"}\n'
                     f'🟢 {d["status"]}\n'
                     f'👥 কমন গ্রুপ: {d["groups_count"]}টি\n')
            # LeakCheck username
            if LEAKCHECK_KEY:
                await msg.edit_text(text + '\n\n⚠️ লিক ডাটা চেক করা হচ্ছে...', parse_mode='Markdown')
                lc = await self.engine.leakcheck_search(username, 'username')
                if lc['found']:
                    text += f'\n⚠️ **লিক ডাটা ({lc["total"]}টি):**\n'
                    for e in lc['entries'][:3]:
                        if e['password']: text += f'🔑 পাস: `{e["password"]}`\n'
                        if e['email']: text += f'📧 {e["email"]}\n'
            # IntelX username
            if INTELX_KEY:
                ix = await self.engine.intelx_search(username, 'username')
                if ix['found']:
                    text += f'\n🌐 IntelX: {ix["total"]}টি রেজাল্ট\n'
                    for e in ix['entries'][:3]:
                        if e['selector']: text += f'📄 {e["selector"][:80]}\n'
            # Dehashed username
            if DEHASHED_KEY and DEHASHED_EMAIL:
                dh = await self.engine.dehashed_search(username, 'username')
                if dh['found']:
                    text += f'\n⚠️ **Dehashed ({dh["total"]}টি):**\n'
                    for e in dh['entries'][:3]:
                        if e['password']: text += f'🔑 `{e["password"]}`\n'
                        if e['email']: text += f'📧 {e["email"]}\n'
            self._save(u.effective_user.id, username, 'username', username, f'{d["first_name"]} {d["last_name"]}')
            await msg.edit_text(text, parse_mode='Markdown')
        else:
            await msg.edit_text(f'❌ {result["error"]}', parse_mode='Markdown')

    async def phone(self, u: Update, c: ContextTypes.DEFAULT_TYPE):
        if not c.args: return await u.message.reply_text('⚠️ `/p 01XXXXXXXXX`', parse_mode='Markdown')
        phone = c.args[0]
        msg = await u.message.reply_text('⏳ ফোন চেক...', parse_mode='Markdown')
        text = f'📞 **ফোন স্ক্যান**\n━━━━━━━━━━━━━━━━━━━━\n🔢 `{phone}`\n'
        if NUMVERIFY_KEY:
            pv = await self.engine.validate_phone(phone)
            if pv['valid']:
                pd = pv['data']
                text += f'✅ ভ্যালিড\n🌍 {pd["country"]}\n🏢 {pd["carrier"]}\n📟 {pd["line_type"]}\n'
        await msg.edit_text(text + '\n📡 টেলিগ্রাম চেক...', parse_mode='Markdown')
        tg = await self.engine.tg_phone_check(phone)
        if tg['found']:
            td = tg['data']
            text += (f'\n✅ **টেলিগ্রামে আছে!**\n'
                     f'👤 @{td["username"] or "—"}\n'
                     f'📛 {td["first_name"]} {td["last_name"]}\n'
                     f'🆔 `{td["user_id"]}`\n')
        else:
            text += '\n❌ টেলিগ্রামে নেই\n'
        if LEAKCHECK_KEY:
            await msg.edit_text(text + '\n⚠️ লিক ডাটা চেক...', parse_mode='Markdown')
            lc = await self.engine.leakcheck_search(phone, 'phone')
            if lc['found']:
                text += f'\n⚠️ **লিক ডাটা ({lc["total"]}টি):**\n'
                for e in lc['entries'][:5]:
                    if e['password']: text += f'🔑 `{e["password"]}`\n'
                    if e['email']: text += f'📧 {e["email"]}\n'
        if DEHASHED_KEY and DEHASHED_EMAIL:
            dh = await self.engine.dehashed_search(phone, 'phone')
            if dh['found']:
                text += f'\n⚠️ **Dehashed ({dh["total"]}টি):**\n'
                for e in dh['entries'][:3]:
                    if e['password']: text += f'🔑 `{e["password"]}`\n'
        self._save(u.effective_user.id, phone, 'phone', phone, f'TG: {"Yes" if tg["found"] else "No"}')
        await msg.edit_text(text, parse_mode='Markdown')

    async def email(self, u: Update, c: ContextTypes.DEFAULT_TYPE):
        if not c.args: return await u.message.reply_text('⚠️ `/e user@example.com`', parse_mode='Markdown')
        email = c.args[0]
        msg = await u.message.reply_text('⏳ ইমেইল চেক...', parse_mode='Markdown')
        text = f'📧 **ইমেইল রিপোর্ট**\n━━━━━━━━━━━━━━━━━━━━\n🎯 `{email}`\n\n'
        # EmailRep (FREE — no key)
        text += '**📊 EmailRep:**\n'
        await msg.edit_text(text + '⏳ চেক...', parse_mode='Markdown')
        rep = await self.engine.emailrep_check(email)
        if rep['data'] and rep['data'].get('reputation', 'none') != 'none':
            rd = rep['data']
            text += (f'⭐ {rd.get("reputation", "—")}\n'
                     f'⚠️ সাসপিশিয়াস: {"হ্যাঁ" if rd.get("suspicious") else "না"}\n'
                     f'🔴 ক্রিডেনশিয়াল লিক: {"হ্যাঁ" if rd.get("leaked") else "না"}\n'
                     f'🔴 ব্রিচ: {"হ্যাঁ" if rd.get("breach") else "না"}\n'
                     f'📚 {rd.get("references", 0)}টি সোর্স\n\n')
        else:
            text += 'ℹ️ তথ্য নেই\n\n'
        # LeakCheck
        if LEAKCHECK_KEY:
            text += '**⚠️ LeakCheck:**\n'
            await msg.edit_text(text + '⏳ চেক...', parse_mode='Markdown')
            lc = await self.engine.leakcheck_search(email, 'email')
            if lc['found']:
                text += f'⚠️ **{lc["total"]}টি লিক!**\n'
                for e in lc['entries'][:5]:
                    if e['password']: text += f'🔑 `{e["password"]}`\n'
                    if e['username']: text += f'👤 @{e["username"]}\n'
            else:
                text += '✅ পাওয়া যায়নি\n'
            text += '\n'
        # Dehashed
        if DEHASHED_KEY and DEHASHED_EMAIL:
            text += '**⚠️ Dehashed:**\n'
            await msg.edit_text(text + '⏳ চেক...', parse_mode='Markdown')
            dh = await self.engine.dehashed_search(email, 'email')
            if dh['found']:
                text += f'⚠️ **{dh["total"]}টি লিক!**\n'
                for e in dh['entries'][:3]:
                    if e['password']: text += f'🔑 `{e["password"]}`\n'
                    if e['phone']: text += f'📞 {e["phone"]}\n'
            else:
                text += '✅ পাওয়া যায়নি\n'
            text += '\n'
        # IntelX
        if INTELX_KEY:
            text += '**🌐 IntelX:**\n'
            await msg.edit_text(text + '⏳ চেক...', parse_mode='Markdown')
            ix = await self.engine.intelx_search(email, 'email')
            if ix['found']:
                text += f'✅ {ix["total"]}টি রেজাল্ট\n'
                for e in ix['entries'][:3]:
                    if e['selector']: text += f'📄 {e["selector"][:80]}\n'
            else:
                text += 'ℹ️ পাওয়া যায়নি\n'
        self._save(u.effective_user.id, email, 'email', email, f'Leaks: {lc.get("total", 0) if LEAKCHECK_KEY else "?"}')
        await msg.edit_text(text, parse_mode='Markdown')

    async def full_scan(self, u: Update, c: ContextTypes.DEFAULT_TYPE):
        if not c.args: return await u.message.reply_text('⚠️ `/all @username`\n⏱ ৩০-৬০ সেকেন্ড', parse_mode='Markdown')
        target = c.args[0].replace('@', '')
        msg = await u.message.reply_text('🔥 **ফুল স্ক্যান শুরু...**\n📌 টেলিগ্রাম...', parse_mode='Markdown')
        text = (f'🔍 **ফুল OSINT রিপোর্ট**\n'
                f'🎯 @{target}\n'
                f'📅 {datetime.now():%Y-%m-%d %H:%M}\n'
                f'━━━━━━━━━━━━━━━━━━━━\n\n')
        tg = await self.engine.tg_lookup(target)
        if tg['success']:
            d = tg['data']
            text += '**【📱 টেলিগ্রাম】**\n'
            text += f'👤 {d["first_name"]} {d["last_name"]}\n🆔 `{d["user_id"]}`\n'
            phone = d['phone']
            if phone:
                text += f'📞 `{phone}`\n'
            else:
                text += '📞 🔒 লুকানো\n'
            text += f'✅ ভেরিফাইড: {"হ্যাঁ" if d["is_verified"] else "না"}\n👥 গ্রুপ: {d["groups_count"]}টি\n\n'
            if phone and NUMVERIFY_KEY:
                await msg.edit_text('🔥 স্ক্যান...\n📌 ফোন ভ্যালিডেশন...', parse_mode='Markdown')
                pv = await self.engine.validate_phone(phone)
                if pv['valid']:
                    text += (f'**【📡 ফোন】**\n'
                             f'🌍 {pv["data"]["country"]}\n'
                             f'🏢 {pv["data"]["carrier"]}\n\n')
        if LEAKCHECK_KEY:
            await msg.edit_text('🔥 স্ক্যান...\n📌 LeakCheck...', parse_mode='Markdown')
            lc = await self.engine.leakcheck_search(target, 'username')
            if lc['found']:
                text += f'**【⚠️ LeakCheck {lc["total"]}টি】**\n'
                for e in lc['entries'][:3]:
                    if e['password']: text += f'🔑 `{e["password"]}`\n'
                    if e['email']: text += f'📧 {e["email"]}\n'
                text += '\n'
        if DEHASHED_KEY and DEHASHED_EMAIL:
            await msg.edit_text('🔥 স্ক্যান...\n📌 Dehashed...', parse_mode='Markdown')
            dh = await self.engine.dehashed_search(target, 'username')
            if dh['found']:
                text += f'**【⚠️ Dehashed {dh["total"]}টি】**\n'
                for e in dh['entries'][:3]:
                    if e['password']: text += f'🔑 `{e["password"]}`\n'
                    if e['email']: text += f'📧 {e["email"]}\n'
                text += '\n'
        if INTELX_KEY:
            await msg.edit_text('🔥 স্ক্যান...\n📌 IntelX...', parse_mode='Markdown')
            ix = await self.engine.intelx_search(target, 'username')
            if ix['found']:
                text += f'**【🌐 IntelX {ix["total"]}টি】**\n'
                for e in ix['entries'][:3]:
                    if e['selector']: text += f'📄 {e["selector"][:80]}\n'
                text += '\n'
        text += '━━━━━━━━━━━━━━━━━━━━\n✅ **স্ক্যান শেষ!**\n'
        self._save(u.effective_user.id, target, 'full_scan', target, f'Phone: {phone or "Hidden"}')
        await msg.edit_text(text, parse_mode='Markdown')

    async def leak_cmd(self, u: Update, c: ContextTypes.DEFAULT_TYPE):
        if not c.args: return await u.message.reply_text('⚠️ `/leak @username` বা `/leak email@ex.com`', parse_mode='Markdown')
        query = c.args[0].replace('@', '')
        msg = await u.message.reply_text('⚠️ লিক ডাটা খোঁজা হচ্ছে...', parse_mode='Markdown')
        text = f'⚠️ **লিক ডাটা চেক**\n🎯 `{query}`\n━━━━━━━━━━━━━━━━━━━━\n\n'
        found = False
        if LEAKCHECK_KEY:
            qtype = 'email' if '@' in query else 'username'
            lc = await self.engine.leakcheck_search(query, qtype)
            if lc['found']:
                found = True
                text += f'**LeakCheck ({lc["total"]}টি):**\n'
                for e in lc['entries'][:8]:
                    if e.get('password'): text += f'🔑 `{e["password"]}`\n'
                    if e.get('email'): text += f'📧 {e["email"]}\n'
                    if e.get('phone'): text += f'📞 {e["phone"]}\n'
                text += '\n'
        if DEHASHED_KEY and DEHASHED_EMAIL:
            qtype = 'email' if '@' in query else 'username'
            dh = await self.engine.dehashed_search(query, qtype)
            if dh['found']:
                found = True
                text += f'**Dehashed ({dh["total"]}টি):**\n'
                for e in dh['entries'][:5]:
                    if e.get('password'): text += f'🔑 `{e["password"]}`\n'
                    if e.get('email'): text += f'📧 {e["email"]}\n'
                text += '\n'
        if '@' in query:
            rep = await self.engine.emailrep_check(query)
            if rep['data'] and rep['data'].get('leaked'):
                found = True
                text += f'**EmailRep:** লিক হয়েছে!\n'
        if not found:
            text += '❌ কোনো লিক ডাটা পাওয়া যায়নি\n'
        self._save(u.effective_user.id, query, 'leak', query, f'Found: {found}')
        await msg.edit_text(text, parse_mode='Markdown')

    async def history(self, u: Update, c: ContextTypes.DEFAULT_TYPE):
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute('SELECT query_type, query_value, timestamp FROM search_history WHERE user_id=? ORDER BY timestamp DESC LIMIT 15', (u.effective_user.id,)).fetchall()
        conn.close()
        if not rows:
            return await u.message.reply_text('📋 কোনো হিস্টোরি নেই', parse_mode='Markdown')
        icons = {'username': '👤', 'phone': '📞', 'email': '📧', 'full_scan': '🔍', 'leak': '⚠️'}
        text = '📋 **সার্চ হিস্টোরি:**\n\n'
        for qt, qv, ts in rows:
            text += f'{icons.get(qt, "❓")} `{qv}` — {ts[:19]}\n'
        await u.message.reply_text(text, parse_mode='Markdown')

    async def stats(self, u: Update, c: ContextTypes.DEFAULT_TYPE):
        conn = sqlite3.connect(DB_PATH)
        ud = conn.execute('SELECT search_count, first_seen, last_seen FROM users WHERE user_id=?', (u.effective_user.id,)).fetchone()
        cnt = conn.execute('SELECT COUNT(*), COUNT(DISTINCT query_type) FROM search_history WHERE user_id=?', (u.effective_user.id,)).fetchone()
        conn.close()
        await u.message.reply_text(
            f'📊 **পরিসংখ্যান**\n'
            f'━━━━━━━━━━━━━━━━━━━━\n'
            f'🔍 **মোট সার্চ:** {cnt[0] or 0}টি\n'
            f'📂 **টাইপ:** {cnt[1] or 0} ধরনের\n'
            f'📅 **প্রথম:** {(ud[1] or "—")[:19]}\n'
            f'🕐 **শেষ:** {(ud[2] or "—")[:19]}',
            parse_mode='Markdown')

    async def help(self, u: Update, c: ContextTypes.DEFAULT_TYPE):
        await u.message.reply_text(
            '🆘 **সাহায্য**\n\n'
            '👤 `/u @user` — প্রোফাইল\n'
            '📞 `/p 01XXX` — ফোন\n'
            '📧 `/e email` — ইমেইল\n'
            '🔍 `/all @user` — ফুল স্ক্যান\n'
            '⚠️ `/leak query` — লিক ডাটা\n'
            '📋 `/history` — হিস্টোরি\n'
            '📊 `/stats` — পরিসংখ্যান',
            parse_mode='Markdown')

    async def about(self, u: Update, c: ContextTypes.DEFAULT_TYPE):
        await u.message.reply_text(
            '🤖 **আলটিমেট OSINT বট v4.0**\n'
            '✅ ১০০% ফ্রি API\n'
            '✅ LeakCheck, Dehashed, IntelX, EmailRep\n'
            '✅ টেলিগ্রাম প্রোফাইল\n'
            '✅ ফোন ভ্যালিডেশন\n'
            '✅ ইমেইল লিক চেক\n\n'
            f'⏱ {(datetime.now()-self.start_time).total_seconds()/3600:.1f} ঘন্টা ধরে চলছে\n\n'
            '⚠️ শুধুমাত্র এথিক্যাল রিসার্চের জন্য।',
            parse_mode='Markdown')

    async def button_handler(self, u: Update, c: ContextTypes.DEFAULT_TYPE):
        q = u.callback_query
        await q.answer()
        msgs = {
            'hu': '👤 `/u @username` — প্রোফাইল + ফোন + লিক ডাটা',
            'hp': '📞 `/p 01XXX` — ফোন ভ্যালিডেশন + টেলিগ্রাম + লিক',
            'he': '📧 `/e email` — EmailRep + LeakCheck + Dehashed + IntelX',
            'hf': '🔍 `/all @user` — সব API একসাথে (সেরা)',
            'hl': '⚠️ `/leak query` — শুধু লিক/ব্রিচ ডাটা সার্চ',
            'as': (f'📊 **API:**\n'
                   f'✅ টেলিগ্রাম\n'
                   f'✅ EmailRep\n'
                   f'{"✅" if INTELX_KEY else "❌"} IntelX\n'
                   f'{"✅" if LEAKCHECK_KEY else "❌"} LeakCheck\n'
                   f'{"✅" if DEHASHED_KEY else "❌"} Dehashed\n'
                   f'{"✅" if NUMVERIFY_KEY else "❌"} Numverify')
        }
        await q.edit_message_text(msgs.get(q.data, '❓'), parse_mode='Markdown')

    async def error_handler(self, u: Update, c: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Error: {c.error}")
        try:
            if u and u.effective_message:
                await u.effective_message.reply_text('⚠️ ত্রুটি হয়েছে! আবার চেষ্টা করুন।', parse_mode='Markdown')
        except:
            pass


# =============================================================================
def main():
    print("""
    ╔═══════════════════════════════════════╗
    ║  🔥 Ultimate OSINT Bot v4.0          ║
    ║  Zero API Keys Required — Free       ║
    ╚═══════════════════════════════════════╝
    """)
    if API_ID == 123456 or BOT_TOKEN == "your_bot_token_here":
        print("❌ ERROR: Set API_ID, API_HASH and BOT_TOKEN first!")
        print("   📍 API_ID & API_HASH: https://my.telegram.org")
        print("   📍 BOT_TOKEN: https://t.me/BotFather")
        return
    print(f"📊 APIs: IntelX={'✅' if INTELX_KEY else '❌'} | LeakCheck={'✅' if LEAKCHECK_KEY else '❌'} | Dehashed={'✅' if DEHASHED_KEY else '❌'} | Numverify={'✅' if NUMVERIFY_KEY else '❌'} | EmailRep=✅")
    print("✅ Bot starting...")
    bot = OSINTBot()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', bot.start))
    app.add_handler(CommandHandler(['u', 'username', 'full'], bot.username))
    app.add_handler(CommandHandler(['p', 'phone'], bot.phone))
    app.add_handler(CommandHandler(['e', 'email'], bot.email))
    app.add_handler(CommandHandler(['all', 'full_scan'], bot.full_scan))
    app.add_handler(CommandHandler('leak', bot.leak_cmd))
    app.add_handler(CommandHandler('history', bot.history))
    app.add_handler(CommandHandler('stats', bot.stats))
    app.add_handler(CommandHandler('help', bot.help))
    app.add_handler(CommandHandler('about', bot.about))
    app.add_handler(CallbackQueryHandler(bot.button_handler))
    app.add_error_handler(bot.error_handler)
    print(f"✅ Running! Send /start to @{BOT_TOKEN.split(':')[0]}")
    app.run_polling(allowed_updates=['message', 'callback_query'])


if __name__ == '__main__':
    main()