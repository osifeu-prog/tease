# app/bot/investor_wallet_bot.py
import logging

# --- SLH SAFETY: ignore non-private updates at webhook (groups/channels) ---
def _slh_is_private_update(payload: dict) -> bool:
    try:
        msg = payload.get("message") or payload.get("edited_message") or payload.get("channel_post") or payload.get("edited_channel_post")
        if isinstance(msg, dict):
            chat = msg.get("chat") or {}
            return chat.get("type") == "private"

        cb = payload.get("callback_query")
        if isinstance(cb, dict):
            m2 = cb.get("message") or {}
            chat = m2.get("chat") or {}
            return chat.get("type") == "private"

        # If we cannot detect chat type, do not block.
        return True
    except Exception:
        return True
from decimal import Decimal

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from sqlalchemy import or_

from app.core.config import settings
from app.database import SessionLocal
from app import models, crud, blockchain
from app.monitoring import run_selftest
from app import i18n

logger = logging.getLogger(__name__)

STATE_AWAITING_BNB_ADDRESS = "AWAITING_BNB_ADDRESS"
STATE_AWAITING_TRANSFER_TARGET = "AWAITING_TRANSFER_TARGET"
STATE_AWAITING_TRANSFER_AMOUNT = "AWAITING_TRANSFER_AMOUNT"


class InvestorWalletBot:
    def __init__(self):
        self.application: Application | None = None
        self.bot: Bot | None = None

    # ===== DB helper =====

    def _db(self):
        return SessionLocal()

    # ===== Language helper (in-memory preferred language) =====

    def _get_lang(
        self,
        tg_user,
        context: ContextTypes.DEFAULT_TYPE | None = None,
    ) -> str:
        """
        ×§×•×‘×¢ ×گ×ھ ×”×©×¤×” ×¢×‘×•×¨ ×‍×©×ھ×‍×©:
        1. ×گ×‌ ×™×© override ×‘-context.user_data["lang"] â€“ ×‍×©×ھ×‍×©×™×‌ ×‘×•.
        2. ×گ×—×¨×ھ ×œ×¤×™ language_code ×‍×ک×œ×’×¨×‌.
        3. ×گ×—×¨×ھ DEFAULT_LANGUAGE.
        """
        override = None
        if context is not None:
            override = context.user_data.get("lang")

        if override:
            return i18n.normalize_lang(override)

        raw = getattr(tg_user, "language_code", None) or settings.DEFAULT_LANGUAGE
        return i18n.normalize_lang(raw)

    # ===== User helper (with is_new flag) =====

    def _get_or_create_user_with_flag(
        self, tg_user
    ) -> tuple[models.User, bool]:
        """
        ×‍×—×–×™×¨ (user, is_new):
        - ×گ×‌ ×”×‍×©×ھ×‍×© ×œ×گ ×§×™×™×‌ ×‘×ک×‘×œ×” -> ×™×•×¦×¨ ×گ×•×ھ×•, is_new = True
        - ×گ×‌ ×§×™×™×‌ -> ×‍×¢×“×›×ں username ×گ×‌ ×¦×¨×™×ڑ, is_new = False
        """
        db = self._db()
        try:
            user = (
                db.query(models.User)
                .filter(models.User.telegram_id == tg_user.id)
                .first()
            )
            is_new = False

            if not user:
                user = models.User(
                    telegram_id=tg_user.id,
                    username=tg_user.username,
                    balance_slh=Decimal("0"),
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                is_new = True
            else:
                # ×¢×“×›×•×ں username ×گ×‌ ×”×©×ھ× ×” ×‘×ک×œ×’×¨×‌
                if tg_user.username and user.username != tg_user.username:
                    user.username = tg_user.username
                    db.add(user)
                    db.commit()
                    db.refresh(user)

            return user, is_new
        finally:
            db.close()

    def _ensure_user(self, update: Update) -> models.User:
        """
        ×œ×©×™×‍×•×© ×‘×©×گ×¨ ×”×¤×§×•×“×•×ھ â€“ ×‍×—×–×™×¨ ×ھ×‍×™×“ user, ×‘×œ×™ ×œ×”×ھ×¢×،×§ ×‘-is_new.
        """
        tg_user = update.effective_user
        user, _ = self._get_or_create_user_with_flag(tg_user)
        return user

    async def _log_new_investor(
        self, tg_user, user: models.User
    ) -> None:
        """
        ×œ×•×’ ×¢×œ ×‍×©×ھ×‍×© ×—×“×© ×œ×§×‘×•×¦×”/×¢×¨×•×¥ ×©×‍×•×’×“×¨ ×‘-LOG_NEW_USERS_CHAT_ID.
        ×¨×¥ ×¨×§ ×›×گ×©×¨ ×”×‍×©×ھ×‍×© × ×•×¦×¨ ×¢×›×©×™×• (is_new=True).
        """
        chat_id = settings.LOG_NEW_USERS_CHAT_ID
        if not chat_id:
            return

        if not self.application or not self.application.bot:
            logger.warning(
                "Cannot log new investor â€“ application.bot is not ready"
            )
            return

        target_chat = chat_id
        # × × ×،×” ×œ×”×‍×™×¨ ×œ-int ×گ×‌ ×–×” ×‍×،×¤×¨ (×›×•×œ×œ ×¢×¨×•×¦×™ -100...)
        try:
            target_chat = int(chat_id)
        except ValueError:
            # ×گ×‌ ×–×” ×œ×گ ×‍×،×¤×¨, × ×©×گ×™×¨ ×‍×—×¨×•×–×ھ
            pass

        lines: list[str] = []
        lines.append("ًں†• New investor in SLH Global Investments")
        lines.append(f"Telegram ID: {tg_user.id}")
        if tg_user.username:
            lines.append(f"Username: @{tg_user.username}")
        else:
            lines.append("Username: N/A")
        lines.append(f"BNB address: {user.bnb_address or 'Not linked yet'}")
        lines.append(f"SLH balance: {(user.balance_slh or 0):.4f} SLH")

        try:
            await self.application.bot.send_message(
                chat_id=target_chat,
                text="\n".join(lines),
            )
        except Exception as e:
            logger.warning("Failed to send new investor log: %s", e)

    # ===== Initialization =====

    async def initialize(self):
        if not settings.BOT_TOKEN:
            logger.warning(
                "BOT_TOKEN is not set, skipping Telegram bot initialization"
            )
            return

        self.application = Application.builder().token(settings.BOT_TOKEN).build()
        self.bot = self.application.bot

        # Commands
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("menu", self.cmd_menu))
        self.application.add_handler(CommandHandler("wallet", self.cmd_wallet))
        self.application.add_handler(
            CommandHandler("link_wallet", self.cmd_link_wallet)
        )
        self.application.add_handler(
            CommandHandler("balance", self.cmd_balance)
        )
        self.application.add_handler(
            CommandHandler("onchain_balance", self.cmd_onchain_balance)
        )
        self.application.add_handler(
            CommandHandler("history", self.cmd_history)
        )
        self.application.add_handler(
            CommandHandler("transfer", self.cmd_transfer)
        )
        self.application.add_handler(
            CommandHandler("send_slh", self.cmd_send_slh)
        )
        self.application.add_handler(
            CommandHandler("whoami", self.cmd_whoami)
        )
        self.application.add_handler(
            CommandHandler("summary", self.cmd_summary)
        )
        self.application.add_handler(CommandHandler("docs", self.cmd_docs))

        # Future economic-engine modules (placeholders with i18n 'coming soon')
        self.application.add_handler(
            CommandHandler("staking", self.cmd_staking)
        )
        self.application.add_handler(
            CommandHandler("signals", self.cmd_signals)
        )
        self.application.add_handler(
            CommandHandler("academy", self.cmd_academy)
        )
        self.application.add_handler(
            CommandHandler("referrals", self.cmd_referrals)
        )
        self.application.add_handler(
            CommandHandler("reports", self.cmd_reports)
        )
        self.application.add_handler(
            CommandHandler("portfolio_pro", self.cmd_portfolio_pro)
        )

        # NEW: language selector
        self.application.add_handler(
            CommandHandler("language", self.cmd_language)
        )

        # NEW: quick health check command (×œ×›×•×œ×‌)
        self.application.add_handler(CommandHandler("ping", self.cmd_ping))

        # Admin-only commands
        self.application.add_handler(
            CommandHandler("admin_credit", self.cmd_admin_credit)
        )
        self.application.add_handler(
            CommandHandler("admin_menu", self.cmd_admin_menu)
        )
        self.application.add_handler(
            CommandHandler("admin_list_users", self.cmd_admin_list_users)
        )
        self.application.add_handler(
            CommandHandler("admin_ledger", self.cmd_admin_ledger)
        )

        # NEW: admin self-test command
        self.application.add_handler(
            CommandHandler("admin_selftest", self.cmd_admin_selftest)
        )

        # Callback for inline buttons â€“ ×‍×©×§×™×¢×™×‌
        self.application.add_handler(
            CallbackQueryHandler(self.cb_wallet_menu, pattern=r"^WALLET_")
        )
        self.application.add_handler(
            CallbackQueryHandler(self.cb_main_menu, pattern=r"^MENU_")
        )

        # Callback ×œ×©×¤×”
        self.application.add_handler(
            CallbackQueryHandler(self.cb_language, pattern=r"^LANG_")
        )

        # Callback ×œ×گ×“×‍×™×ں
        self.application.add_handler(
            CallbackQueryHandler(self.cb_admin_menu, pattern=r"^ADMIN_")
        )

        # Generic text handler (for address / amounts / usernames)
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_text,
            )
        )

        # ×—×•×‘×” ×‘-ptb v21 ×œ×¤× ×™ process_update
        await self.application.initialize()

        # Webhook mode
        if settings.WEBHOOK_URL:
            webhook_url = (
                f"{settings.WEBHOOK_URL.rstrip('/')}/webhook/telegram"
            )
            await self.bot.set_webhook(webhook_url)
            logger.info(f"Webhook set to: {webhook_url}")
        else:
            logger.info(
                "No WEBHOOK_URL set - you can run in polling mode locally"
            )

        logger.info("InvestorWalletBot initialized")

    # ===== Helpers =====

    def _slh_price_nis(self) -> Decimal:
        """×‍×—×™×¨ SLH ×‘× ×™×، (×‘×¨×™×¨×ھ ×‍×—×“×œ: 444) ×›-Decimal."""
        try:
            return Decimal(str(settings.SLH_PRICE_NIS))
        except Exception:
            return Decimal("444")

    def _investor_tier(self, balance: Decimal) -> str:
        """×”×’×“×¨×ھ tier ×‍×©×§×™×¢ ×œ×¤×™ ×™×ھ×¨×ھ SLH."""
        if balance >= Decimal("500000"):
            return " Ultra Strategic"
        if balance >= Decimal("100000"):
            return " Strategic"
        if balance >= Decimal("10000"):
            return " Core"
        if balance > 0:
            return " Early"
        return "â€”"

    def _is_admin(self, user_id: int) -> bool:
        admin_id = settings.ADMIN_USER_ID
        return bool(admin_id) and str(user_id) == str(admin_id)

    def _referral_reward_amount(self) -> Decimal:
        """
        ×’×•×‘×” ×”×‘×•× ×•×، ×œ×›×œ ×”×¦×ک×¨×¤×•×ھ ×“×¨×ڑ ×§×™×©×•×¨ ×”×¤× ×™×” (SLHA).
        × ×©×œ×ک ×¢"×™ SLHA_REWARD_REFERRAL, ×‘×¨×™×¨×ھ ×‍×—×“×œ 0.00001.
        """
        try:
            val = Decimal(str(settings.SLHA_REWARD_REFERRAL))
        except Exception:
            val = Decimal("0.00001")
        if val < 0:
            val = Decimal("0")
        return val

    def _apply_referral_reward(
        self,
        new_user_tid: int,
        referrer_tid: int,
    ) -> Decimal:
        """
        ×‍×¢× ×™×§ ×‘×•× ×•×، SLHA ×œ×‍×¤× ×” (×•×’×‌ ×œ×‍×•×¤× ×”), ×•×¨×•×©×‌ ×ک×¨× ×–×§×¦×™×” ×‍×،×•×’ referral_bonus_slha.
        ×‍×—×–×™×¨ ×گ×ھ ×،×›×•×‌ ×”×‘×•× ×•×، ×©× ×–×§×£ ×œ×‍×¤× ×”.
        """
        reward = self._referral_reward_amount()
        if reward <= 0:
            return Decimal("0")

        if new_user_tid == referrer_tid:
            # ×œ×گ × ×•×ھ× ×™×‌ ×¨×¤×¨×¨×œ ×œ×¢×¦×‍×™
            return Decimal("0")

        db = self._db()
        try:
            referrer = (
                db.query(models.User)
                .filter(models.User.telegram_id == referrer_tid)
                .first()
            )
            new_user = (
                db.query(models.User)
                .filter(models.User.telegram_id == new_user_tid)
                .first()
            )

            if not referrer or not new_user:
                return Decimal("0")

            # ×¢×“×›×•×ں SLHA balance â€“ ×‍×¤× ×”
            current_ref = getattr(referrer, "slha_balance", None)
            if current_ref is None:
                referrer.slha_balance = reward
            else:
                referrer.slha_balance = current_ref + reward

            # ×¢×“×›×•×ں SLHA balance â€“ ×‍×©×ھ×‍×© ×—×“×© (×گ×¤×©×¨ ×œ×©× ×•×ھ ×œض¾0 ×گ×‌ ×œ×گ ×¨×•×¦×™×‌ ×œ×ھ×ھ ×œ×•)
            current_new = getattr(new_user, "slha_balance", None)
            if current_new is None:
                new_user.slha_balance = reward
            else:
                new_user.slha_balance = current_new + reward

            # ×œ×•×’ ×‘-Transaction (amount_slh=0 â€“ ×–×” ×œ×•×’ ×‘×œ×‘×“ ×¢×‘×•×¨ SLHA)
            tx = models.Transaction(
                tx_type="referral_bonus_slha",
                from_user=None,
                to_user=referrer_tid,
                amount_slh=Decimal("0"),
            )
            db.add(tx)
            db.commit()
            return reward
        except Exception as e:
            logger.exception("Error applying referral reward: %s", e)
            db.rollback()
            return Decimal("0")
        finally:
            db.close()

    async def _log_referral_event(
        self,
        new_tg_user,
        referrer_tid: int,
        reward: Decimal,
    ) -> None:
        """
        ×©×•×œ×— ×”×•×“×¢×” ×œ×§×‘×•×¦×ھ REFERRAL_LOGS_CHAT_ID ×¢×œ ×¨×¤×¨×¨×œ ×—×“×©.
        """
        chat_id = settings.REFERRAL_LOGS_CHAT_ID
        if not chat_id:
            return
        if not self.application or not self.application.bot:
            return

        try:
            target_chat = int(chat_id)
        except ValueError:
            target_chat = chat_id

        uname = (
            f"@{new_tg_user.username}"
            if getattr(new_tg_user, "username", None)
            else "N/A"
        )

        lines: list[str] = []
        lines.append("ًںژپ New referral registered")
        lines.append(f"New user: {new_tg_user.id} ({uname})")
        lines.append(f"Referrer: {referrer_tid}")
        lines.append(f"Reward credited: {reward:.8f} SLHA (to referrer + new user)")

        try:
            await self.application.bot.send_message(
                chat_id=target_chat,
                text="\n".join(lines),
            )
        except Exception as e:
            logger.warning("Failed to send referral log: %s", e)

    def _coming_soon_text(self, tg_user, context, module_key: str) -> str:
        """
        ×‍×—×–×™×¨ ×ک×§×،×ک '×‘×§×¨×•×‘' ×¨×‘ض¾×œ×©×•× ×™ ×¢×‘×•×¨ ×‍×•×“×•×œ × ×ھ×•×ں.
        module_key = ×گ×—×“ ×‍×”×‍×¤×ھ×—×•×ھ:
            MODULE_NAME_STAKING / MODULE_NAME_SIGNALS / MODULE_NAME_ACADEMY /
            MODULE_NAME_REFERRALS / MODULE_NAME_REPORTS / MODULE_NAME_PORTFOLIO
        """
        lang = self._get_lang(tg_user, context)
        module_name = i18n.t(lang, module_key)
        title = i18n.t(lang, "COMING_SOON_TITLE")
        body = i18n.t(lang, "COMING_SOON_BODY").format(module=module_name)
        return f"{title}\n\n{body}"

    # ===== Menus (inline keyboards) =====

    def _main_menu_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        " Summary", callback_data="MENU_SUMMARY"
                    ),
                    InlineKeyboardButton(
                        " Balance", callback_data="MENU_BALANCE"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        " Wallet", callback_data="MENU_WALLET"
                    ),
                    InlineKeyboardButton(
                        " Link Wallet",
                        callback_data="MENU_LINK_WALLET",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        " History", callback_data="MENU_HISTORY"
                    ),
                    InlineKeyboardButton(
                        " Transfer", callback_data="MENU_TRANSFER"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        " Docs", callback_data="MENU_DOCS"
                    ),
                ],
            ]
        )

    def _admin_menu_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        " Admin credit help",
                        callback_data="ADMIN_HELP_CREDIT",
                    )
                ],
                [
                    InlineKeyboardButton(
                        " Ledger overview",
                        callback_data="ADMIN_HELP_HISTORY",
                    )
                ],
            ]
        )

    def _language_keyboard(self) -> InlineKeyboardMarkup:
        """
        ×›×¤×ھ×•×¨×™ ×‘×—×™×¨×ھ ×©×¤×”.
        ×گ× ×—× ×• ×‘×•× ×™×‌ ×گ×•×ھ×‌ ×‍×ھ×•×ڑ i18n ×›×“×™ ×©×”×ک×§×،×ک ×™×”×™×” × ×›×•×ں ×œ×›×œ ×©×¤×”.
        """
        # × ×©×ھ×‍×© ×ھ×‍×™×“ ×‘×گ× ×’×œ×™×ھ ×œ×”×’×“×¨×ھ ×©×‍×•×ھ ×”×›×¤×ھ×•×¨×™×‌ (×گ×—×™×“ ×œ×›×•×œ×‌)
        btn_en = i18n.t("en", "LANGUAGE_BUTTON_EN")
        btn_he = i18n.t("en", "LANGUAGE_BUTTON_HE")
        btn_ru = i18n.t("en", "LANGUAGE_BUTTON_RU")
        btn_es = i18n.t("en", "LANGUAGE_BUTTON_ES")
        btn_ar = i18n.t("en", "LANGUAGE_BUTTON_AR")

        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(btn_en, callback_data="LANG_en"),
                    InlineKeyboardButton(btn_he, callback_data="LANG_he"),
                ],
                [
                    InlineKeyboardButton(btn_ru, callback_data="LANG_ru"),
                    InlineKeyboardButton(btn_es, callback_data="LANG_es"),
                ],
                [
                    InlineKeyboardButton(btn_ar, callback_data="LANG_ar"),
                ],
            ]
        )

    # ===== Commands =====

    async def cmd_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """×—×•×•×™×™×ھ ×”×¨×©×‍×”: ×‍×،×ڑ ×¤×ھ×™×—×” + ×”×،×‘×¨ ×‍×” ×¢×•×©×™×‌ ×¢×›×©×™×•, ×¢×‌ i18n + ×¨×¤×¨×¨×œ."""
        tg_user = update.effective_user
        lang = self._get_lang(tg_user, context)

        # ×›×گ×ں ×‍×©×ھ×‍×©×™×‌ ×‘-is_new ×›×“×™ ×œ×–×”×•×ھ ×‍×©×ھ×‍×© ×—×“×© ×‘×œ×‘×“
        user, is_new = self._get_or_create_user_with_flag(tg_user)

        # ×œ×•×’ ×œ×§×‘×•×¦×ھ ×œ×•×’×™×‌ ×¨×§ ×گ×‌ ×”×‍×©×ھ×‍×© ×—×“×©
        if is_new:
            await self._log_new_investor(tg_user, user)

        # --- REFERRAL: /start ref_XXXX (×¤×•×¢×œ ×¨×§ ×‘×”×¨×©×‍×” ×”×¨×گ×©×•× ×”) ---
        if is_new and context.args:
            raw_code = context.args[0]
            if isinstance(raw_code, str) and raw_code.startswith("ref_"):
                code_part = raw_code[4:]
                try:
                    referrer_tid = int(code_part)
                except ValueError:
                    referrer_tid = None

                if referrer_tid and referrer_tid != tg_user.id:
                    reward = self._apply_referral_reward(
                        new_user_tid=tg_user.id,
                        referrer_tid=referrer_tid,
                    )
                    if reward > 0:
                        await self._log_referral_event(
                            new_tg_user=tg_user,
                            referrer_tid=referrer_tid,
                            reward=reward,
                        )

        min_invest = 100_000
        balance = user.balance_slh or Decimal("0")
        has_wallet = bool(user.bnb_address)

        lines: list[str] = []
        lines.append(i18n.t(lang, "START_TITLE"))
        lines.append("")
        lines.append(
            i18n.t(lang, "START_INTRO_MIN_INVEST").format(
                min_invest=min_invest
            )
        )
        lines.append("")
        lines.append(i18n.t(lang, "START_FEATURES_INTRO"))
        lines.append(i18n.t(lang, "START_FEATURE_1"))
        lines.append(i18n.t(lang, "START_FEATURE_2"))
        lines.append(i18n.t(lang, "START_FEATURE_3"))
        lines.append(i18n.t(lang, "START_FEATURE_4"))
        lines.append("")
        lines.append(i18n.t(lang, "START_NEXT_STEPS_TITLE"))

        if not has_wallet:
            lines.append(i18n.t(lang, "START_STEP_LINK_WALLET_MISSING"))
        else:
            lines.append(
                i18n.t(lang, "START_STEP_LINK_WALLET_SET").format(
                    bnb_address=user.bnb_address
                )
            )

        if balance == Decimal("0"):
            lines.append(i18n.t(lang, "START_STEP_BALANCE_ZERO"))
        else:
            lines.append(
                i18n.t(lang, "START_STEP_BALANCE_NONZERO").format(
                    balance=balance
                )
            )

        lines.append(i18n.t(lang, "START_STEP_WALLET"))
        lines.append(i18n.t(lang, "START_STEP_WHOAMI"))
        lines.append(i18n.t(lang, "START_STEP_SUMMARY"))
        lines.append(i18n.t(lang, "START_STEP_HISTORY"))
        lines.append("")
        lines.append(i18n.t(lang, "START_FOOTER_MENU"))
        lines.append(i18n.t(lang, "START_FOOTER_LANGUAGE"))

        await update.message.reply_text("\n".join(lines))

    async def cmd_help(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        tg_user = update.effective_user
        lang = self._get_lang(tg_user, context)

        title = i18n.t(lang, "HELP_TITLE")
        body = i18n.t(lang, "HELP_BODY")
        text = f"{title}\n\n{body}"

        await update.message.reply_text(text)

    async def cmd_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """×ھ×¤×¨×™×ک ×”×›×¤×ھ×•×¨×™×‌ ×”×¨×گ×©×™ ×œ×‍×©×§×™×¢."""
        await update.message.reply_text(
            "SLH Investor Menu â€“ choose an action:",
            reply_markup=self._main_menu_keyboard(),
        )

    async def cmd_wallet(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        user = self._ensure_user(update)

        addr = settings.COMMUNITY_WALLET_ADDRESS or ""
        token_addr = settings.SLH_TOKEN_ADDRESS or ""
        user_addr = (
            user.bnb_address
            or "You have not linked a BNB address yet (see /link_wallet)."
        )

        lines: list[str] = []
        lines.append("SLH Wallet Overview")
        lines.append("")
        lines.append("Your BNB address (BSC):")
        lines.append(f"{user_addr}")
        lines.append("")
        lines.append("Community wallet address (for deposits / tracking):")
        lines.append(f"{addr}")
        lines.append("")
        lines.append("SLH token address:")
        lines.append(f"{token_addr}")
        lines.append("")
        lines.append(
            f"Each SLH nominally represents {self._slh_price_nis():.0f} ILS."
        )

        if settings.BSC_SCAN_BASE and addr and not addr.startswith("<"):
            lines.append("")
            lines.append("View community wallet on BscScan:")
            lines.append(
                f"{settings.BSC_SCAN_BASE.rstrip('/')}/address/{addr}"
            )

        if (
            settings.BSC_SCAN_BASE
            and token_addr
            and not token_addr.startswith("<")
        ):
            lines.append("")
            lines.append("View SLH token on BscScan:")
            lines.append(
                f"{settings.BSC_SCAN_BASE.rstrip('/')}/token/{token_addr}"
            )

        if settings.BUY_BNB_URL:
            lines.append("")
            lines.append("External BNB purchase link (optional):")
            lines.append(settings.BUY_BNB_URL)

        if settings.STAKING_INFO_URL:
            lines.append("")
            lines.append("BNB staking info:")
            lines.append(settings.STAKING_INFO_URL)

        await update.message.reply_text("\n".join(lines))

    async def cmd_link_wallet(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """
        ×©× ×™ ×‍×¦×‘×™×‌:
        1) /link_wallet -> ×©×•×گ×œ ×گ×•×ھ×ڑ ×œ×©×œ×•×— ×›×ھ×•×‘×ھ ×‘×”×•×“×¢×” ×”×‘×گ×”
        2) /link_wallet 0xABC... -> ×©×•×‍×¨ ×‍×™×“ ×گ×ھ ×”×›×ھ×•×‘×ھ ×‍×”×¤×§×•×“×”
        """
        tg_user = update.effective_user
        self._ensure_user(update)

        # ×گ×‌ × ×©×œ×—×” ×›×ھ×•×‘×ھ ×‘×ھ×•×ڑ ×”×¤×§×•×“×” ×¢×¦×‍×”
        if context.args:
            addr = context.args[0].strip()
            if not addr.startswith("0x") or len(addr) < 20:
                await update.message.reply_text(
                    "Address seems invalid.\n"
                    "Usage: /link_wallet 0xyouraddress or send the address after /link_wallet."
                )
                return

            db = self._db()
            try:
                user = crud.get_or_create_user(
                    db,
                    telegram_id=tg_user.id,
                    username=tg_user.username,
                )
                crud.set_bnb_address(db, user, addr)
                await update.message.reply_text(
                    f"Your BNB address was saved:\n{addr}"
                )
            finally:
                db.close()

            context.user_data["state"] = None
            return

        # ×‍×¦×‘ ×¨×’×™×œ â€“ ×‍×‘×§×© ×›×ھ×•×‘×ھ ×‘×”×•×“×¢×” ×”×‘×گ×”
        context.user_data["state"] = STATE_AWAITING_BNB_ADDRESS
        await update.message.reply_text(
            "Please send your BNB address (BSC network, usually starts with 0x...)."
        )

    async def cmd_balance(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        db = self._db()
        try:
            tg_user = update.effective_user
            user = crud.get_or_create_user(
                db,
                telegram_id=tg_user.id,
                username=tg_user.username,
            )
            balance = user.balance_slh or Decimal("0")
            price = self._slh_price_nis()
            value_nis = balance * price

            lines: list[str] = []
            lines.append("SLH Off-Chain Balance")
            lines.append("")
            lines.append(f"Current balance: {balance:.4f} SLH")
            lines.append(
                f"Nominal value: {value_nis:.2f} ILS (at {price:.0f} ILS per SLH)"
            )
            lines.append("")

            onchain_bnb = None
            onchain_slh = None

            if user.bnb_address and settings.BSC_RPC_URL:
                try:
                    on = (
                        blockchain.get_onchain_balances(user.bnb_address)
                        or {}
                    )
                    onchain_bnb = on.get("bnb")
                    onchain_slh = on.get("slh")
                except Exception as e:
                    logger.warning(
                        "On-chain balance fetch failed: %s", e
                    )
                    onchain_bnb = None
                    onchain_slh = None

            lines.append("On-Chain view (BNB Chain):")
            if onchain_bnb is not None:
                lines.append(f"- BNB: {onchain_bnb:.6f} BNB")
            else:
                lines.append(
                    "- BNB: unavailable (RPC / address / node error)"
                )

            if onchain_slh is not None:
                lines.append(f"- SLH: {onchain_slh:.6f} SLH")
            else:
                lines.append(
                    "- SLH: unavailable (token / RPC / node error)"
                )

            lines.append("")
            lines.append(
                "This reflects allocations recorded for you inside the system."
            )
            lines.append(
                "There is no redemption yet â€“ only future usage inside the ecosystem."
            )

            await update.message.reply_text("\n".join(lines))
        finally:
            db.close()

    async def cmd_whoami(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """× ×•×ھ×ں ×—×•×•×™×™×ھ "×گ× ×™ ×¨×©×•×‌ ×‘×‍×¢×¨×›×ھ" + ×‍×¦×™×’ ×’×‌ SLHA."""
        db = self._db()
        try:
            tg_user = update.effective_user
            user = crud.get_or_create_user(
                db,
                telegram_id=tg_user.id,
                username=tg_user.username,
            )
            balance = user.balance_slh or Decimal("0")

            # SLHA balance (internal points)
            slha_balance = getattr(user, "slha_balance", None)
            if slha_balance is None:
                slha_balance = Decimal("0")

            lines: list[str] = []
            lines.append("Your SLH Investor Profile")
            lines.append("")
            lines.append(f"Telegram ID: {tg_user.id}")
            lines.append(
                f"Username: @{tg_user.username}"
                if tg_user.username
                else "Username: N/A"
            )
            lines.append(
                f"BNB address: {user.bnb_address or 'Not linked yet (use /link_wallet)'}"
            )
            lines.append(f"SLH balance: {balance:.4f} SLH")
            lines.append(
                f"Internal SLHA points: {slha_balance:.8f} SLHA"
            )
            lines.append("")
            lines.append(
                "SLH = off-chain allocation units in the investor ledger."
            )
            lines.append(
                "SLHA = internal reward points for referrals, activity and future modules."
            )
            lines.append("")
            lines.append(
                "You can see your referral link and stats via /referrals."
            )

            await update.message.reply_text("\n".join(lines))
        finally:
            db.close()

    async def cmd_summary(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """×“×©×‘×•×¨×“ ×‍×©×§×™×¢ ×‘×‍×،×ڑ ×گ×—×“ â€“ ×›×•×œ×œ SLHA."""
        db = self._db()
        try:
            tg_user = update.effective_user
            user = crud.get_or_create_user(
                db,
                telegram_id=tg_user.id,
                username=tg_user.username,
            )
            balance = user.balance_slh or Decimal("0")
            price = self._slh_price_nis()
            value_nis = balance * price

            # SLHA balance (internal reward points)
            slha_balance = getattr(user, "slha_balance", None)
            if slha_balance is None:
                slha_balance = Decimal("0")

            addr = settings.COMMUNITY_WALLET_ADDRESS or ""
            token_addr = settings.SLH_TOKEN_ADDRESS or ""
            user_addr = (
                user.bnb_address or "Not linked yet (use /link_wallet)."
            )

            onchain_bnb = None
            onchain_slh = None
            if user.bnb_address and settings.BSC_RPC_URL:
                try:
                    on = blockchain.get_onchain_balances(user.bnb_address)
                    onchain_bnb = on.get("bnb")
                    onchain_slh = on.get("slh")
                except Exception as e:
                    logger.warning(
                        "On-chain balance fetch failed: %s", e
                    )

            tier = self._investor_tier(balance)
            hypothetical_yield_rate = Decimal("0.10")
            projected_yearly_yield = balance * hypothetical_yield_rate

            lines: list[str] = []
            lines.append("SLH Investor Dashboard")
            lines.append("")
            lines.append("Profile:")
            lines.append(f"- Telegram ID: {tg_user.id}")
            lines.append(
                f"- Username: @{tg_user.username}"
                if tg_user.username
                else "- Username: N/A"
            )
            lines.append(f"- Investor tier: {tier}")
            lines.append("")
            lines.append("Wallets:")
            lines.append(f"- Your BNB (BSC): {user_addr}")
            lines.append(f"- Community wallet: {addr}")
            lines.append(f"- SLH token: {token_addr}")
            lines.append("")
            lines.append("Balance (Off-Chain System Ledger):")
            lines.append(f"- SLH: {balance:.4f} SLH")
            lines.append(
                f"- Nominal ILS value: {value_nis:.2f} ILS "
                f"(at {price:.0f} ILS per SLH)"
            )
            lines.append(
                f"- Hypothetical yearly yield (10%): "
                f"{projected_yearly_yield:.4f} SLH"
            )
            lines.append(
                f"- Internal SLHA points: {slha_balance:.8f} SLHA"
            )
            lines.append("")
            lines.append(
                "SLH = off-chain allocation units that mirror investor deposits."
            )
            lines.append(
                "SLHA = internal reward points for referrals, activity and "
                "future staking / AI modules."
            )
            lines.append("")

            if user.bnb_address and (
                onchain_bnb is not None or onchain_slh is not None
            ):
                lines.append(
                    "On-Chain (BNB Chain) â€“ based on your BNB address:"
                )
                if onchain_bnb is not None:
                    lines.append(f"- BNB: {onchain_bnb:.6f} BNB")
                else:
                    lines.append(
                        "- BNB: unavailable (RPC or address error)"
                    )
                if onchain_slh is not None:
                    lines.append(f"- SLH: {onchain_slh:.6f} SLH")
                else:
                    lines.append(
                        "- SLH: unavailable (token or RPC error)"
                    )
                lines.append("")

            if settings.BSC_SCAN_BASE and addr and not addr.startswith("<"):
                lines.append("On BscScan:")
                lines.append(
                    f"- Community wallet: {settings.BSC_SCAN_BASE.rstrip('/')}/address/{addr}"
                )

            if (
                settings.BSC_SCAN_BASE
                and token_addr
                and not token_addr.startswith("<")
            ):
                lines.append(
                    f"- SLH token: {settings.BSC_SCAN_BASE.rstrip('/')}/token/{token_addr}"
                )

            if settings.DOCS_URL:
                lines.append("")
                lines.append(f"Investor Docs: {settings.DOCS_URL}")

            lines.append("")
            lines.append(
                "Key commands: /menu, /wallet, /balance, /history, "
                "/transfer, /docs, /help, /language, /referrals"
            )

            await update.message.reply_text("\n".join(lines))
        finally:
            db.close()

    async def cmd_docs(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """×§×™×©×•×¨ ×œ×‍×،×‍×›×™ ×”-DOCS ×”×¨×©×‍×™×™×‌ (README ×œ×‍×©×§×™×¢×™×‌)."""
        if not settings.DOCS_URL:
            await update.message.reply_text(
                "Investor docs URL is not configured yet.\n"
                "Please contact the SLH team."
            )
            return

        text_lines: list[str] = []
        text_lines.append("SLH Investor Documentation")
        text_lines.append("")
        text_lines.append(
            "The full investor deck, ecosystem overview and technical docs are available here:"
        )
        text_lines.append(settings.DOCS_URL)
        text_lines.append("")
        text_lines.append(
            "You can share this link with potential strategic partners and investors."
        )

        await update.message.reply_text("\n".join(text_lines))

    # === Coming soon feature modules (multi-language placeholders) ===

    async def cmd_staking(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """
        ×‍×•×“×•×œ ×،×ک×™×™×§×™× ×’ â€“ ×›×¨×’×¢ placeholder ×¢×‌ ×”×•×“×¢×ھ '×‘×§×¨×•×‘' ×‘×›×œ ×”×©×¤×•×ھ.
        ×‘×”×‍×©×ڑ × ×—×‘×¨ ×œ×›×گ×ں ×‍× ×•×¢ ×،×ک×™×™×§×™× ×’ ×گ×‍×™×ھ×™ (on/off-chain).
        """
        tg_user = update.effective_user
        _ = self._ensure_user(update)
        text = self._coming_soon_text(tg_user, context, "MODULE_NAME_STAKING")
        await update.message.reply_text(text)

    async def cmd_signals(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """
        ×‍×•×“×•×œ ×گ×•×ھ×•×ھ ×‍×،×—×¨ â€“ placeholder.
        ×‘×”×‍×©×ڑ: ×—×™×‘×•×¨ ×œ-API/AI ×©×™×™×ھ×ں ×،×™×’× ×œ×™×‌ ×œ×¤×™ ×¤×¨×•×¤×™×œ ×”×‍×©×§×™×¢.
        """
        tg_user = update.effective_user
        _ = self._ensure_user(update)
        text = self._coming_soon_text(tg_user, context, "MODULE_NAME_SIGNALS")
        await update.message.reply_text(text)

    async def cmd_academy(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """
        ×گ×§×“×‍×™×™×ھ SLH â€“ placeholder.
        ×‘×”×‍×©×ڑ: ×ھ×›× ×™ ×œ×™×‍×•×“, ×§×•×¨×،×™×‌, '×©×™×¢×•×¨ ×œ×™×•×‌' ×•×›×•'.
        """
        tg_user = update.effective_user
        _ = self._ensure_user(update)
        text = self._coming_soon_text(tg_user, context, "MODULE_NAME_ACADEMY")
        await update.message.reply_text(text)

    async def cmd_referrals(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """
        ×ھ×•×›× ×™×ھ ×”×¤× ×™×•×ھ â€“ ×¢×›×©×™×• LIVE:
        - ×§×™×©×•×¨ ×گ×™×©×™: https://t.me/<bot>?start=ref_<telegram_id>
        - ×،×¤×™×¨×ھ referrals
        - ×”×¦×’×ھ ×™×ھ×¨×ھ SLHA
        """
        db = self._db()
        try:
            tg_user = update.effective_user
            user = crud.get_or_create_user(
                db,
                telegram_id=tg_user.id,
                username=tg_user.username,
            )

            # ×§×‘×œ×ھ username ×©×œ ×”×‘×•×ک ×œ×¦×•×¨×ڑ ×§×™×©×•×¨ ×گ×™×©×™
            bot_username = None
            try:
                if self.bot and self.bot.username:
                    bot_username = self.bot.username
                else:
                    me = await context.bot.get_me()
                    bot_username = me.username
            except Exception as e:
                logger.warning("Failed to get bot username: %s", e)

            if not bot_username:
                link = "Unavailable â€“ bot username not resolved yet."
            else:
                link = f"https://t.me/{bot_username}?start=ref_{tg_user.id}"

            # ×،×ک×ک×™×،×ک×™×§×•×ھ ×¨×¤×¨×¨×œ×™×‌ â€“ ×œ×¤×™ Transactions ×‍×،×•×’ referral_bonus_slha
            txs = (
                db.query(models.Transaction)
                .filter(
                    models.Transaction.to_user == tg_user.id,
                    models.Transaction.tx_type == "referral_bonus_slha",
                )
                .all()
            )

            referrals_count = len(txs)
            reward_per = self._referral_reward_amount()

            # ×™×ھ×¨×ھ SLHA ×‘×¤×•×¢×œ â€“ ×‍×”×ک×‘×œ×”
            slha_balance = getattr(user, "slha_balance", None)
            if slha_balance is None:
                slha_balance = Decimal("0")

            lang = self._get_lang(tg_user, context)

            if lang == "he":
                lines: list[str] = []
                lines.append("×ھ×•×›× ×™×ھ ×”×¤× ×™×•×ھ â€“ SLH Global Investments")
                lines.append("")
                lines.append("×–×”×• ×”×§×™×©×•×¨ ×”×گ×™×©×™ ×©×œ×ڑ ×œ×©×™×ھ×•×£ (×—×‘×¨×™×‌, ×‍×©×¤×—×”, ×œ×§×•×—×•×ھ):")
                lines.append(link)
                lines.append("")
                lines.append(f"×‍×،×¤×¨ ×‍×¦×ک×¨×¤×™×‌ ×©×–×•×”×• ×“×¨×ڑ ×”×§×™×©×•×¨ ×©×œ×ڑ: {referrals_count}")
                lines.append(
                    f"×™×ھ×¨×ھ SLHA ×¤× ×™×‍×™×ھ (× ×§×•×“×•×ھ ×‍×¢×¨×›×ھ): {slha_balance:.8f} SLHA"
                )
                lines.append("")
                lines.append(
                    f"×›×¨×’×¢, ×›×œ ×‍×¦×ک×¨×£ ×“×¨×ڑ ×”×§×™×©×•×¨ ×‍×–×›×” ×‘-{reward_per:.8f} SLHA "
                    f"(â‰ˆ 1 â‚ھ × ×•×‍×™× ×œ×™) â€“ ×‍×—×•×œ×§ ×’×‌ ×œ×‍×¤× ×” ×•×’×‌ ×œ×‍×¦×ک×¨×£."
                )
                lines.append("")
                lines.append(
                    "×”× ×§×•×“×•×ھ ×”×ں Off-Chain ×•×™×©×‍×©×• ×‘×”×‍×©×ڑ ×œ×،×ک×™×™×§×™× ×’, ×”×ک×‘×•×ھ, "
                    "×’×™×©×” ×œ×‍×•×“×•×œ×™×‌ ×‍×ھ×§×“×‍×™×‌ ×•×œ-AI Trading Tutor."
                )
                lines.append("")
                lines.append(
                    "×›×›×œ ×©×ھ×©×ھ×£ ×™×•×ھ×¨ ×•×ھ×‘× ×” ×¨×©×ھ ×‍×©×§×™×¢×™×‌ ×،×‘×™×‘×ڑ, ×›×ڑ ×ھ×•×›×œ/×™ ×œ×¤×ھ×•×— "
                    "×¢×•×“ ×©×›×‘×•×ھ ×‘×گ×§×•-×،×™×،×ک×‌ ×©×œ SLH."
                )
            else:
                lines = []
                lines.append("Referral Program â€“ SLH Global Investments")
                lines.append("")
                lines.append(
                    "Your personal invite link (share with friends, family, clients):"
                )
                lines.append(link)
                lines.append("")
                lines.append(f"Referrals detected via your link: {referrals_count}")
                lines.append(
                    f"Current internal SLHA balance: {slha_balance:.8f} SLHA"
                )
                lines.append("")
                lines.append(
                    f"Each new investor via your link currently grants "
                    f"{reward_per:.8f} SLHA (â‰ˆ 1 ILS nominal value), "
                    "credited both to you and to the new investor."
                )
                lines.append("")
                lines.append(
                    "These points are off-chain and will be used later for staking tiers, "
                    "bonuses and access to advanced AI trading modules."
                )
                lines.append("")
                lines.append(
                    "The more you share and onboard investors, the more you unlock inside "
                    "the SLH ecosystem."
                )

            await update.message.reply_text("\n".join(lines))
        finally:
            db.close()

    async def cmd_reports(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """
        ×“×•×—×•×ھ ×‍×©×§×™×¢×™×‌ â€“ placeholder.
        ×‘×”×‍×©×ڑ: PDF/HTML, ×،×™×›×•×‍×™ ×—×•×“×©, ×ھ×©×•×گ×•×ھ ×•×›×•'.
        """
        tg_user = update.effective_user
        _ = self._ensure_user(update)
        text = self._coming_soon_text(tg_user, context, "MODULE_NAME_REPORTS")
        await update.message.reply_text(text)

    async def cmd_portfolio_pro(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """
        ×¤×•×¨×ک×¤×•×œ×™×• ×‍×ھ×§×“×‌ â€“ placeholder.
        ×‘×”×‍×©×ڑ: ×’×¨×¤×™×‌, ×¤×™×œ×•×—, × ×™×ھ×•×— ×،×™×›×•× ×™×‌.
        """
        tg_user = update.effective_user
        _ = self._ensure_user(update)
        text = self._coming_soon_text(
            tg_user, context, "MODULE_NAME_PORTFOLIO"
        )
        await update.message.reply_text(text)

    async def cmd_onchain_balance(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show live on-chain BNB & SLH balances for the linked wallet."""
        db = self._db()
        try:
            tg_user = update.effective_user
            user = crud.get_or_create_user(
                db,
                telegram_id=tg_user.id,
                username=tg_user.username,
            )

            if not user.bnb_address:
                await update.message.reply_text(
                    "You have not linked a BNB address yet.\nUse /link_wallet first."
                )
                return

            if not settings.BSC_RPC_URL:
                await update.message.reply_text(
                    "On-chain RPC is not configured on the server (BSC_RPC_URL missing)."
                )
                return

            try:
                on = blockchain.get_onchain_balances(user.bnb_address)
                onchain_bnb = on.get("bnb")
                onchain_slh = on.get("slh")
            except Exception as e:
                logger.warning("On-chain balance fetch failed: %s", e)
                await update.message.reply_text(
                    "Failed to fetch on-chain balances (RPC or token error)."
                )
                return

            lines: list[str] = []
            lines.append("On-Chain Balances (BNB Smart Chain)")
            lines.append(f"Address: {user.bnb_address}")
            lines.append("")

            if onchain_bnb is not None:
                lines.append(f"- BNB: {onchain_bnb:.6f} BNB")
            else:
                lines.append(
                    "- BNB: unavailable (RPC or address error)"
                )

            if onchain_slh is not None:
                lines.append(f"- SLH: {onchain_slh:.6f} SLH")
            else:
                lines.append(
                    "- SLH: unavailable (token or RPC error)"
                )

            if settings.BSC_SCAN_BASE:
                base = settings.BSC_SCAN_BASE.rstrip("/")
                lines.append("")
                lines.append("On BscScan:")
                lines.append(f"- Wallet: {base}/address/{user.bnb_address}")
                if settings.SLH_TOKEN_ADDRESS:
                    lines.append(
                        f"- SLH token: {base}/token/{settings.SLH_TOKEN_ADDRESS}"
                    )

            await update.message.reply_text("\n".join(lines))
        finally:
            db.close()

    async def cmd_history(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """
        ×‍×¦×™×’ ×¢×“ 10 ×”×ک×¨× ×–×§×¦×™×•×ھ ×”×گ×—×¨×•× ×•×ھ ×©×‘×”×ں ×”×‍×©×ھ×‍×© ×‍×¢×•×¨×‘ (Off-Chain).
        ×¢×•×‘×“ ×‍×•×œ Transaction.from_user / Transaction.to_user (×‍×–×”×™ ×ک×œ×’×¨×‌).
        """
        db = self._db()
        try:
            tg_user = update.effective_user
            user = crud.get_or_create_user(
                db,
                telegram_id=tg_user.id,
                username=tg_user.username,
            )
            my_tid = user.telegram_id

            q = (
                db.query(models.Transaction)
                .filter(
                    or_(
                        models.Transaction.from_user == my_tid,
                        models.Transaction.to_user == my_tid,
                    )
                )
                .order_by(models.Transaction.created_at.desc())
                .limit(10)
            )
            txs = q.all()

            if not txs:
                await update.message.reply_text(
                    "No recent transactions found in the internal ledger."
                )
                return

            lines: list[str] = []
            lines.append("Last transactions (internal ledger)")
            lines.append("Most recent first (max 10):")
            lines.append("")

            for tx in txs:
                from_id = getattr(tx, "from_user", None)
                to_id = getattr(tx, "to_user", None)
                tx_type = getattr(tx, "tx_type", "N/A")
                amount = getattr(tx, "amount_slh", 0)
                created_at = getattr(tx, "created_at", None)

                if created_at is not None:
                    try:
                        ts = created_at.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        ts = str(created_at)
                else:
                    ts = "N/A"

                if from_id == my_tid and to_id == my_tid:
                    direction = "SELF"
                elif from_id == my_tid:
                    direction = "OUT"
                elif to_id == my_tid:
                    direction = "IN"
                else:
                    direction = "OTHER"

                lines.append(
                    f"[{ts}] {direction} â€“ {amount:.4f} SLH (type={tx_type}, id={tx.id})"
                )

            await update.message.reply_text("\n".join(lines))
        except Exception as e:
            logger.exception("Error while fetching history: %s", e)
            await update.message.reply_text(
                "Could not load transaction history.\nPlease contact the SLH team."
            )
        finally:
            db.close()

    async def cmd_transfer(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        self._ensure_user(update)
        context.user_data["state"] = STATE_AWAITING_TRANSFER_TARGET
        await update.message.reply_text(
            "Type the target username you want to transfer to (e.g. @username)."
        )

    async def cmd_send_slh(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """×§×™×¦×•×¨ ×“×¨×ڑ: /send_slh <amount> <@username|user_id>"""
        self._ensure_user(update)

        parts = (update.message.text or "").split()
        if len(parts) != 3:
            await update.message.reply_text(
                "Usage: /send_slh <amount> <@username|user_id>"
            )
            return

        try:
            amount = float(parts[1].replace(",", ""))
        except ValueError:
            await update.message.reply_text("Invalid amount.")
            return

        target = parts[2]

        db = self._db()
        try:
            tg_user = update.effective_user
            sender = crud.get_or_create_user(
                db,
                telegram_id=tg_user.id,
                username=tg_user.username,
            )

            if target.startswith("@"):
                username = target[1:]
                receiver = (
                    db.query(models.User)
                    .filter(models.User.username == username)
                    .first()
                )
            else:
                try:
                    tid = int(target)
                except ValueError:
                    await update.message.reply_text(
                        "Invalid target format."
                    )
                    return

                receiver = (
                    db.query(models.User)
                    .filter(models.User.telegram_id == tid)
                    .first()
                )

            if not receiver:
                await update.message.reply_text(
                    "Target user not found in the system.\n"
                    "They must send /start once."
                )
                return

            try:
                tx = crud.internal_transfer(
                    db,
                    sender=sender,
                    receiver=receiver,
                    amount_slh=amount,
                )
            except ValueError as e:
                await update.message.reply_text(str(e))
                return

            await update.message.reply_text(
                "Transfer completed:\n"
                f"{amount:.4f} SLH -> @{receiver.username or receiver.telegram_id}\n"
                f"Transaction ID: {tx.id}"
            )
        finally:
            db.close()

    async def cmd_admin_credit(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """
        ×گ×“×‍×™×ں ×‘×œ×‘×“: ×ک×¢×™× ×ھ SLH ×œ×‍×©×ھ×‍×© ×œ×¤×™ ID.
        /admin_credit <telegram_id> <amount>
        """
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("This command is admin-only.")
            return

        parts = (update.message.text or "").split()
        if len(parts) != 3:
            await update.message.reply_text(
                "Usage: /admin_credit <telegram_id> <amount>"
            )
            return

        try:
            target_id = int(parts[1])
            amount = float(parts[2])
        except ValueError:
            await update.message.reply_text(
                "Invalid parameters.\nCheck ID and amount."
            )
            return

        db = self._db()
        try:
            user = crud.get_or_create_user(
                db,
                telegram_id=target_id,
                username=None,
            )
            tx = crud.change_balance(
                db,
                user=user,
                delta_slh=amount,
                tx_type="admin_credit",
                from_user=None,
                to_user=target_id,
            )

            await update.message.reply_text(
                f"Credited {amount:.4f} SLH to user {target_id}.\n"
                f"Transaction ID: {tx.id}"
            )
        finally:
            db.close()

    async def cmd_admin_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """×ھ×¤×¨×™×ک ×گ×“×‍×™×ں â€“ ×–×‍×™×ں ×¨×§ ×œ×‍×–×”×” ×”×‍×•×’×“×¨ ×‘-ADMIN_USER_ID."""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("This command is admin-only.")
            return

        await update.message.reply_text(
            "SLH Admin Menu â€“ tools for managing investor balances:",
            reply_markup=self._admin_menu_keyboard(),
        )

    async def cmd_admin_list_users(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """×گ×“×‍×™×ں: ×¨×©×™×‍×ھ ×”×‍×©×ھ×‍×©×™×‌ ×‘×‍×¢×¨×›×ھ + ×™×ھ×¨×•×ھ."""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("This command is admin-only.")
            return

        db = self._db()
        try:
            q = (
                db.query(models.User)
                .order_by(models.User.balance_slh.desc())
                .limit(50)
            )
            users = q.all()

            if not users:
                await update.message.reply_text(
                    "No users found in the system yet."
                )
                return

            lines: list[str] = []
            lines.append("Admin â€“ Users (top 50 by SLH balance):")
            lines.append("")

            for u in users:
                bal = u.balance_slh or Decimal("0")
                tier = self._investor_tier(bal)
                lines.append(
                    f"- ID {u.telegram_id} | @{u.username or 'N/A'} | "
                    f"{bal:.4f} SLH | tier={tier} | "
                    f"BNB={u.bnb_address or 'â€”'}"
                )

            await update.message.reply_text("\n".join(lines))
        finally:
            db.close()

    async def cmd_admin_ledger(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """×گ×“×‍×™×ں: ×ھ×¦×•×’×” ×’×œ×•×‘×œ×™×ھ ×©×œ ×”-Ledger (×¢×“ 50 ×”×ک×¨× ×–×§×¦×™×•×ھ ×”×گ×—×¨×•× ×•×ھ)."""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("This command is admin-only.")
            return

        db = self._db()
        try:
            txs = (
                db.query(models.Transaction)
                .order_by(models.Transaction.created_at.desc())
                .limit(50)
                .all()
            )

            if not txs:
                await update.message.reply_text(
                    "No transactions in the ledger yet."
                )
                return

            lines: list[str] = []
            lines.append("Admin â€“ Global Ledger (last 50 transactions):")
            lines.append("")

            for tx in txs:
                from_id = getattr(tx, "from_user", None)
                to_id = getattr(tx, "to_user", None)
                tx_type = getattr(tx, "tx_type", "N/A")
                amount = getattr(tx, "amount_slh", 0)
                created_at = getattr(tx, "created_at", None)

                if created_at is not None:
                    try:
                        ts = created_at.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        ts = str(created_at)
                else:
                    ts = "N/A"

                lines.append(
                    f"[{ts}] {tx_type} â€“ {amount:.4f} SLH | "
                    f"from={from_id or '-'} -> to={to_id or '-'} | id={tx.id}"
                )

            await update.message.reply_text("\n".join(lines))
        finally:
            db.close()

    # === NEW: health + language commands ===

    async def cmd_ping(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """×‘×“×™×§×ھ ×—×™×™×‌ ×‍×”×™×¨×” ×‘×§×œ×™×™× ×ک."""
        await update.message.reply_text("pong")

    async def cmd_admin_selftest(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """×گ×“×‍×™×ں ×‘×œ×‘×“: ×‍×¨×™×¥ self-test ×¢×‍×•×§ ×•×‍×¦×™×’ ×“×•\"×— ×‍×¦×‘."""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("This command is admin-only.")
            return

        result = run_selftest(quick=False)
        status = result.get("status", "unknown")
        checks = result.get("checks", {})

        lines: list[str] = []
        lines.append(f"Self-test status: {status}")
        lines.append("")

        for name, check in checks.items():
            ok = check.get("ok", False)
            skipped = check.get("skipped", False)

            if ok and not skipped:
                lines.append(f"âœ… {name}")
            elif skipped:
                reason = check.get("reason", "")
                lines.append(f"âڑھ {name} â€“ skipped ({reason})")
            else:
                err = check.get("error", "unknown error")
                lines.append(f"â‌Œ {name} â€“ {err}")

        await update.message.reply_text("\n".join(lines))

    async def cmd_language(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """
        ×‍×¦×™×’ ×œ×‍×©×ھ×‍×© ×ھ×¤×¨×™×ک ×‘×—×™×¨×ھ ×©×¤×”.
        ×‘×©×œ×‘ ×”×–×” ×گ× ×—× ×• ×©×•×‍×¨×™×‌ ×گ×ھ ×”×”×¢×“×¤×” ×‘×–×™×›×¨×•×ں (context.user_data),
        ×•×گ×—"×› × ×•×›×œ ×œ×”×¢×‘×™×¨ ×گ×ھ ×›×œ ×”×”×•×“×¢×•×ھ ×œ×”×©×ھ×‍×© ×‘-i18n.
        """
        tg_user = update.effective_user
        lang = self._get_lang(tg_user, context)
        title = i18n.t(lang, "LANGUAGE_MENU_TITLE")

        await update.message.reply_text(
            title,
            reply_markup=self._language_keyboard(),
        )

    # ===== Callback handlers =====

    async def cb_wallet_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        query = update.callback_query
        await query.answer()
        data = query.data

        if data == "WALLET_BALANCE":
            fake_update = Update(update.update_id, message=query.message)
            await self.cmd_balance(fake_update, context)
        elif data == "WALLET_DETAILS":
            fake_update = Update(update.update_id, message=query.message)
            await self.cmd_wallet(fake_update, context)
        elif data == "WALLET_BUY_BNB":
            if settings.BUY_BNB_URL:
                await query.edit_message_text(
                    f"Suggested BNB provider:\n{settings.BUY_BNB_URL}"
                )
            else:
                await query.edit_message_text(
                    "BUY_BNB_URL not set in environment variables."
                )

    async def cb_main_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """×›×¤×ھ×•×¨×™ MENU_* ×¢×‘×•×¨ ×”×‍×©×§×™×¢."""
        query = update.callback_query
        await query.answer()
        data = query.data

        fake_update = Update(update.update_id, message=query.message)

        if data == "MENU_SUMMARY":
            await self.cmd_summary(fake_update, context)
        elif data == "MENU_BALANCE":
            await self.cmd_balance(fake_update, context)
        elif data == "MENU_WALLET":
            await self.cmd_wallet(fake_update, context)
        elif data == "MENU_LINK_WALLET":
            await self.cmd_link_wallet(fake_update, context)
        elif data == "MENU_HISTORY":
            await self.cmd_history(fake_update, context)
        elif data == "MENU_TRANSFER":
            await self.cmd_transfer(fake_update, context)
        elif data == "MENU_DOCS":
            await self.cmd_docs(fake_update, context)

    async def cb_language(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """
        Callback ×©×œ ×‘×—×™×¨×ھ ×©×¤×” â€“ LANG_en / LANG_he / LANG_ru / LANG_es / LANG_ar.
        ×‍×¢×“×›×ں context.user_data["lang"] ×•×‍×¦×™×’ ×”×•×“×¢×ھ ×گ×™×©×•×¨.
        """
        query = update.callback_query
        await query.answer()
        data = query.data  # ×œ×‍×©×œ "LANG_he"

        parts = data.split("_", 1)
        if len(parts) != 2:
            return

        raw_lang = parts[1]
        lang = i18n.normalize_lang(raw_lang)
        context.user_data["lang"] = lang

        # ×”×•×“×¢×ھ ×گ×™×©×•×¨ ×‘×©×¤×” ×”× ×‘×—×¨×ھ
        if lang == "he":
            confirm = i18n.t(lang, "LANGUAGE_SET_CONFIRM_HE")
        elif lang == "ru":
            confirm = i18n.t(lang, "LANGUAGE_SET_CONFIRM_RU")
        elif lang == "es":
            confirm = i18n.t(lang, "LANGUAGE_SET_CONFIRM_ES")
        else:
            confirm = i18n.t(lang, "LANGUAGE_SET_CONFIRM")

        await query.edit_message_text(confirm)

    async def cb_admin_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """×›×¤×ھ×•×¨×™ ADMIN_* ×¢×‘×•×¨ ×گ×“×‍×™×ں."""
        query = update.callback_query
        await query.answer()
        data = query.data

        if not self._is_admin(query.from_user.id):
            await query.edit_message_text("Admin only.")
            return

        if data == "ADMIN_HELP_CREDIT":
            text = (
                "Admin credit tool:\n\n"
                "Use:\n"
                "/admin_credit <telegram_id> <amount>\n\n"
                "Example:\n"
                "/admin_credit 224223270 199999.877\n\n"
                "This will create an internal ledger transaction and update "
                "the user's off-chain SLH balance."
            )
            await query.edit_message_text(text)
        elif data == "ADMIN_HELP_HISTORY":
            text = (
                "Ledger overview:\n\n"
                "For now, use /history from a user account to see their last 10 transactions,\n"
                "or /admin_ledger to see the global last 50 transactions.\n"
                "In future iterations we can add global admin views and filters."
            )
            await query.edit_message_text(text)

    # ===== Text handler =====

    async def handle_text(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        state = context.user_data.get("state")
        text = (update.message.text or "").strip()

        db = self._db()
        try:
            tg_user = update.effective_user
            user = crud.get_or_create_user(
                db,
                telegram_id=tg_user.id,
                username=tg_user.username,
            )

            if state == STATE_AWAITING_BNB_ADDRESS:
                context.user_data["state"] = None

                if not text.startswith("0x") or len(text) < 20:
                    await update.message.reply_text(
                        "Address seems invalid.\nTry again with /link_wallet."
                    )
                    return

                crud.set_bnb_address(db, user, text)
                await update.message.reply_text(
                    f"Your BNB address was saved:\n{text}"
                )
                return

            if state == STATE_AWAITING_TRANSFER_TARGET:
                if not text.startswith("@"):
                    await update.message.reply_text(
                        "Send a username starting with @username"
                    )
                    return

                context.user_data["transfer_target_username"] = text[1:]
                context.user_data["state"] = (
                    STATE_AWAITING_TRANSFER_AMOUNT
                )
                await update.message.reply_text(
                    f"Great.\nNow type the SLH amount you want to transfer to {text}."
                )
                return

            if state == STATE_AWAITING_TRANSFER_AMOUNT:
                context.user_data["state"] = None

                try:
                    amount = float(text.replace(",", ""))
                except ValueError:
                    await update.message.reply_text(
                        "Could not read amount.\nTry again with /transfer."
                    )
                    return

                if amount <= 0:
                    await update.message.reply_text(
                        "Amount must be greater than zero."
                    )
                    return

                target_username = context.user_data.get(
                    "transfer_target_username"
                )
                if not target_username:
                    await update.message.reply_text(
                        "Target not found.\nTry again with /transfer."
                    )
                    return

                receiver = (
                    db.query(models.User)
                    .filter(models.User.username == target_username)
                    .first()
                )

                if not receiver:
                    await update.message.reply_text(
                        "No user with that username in the system.\n"
                        "They must send /start once before receiving transfers."
                    )
                    return

                try:
                    tx = crud.internal_transfer(
                        db,
                        sender=user,
                        receiver=receiver,
                        amount_slh=amount,
                    )
                except ValueError:
                    await update.message.reply_text(
                        "Insufficient balance for this transfer."
                    )
                    return

                await update.message.reply_text(
                    "Transfer completed:\n"
                    f"{amount:.4f} SLH -> @{receiver.username or receiver.telegram_id}\n"
                    f"Transaction ID: {tx.id}"
                )
                return

            # no special state â€“ ×”×•×“×¢×” ×—×•×¤×©×™×ھ
            lang = self._get_lang(tg_user, context)
            fallback = i18n.t(lang, "GENERIC_UNKNOWN_COMMAND")
            await update.message.reply_text(fallback)
        finally:
            db.close()


_bot_instance = InvestorWalletBot()


async def initialize_bot():
    await _bot_instance.initialize()


async def process_webhook(update_dict: dict):
    if not _bot_instance.application:
        logger.error("Application is not initialized")
        return

    update = Update.de_json(update_dict, _bot_instance.application.bot)
    await _bot_instance.application.process_update(update)
