import logging
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
from app import crud, models
from app import blockchain

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

    # ===== Initialization =====
    async def initialize(self):
        if not settings.BOT_TOKEN:
            logger.warning("BOT_TOKEN is not set, skipping Telegram bot initialization")
            return

        self.application = Application.builder().token(settings.BOT_TOKEN).build()
        self.bot = self.application.bot

        # Commands
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("menu", self.cmd_menu))
        self.application.add_handler(CommandHandler("wallet", self.cmd_wallet))
        self.application.add_handler(CommandHandler("link_wallet", self.cmd_link_wallet))
        self.application.add_handler(CommandHandler("balance", self.cmd_balance))
        self.application.add_handler(CommandHandler("history", self.cmd_history))
        self.application.add_handler(CommandHandler("transfer", self.cmd_transfer))
        self.application.add_handler(CommandHandler("send_slh", self.cmd_send_slh))
        self.application.add_handler(CommandHandler("whoami", self.cmd_whoami))
        self.application.add_handler(CommandHandler("summary", self.cmd_summary))
        self.application.add_handler(CommandHandler("docs", self.cmd_docs))

        # Admin-only commands
        self.application.add_handler(CommandHandler("admin_credit", self.cmd_admin_credit))
        self.application.add_handler(CommandHandler("admin_menu", self.cmd_admin_menu))

        # Callback for inline buttons – משקיעים
        self.application.add_handler(
            CallbackQueryHandler(self.cb_wallet_menu, pattern=r"^WALLET_")
        )
        self.application.add_handler(
            CallbackQueryHandler(self.cb_main_menu, pattern=r"^MENU_")
        )

        # Callback לאדמין
        self.application.add_handler(
            CallbackQueryHandler(self.cb_admin_menu, pattern=r"^ADMIN_")
        )

        # Generic text handler (for address / amounts / usernames)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text)
        )

        # חובה ב-ptb v21 לפני process_update
        await self.application.initialize()

        # Webhook mode
        if settings.WEBHOOK_URL:
            webhook_url = f"{settings.WEBHOOK_URL.rstrip('/')}/webhook/telegram"
            await self.bot.set_webhook(webhook_url)
            logger.info(f"Webhook set to: {webhook_url}")
        else:
            logger.info("No WEBHOOK_URL set - you can run in polling mode locally")

        logger.info("InvestorWalletBot initialized")

    # ===== Helpers =====
    def _ensure_user(self, update: Update) -> models.User:
        db = self._db()
        try:
            tg_user = update.effective_user
            return crud.get_or_create_user(
                db, telegram_id=tg_user.id, username=tg_user.username
            )
        finally:
            db.close()

    def _slh_price_nis(self) -> Decimal:
        """
        מחיר SLH בניס (ברירת מחדל: 444) כ-Decimal.
        """
        try:
            return Decimal(str(settings.SLH_PRICE_NIS))
        except Exception:
            return Decimal("444")

    # ===== Menus (inline keyboards) =====

    def _main_menu_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("📊 Summary", callback_data="MENU_SUMMARY"),
                    InlineKeyboardButton("💰 Balance", callback_data="MENU_BALANCE"),
                ],
                [
                    InlineKeyboardButton("👛 Wallet", callback_data="MENU_WALLET"),
                    InlineKeyboardButton("🔗 Link Wallet", callback_data="MENU_LINK_WALLET"),
                ],
                [
                    InlineKeyboardButton("📜 History", callback_data="MENU_HISTORY"),
                    InlineKeyboardButton("🔁 Transfer", callback_data="MENU_TRANSFER"),
                ],
                [
                    InlineKeyboardButton("📄 Docs", callback_data="MENU_DOCS"),
                ],
            ]
        )

    def _admin_menu_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "💳 Admin credit help", callback_data="ADMIN_HELP_CREDIT"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📜 Ledger overview", callback_data="ADMIN_HELP_HISTORY"
                    )
                ],
            ]
        )

    # ===== Commands =====

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        חוויית הרשמה: מסך פתיחה + הסבר מה עושים עכשיו.
        """
        user = self._ensure_user(update)

        min_invest = 100_000
        balance = user.balance_slh or Decimal("0")
        has_wallet = bool(user.bnb_address)

        text_lines = []

        text_lines.append("Welcome to the SLH Investor Gateway.")
        text_lines.append("")
        text_lines.append(
            f"This bot is intended for strategic investors (minimum {min_invest:,.0f} ILS)."
        )
        text_lines.append("")
        text_lines.append("With this bot you can:")
        text_lines.append("- Link your personal BNB wallet (BSC)")
        text_lines.append("- View your off-chain SLH balance")
        text_lines.append("- Transfer SLH units to other investors (off-chain)")
        text_lines.append("- Access external links for BNB purchase and staking info")
        text_lines.append("")
        text_lines.append("Next steps:")

        if not has_wallet:
            text_lines.append("1) Use /link_wallet to connect your BNB (BSC) address.")
        else:
            text_lines.append(f"1) BNB wallet linked: {user.bnb_address}")

        if balance == Decimal("0"):
            text_lines.append(
                "2) Once your existing investment is recorded, you will see your SLH balance via /balance."
            )
        else:
            text_lines.append(f"2) Current SLH balance: {balance:.4f} (see /balance).")

        text_lines.append("3) Use /wallet to view full wallet details and ecosystem links.")
        text_lines.append("4) Use /whoami to see your ID, username and wallet status.")
        text_lines.append("5) Use /summary for a full investor dashboard.")
        text_lines.append("6) Use /history to review your latest transactions.")
        text_lines.append("")
        text_lines.append("You can also open /menu for a button-based experience.")

        await update.message.reply_text("\n".join(text_lines))

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "SLH Wallet Bot – Help\n\n"
            "/start       – Intro and onboarding\n"
            "/menu        – Main menu with buttons\n"
            "/summary     – Full investor dashboard (wallet + balance + profile)\n"
            "/wallet      – Wallet details and ecosystem links\n"
            "/link_wallet – Link your personal BNB (BSC) address\n"
            "/balance     – View your SLH off-chain balance (+ On-Chain if available)\n"
            "/history     – Last transactions in the internal ledger\n"
            "/transfer    – Internal off-chain transfer to another user\n"
            "/whoami      – See your Telegram ID, username and wallet status\n"
            "/docs        – Open the official SLH investor docs\n\n"
            "Admin only:\n"
            "/admin_menu  – Admin tools overview\n"
            "/admin_credit <telegram_id> <amount_slh>\n\n"
            "At this stage there is no redemption of principal – "
            "only usage of SLH units inside the ecosystem.\n"
            "BNB and gas remain in your own wallet via external providers."
        )
        await update.message.reply_text(text)

    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        תפריט הכפתורים הראשי למשקיע.
        """
        await update.message.reply_text(
            "SLH Investor Menu – choose an action:",
            reply_markup=self._main_menu_keyboard(),
        )

    async def cmd_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = self._ensure_user(update)
        addr = settings.COMMUNITY_WALLET_ADDRESS or "<community wallet not set>"
        token_addr = settings.SLH_TOKEN_ADDRESS or "<SLH token not set>"

        user_addr = (
            user.bnb_address
            or "You have not linked a BNB address yet (see /link_wallet)."
        )

        lines = []
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
        lines.append(f"Each SLH nominally represents {self._slh_price_nis():.0f} ILS.")

        if settings.BSC_SCAN_BASE and addr and not addr.startswith("<"):
            lines.append("")
            lines.append("View community wallet on BscScan:")
            lines.append(f"{settings.BSC_SCAN_BASE.rstrip('/')}/address/{addr}")

        if settings.BSC_SCAN_BASE and token_addr and not token_addr.startswith("<"):
            lines.append("")
            lines.append("View SLH token on BscScan:")
            lines.append(f"{settings.BSC_SCAN_BASE.rstrip('/')}/token/{token_addr}")

        if settings.BUY_BNB_URL:
            lines.append("")
            lines.append("External BNB purchase link (optional):")
            lines.append(settings.BUY_BNB_URL)

        if settings.STAKING_INFO_URL:
            lines.append("")
            lines.append("BNB staking info:")
            lines.append(settings.STAKING_INFO_URL)

        await update.message.reply_text("\n".join(lines))

    async def cmd_link_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        שני מצבים:
        1) /link_wallet              -> שואל אותך לשלוח כתובת בהודעה הבאה
        2) /link_wallet 0xABC...     -> שומר מיד את הכתובת מהפקודה
        """
        tg_user = update.effective_user
        self._ensure_user(update)

        # אם נשלחה כתובת בתוך הפקודה עצמה
        if context.args:
            addr = context.args[0].strip()
            if not addr.startswith("0x") or len(addr) < 20:
                await update.message.reply_text(
                    "Address seems invalid. Usage: /link_wallet 0xyouraddress or send the address after /link_wallet."
                )
                return

            db = self._db()
            try:
                user = crud.get_or_create_user(
                    db, telegram_id=tg_user.id, username=tg_user.username
                )
                crud.set_bnb_address(db, user, addr)
                await update.message.reply_text(
                    f"Your BNB address was saved:\n{addr}"
                )
            finally:
                db.close()

            context.user_data["state"] = None
            return

        # מצב רגיל – מבקש כתובת בהודעה הבאה
        context.user_data["state"] = STATE_AWAITING_BNB_ADDRESS
        await update.message.reply_text(
            "Please send your BNB address (BSC network, usually starts with 0x...)."
        )

    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        db = self._db()
        try:
            tg_user = update.effective_user
            user = crud.get_or_create_user(
                db, telegram_id=tg_user.id, username=tg_user.username
            )
            balance = user.balance_slh or Decimal("0")
            price = self._slh_price_nis()
            value_nis = balance * price

            lines = []
            lines.append("SLH Off-Chain Balance")
            lines.append("")
            lines.append(f"Current balance: {balance:.4f} SLH")
            lines.append(
                f"Nominal value: {value_nis:.2f} ILS (at {price:.0f} ILS per SLH)"
            )
            lines.append("")

            # ניסיון להראות גם מצב On-Chain אם יש כתובת
            onchain_bnb = None
            onchain_slh = None
            if user.bnb_address:
                try:
                    on = blockchain.get_onchain_balances(user.bnb_address)
                    onchain_bnb = on.get("bnb")
                    onchain_slh = on.get("slh")
                except Exception as e:
                    logger.warning("On-chain balance fetch failed: %s", e)

            if user.bnb_address and (onchain_bnb is not None or onchain_slh is not None):
                lines.append("On-Chain view (BNB Chain):")
                if onchain_bnb is not None:
                    lines.append(f"- BNB: {onchain_bnb:.6f} BNB")
                else:
                    lines.append("- BNB: unavailable (RPC or address error)")

                if onchain_slh is not None:
                    lines.append(f"- SLH: {onchain_slh:.6f} SLH")
                else:
                    lines.append("- SLH: unavailable (token or RPC error)")
                lines.append("")

            lines.append(
                "This reflects allocations recorded for you inside the system."
            )
            lines.append(
                "There is no redemption yet – only future usage inside the ecosystem."
            )

            await update.message.reply_text("\n".join(lines))
        finally:
            db.close()

    async def cmd_whoami(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        נותן חוויית "אני רשום במערכת".
        """
        db = self._db()
        try:
            tg_user = update.effective_user
            user = crud.get_or_create_user(
                db, telegram_id=tg_user.id, username=tg_user.username
            )
            balance = user.balance_slh or Decimal("0")

            lines = []
            lines.append("Your SLH Investor Profile")
            lines.append("")
            lines.append(f"Telegram ID: {tg_user.id}")
            lines.append(
                f"Username: @{tg_user.username}" if tg_user.username else "Username: N/A"
            )
            lines.append(
                f"BNB address: {user.bnb_address or 'Not linked yet (use /link_wallet)'}"
            )
            lines.append(f"SLH balance: {balance:.4f} SLH")
            lines.append("")
            lines.append(
                "Share your Telegram ID with the SLH team if needed for allocations."
            )

            await update.message.reply_text("\n".join(lines))
        finally:
            db.close()

    async def cmd_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        דשבורד משקיע במסך אחד.
        """
        db = self._db()
        try:
            tg_user = update.effective_user
            user = crud.get_or_create_user(
                db, telegram_id=tg_user.id, username=tg_user.username
            )
            balance = user.balance_slh or Decimal("0")
            price = self._slh_price_nis()
            value_nis = balance * price

            addr = settings.COMMUNITY_WALLET_ADDRESS or "<community wallet not set>"
            token_addr = settings.SLH_TOKEN_ADDRESS or "<SLH token not set>"
            user_addr = (
                user.bnb_address
                or "Not linked yet (use /link_wallet)."
            )

            # On-Chain
            onchain_bnb = None
            onchain_slh = None
            if user.bnb_address:
                try:
                    on = blockchain.get_onchain_balances(user.bnb_address)
                    onchain_bnb = on.get("bnb")
                    onchain_slh = on.get("slh")
                except Exception as e:
                    logger.warning("On-chain balance fetch failed: %s", e)

            lines = []
            lines.append("SLH Investor Dashboard")
            lines.append("")
            lines.append("Profile:")
            lines.append(f"- Telegram ID: {tg_user.id}")
            lines.append(
                f"- Username: @{tg_user.username}"
                if tg_user.username
                else "- Username: N/A"
            )
            lines.append("")
            lines.append("Wallets:")
            lines.append(f"- Your BNB (BSC): {user_addr}")
            lines.append(f"- Community wallet: {addr}")
            lines.append(f"- SLH token: {token_addr}")
            lines.append("")
            lines.append("Balance (Off-Chain System Ledger):")
            lines.append(f"- SLH: {balance:.4f} SLH")
            lines.append(f"- Nominal ILS value: {value_nis:.2f} ILS")
            lines.append("")

            if user.bnb_address and (onchain_bnb is not None or onchain_slh is not None):
                lines.append("On-Chain (BNB Chain) – based on your BNB address:")
                if onchain_bnb is not None:
                    lines.append(f"- BNB: {onchain_bnb:.6f} BNB")
                else:
                    lines.append("- BNB: unavailable (RPC or address error)")
                if onchain_slh is not None:
                    lines.append(f"- SLH: {onchain_slh:.6f} SLH")
                else:
                    lines.append("- SLH: unavailable (token or RPC error)")
                lines.append("")

            if settings.BSC_SCAN_BASE and addr and not addr.startswith("<"):
                lines.append("On BscScan:")
                lines.append(
                    f"- Community wallet: {settings.BSC_SCAN_BASE.rstrip('/')}/address/{addr}"
                )
            if settings.BSC_SCAN_BASE and token_addr and not token_addr.startswith("<"):
                lines.append(
                    f"- SLH token: {settings.BSC_SCAN_BASE.rstrip('/')}/token/{token_addr}"
                )

            if settings.DOCS_URL:
                lines.append("")
                lines.append(f"Investor Docs: {settings.DOCS_URL}")

            lines.append("")
            lines.append("Key commands: /menu, /wallet, /balance, /history, /transfer, /docs, /help")

            await update.message.reply_text("\n".join(lines))
        finally:
            db.close()

    async def cmd_docs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        קישור למסמכי ה-DOCS הרשמיים (README למשקיעים).
        """
        if not settings.DOCS_URL:
            await update.message.reply_text(
                "Investor docs URL is not configured yet. Please contact the SLH team."
            )
            return

        text_lines = []
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

    async def cmd_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        מציג עד 10 הטרנזקציות האחרונות שבהן המשתמש מעורב (Off-Chain).
        """
        db = self._db()
        try:
            tg_user = update.effective_user
            user = crud.get_or_create_user(
                db, telegram_id=tg_user.id, username=tg_user.username
            )

            user_ids = []
            if hasattr(user, "id") and user.id is not None:
                user_ids.append(user.id)
            if hasattr(user, "telegram_id") and user.telegram_id is not None:
                user_ids.append(user.telegram_id)

            if not user_ids:
                await update.message.reply_text("No transactions found for this profile.")
                return

            q = (
                db.query(models.Transaction)
                .filter(
                    or_(
                        models.Transaction.from_user_id.in_(user_ids),
                        models.Transaction.to_user_id.in_(user_ids),
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

            lines = []
            lines.append("Last transactions (internal ledger)")
            lines.append("Most recent first (max 10):")
            lines.append("")

            for tx in txs:
                from_id = getattr(tx, "from_user_id", None)
                to_id = getattr(tx, "to_user_id", None)
                tx_type = getattr(tx, "tx_type", "N/A")
                amount = (
                    getattr(tx, "amount_slh", None)
                    or getattr(tx, "delta_slh", None)
                    or getattr(tx, "amount", None)
                    or 0
                )
                created_at = getattr(tx, "created_at", None)

                direction = "OTHER"
                if any(uid == from_id for uid in user_ids):
                    direction = "OUT"
                if any(uid == to_id for uid in user_ids):
                    direction = "IN"

                if created_at is not None:
                    try:
                        ts = created_at.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        ts = str(created_at)
                else:
                    ts = "N/A"

                lines.append(
                    f"[{ts}] {direction} – {amount:.4f} SLH (type={tx_type}, id={tx.id})"
                )

            await update.message.reply_text("\n".join(lines))

        except Exception as e:
            logger.exception("Error while fetching history: %s", e)
            await update.message.reply_text(
                "Could not load transaction history. Please contact the SLH team."
            )
        finally:
            db.close()

    async def cmd_transfer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self._ensure_user(update)
        context.user_data["state"] = STATE_AWAITING_TRANSFER_TARGET
        await update.message.reply_text(
            "Type the target username you want to transfer to (e.g. @username)."
        )

    async def cmd_admin_credit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        אדמין בלבד: טעינת SLH למשתמש לפי ID.
        /admin_credit <telegram_id> <amount_slh>
        """
        admin_id = settings.ADMIN_USER_ID
        if not admin_id or str(update.effective_user.id) != str(admin_id):
            await update.message.reply_text("This command is admin-only.")
            return

        parts = (update.message.text or "").split()
        if len(parts) != 3:
            await update.message.reply_text(
                "Usage: /admin_credit <telegram_id> <amount_slh>"
            )
            return

        try:
            target_id = int(parts[1])
            amount = float(parts[2])
        except ValueError:
            await update.message.reply_text("Invalid parameters. Check ID and amount.")
            return

        db = self._db()
        try:
            user = crud.get_or_create_user(db, telegram_id=target_id, username=None)
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

    async def cmd_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        תפריט אדמין – זמין רק למזהה המוגדר ב-ADMIN_USER_ID.
        """
        admin_id = settings.ADMIN_USER_ID
        if not admin_id or str(update.effective_user.id) != str(admin_id):
            await update.message.reply_text("This command is admin-only.")
            return

        await update.message.reply_text(
            "SLH Admin Menu – tools for managing investor balances:",
            reply_markup=self._admin_menu_keyboard(),
        )

    # ===== Callback handlers =====

    async def cb_wallet_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    async def cb_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        כפתורי MENU_* עבור המשקיע.
        """
        query = update.callback_query
        await query.answer()
        data = query.data

        # נשתמש ב-fake Update כדי לקרוא לפקודות קיימות
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

    async def cb_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        כפתורי ADMIN_* עבור אדמין.
        """
        query = update.callback_query
        await query.answer()
        data = query.data

        admin_id = settings.ADMIN_USER_ID
        if not admin_id or str(query.from_user.id) != str(admin_id):
            await query.edit_message_text("Admin only.")
            return

        if data == "ADMIN_HELP_CREDIT":
            text = (
                "Admin credit tool:\n\n"
                "Use:\n"
                "/admin_credit <telegram_id> <amount_slh>\n\n"
                "Example:\n"
                "/admin_credit 224223270 199999.877\n\n"
                "This will create an internal ledger transaction and update the user's off-chain SLH balance."
            )
            await query.edit_message_text(text)

        elif data == "ADMIN_HELP_HISTORY":
            text = (
                "Ledger overview:\n\n"
                "For now, use /history from a user account to see their last 10 transactions.\n"
                "In future iterations we can add global admin views and filters."
            )
            await query.edit_message_text(text)

    # ===== Text handler =====
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        state = context.user_data.get("state")
        text = (update.message.text or "").strip()

        db = self._db()
        try:
            tg_user = update.effective_user
            user = crud.get_or_create_user(
                db, telegram_id=tg_user.id, username=tg_user.username
            )

            # BNB address (flow שבו שלחת כתובת אחרי /link_wallet בלי פרמטרים)
            if state == STATE_AWAITING_BNB_ADDRESS:
                context.user_data["state"] = None

                if not text.startswith("0x") or len(text) < 20:
                    await update.message.reply_text(
                        "Address seems invalid. Try again with /link_wallet."
                    )
                    return

                crud.set_bnb_address(db, user, text)
                await update.message.reply_text(
                    f"Your BNB address was saved:\n{text}"
                )
                return

            # Transfer target
            if state == STATE_AWAITING_TRANSFER_TARGET:
                if not text.startswith("@"):
                    await update.message.reply_text(
                        "Send a username starting with @username"
                    )
                    return

                context.user_data["transfer_target_username"] = text[1:]
                context.user_data["state"] = STATE_AWAITING_TRANSFER_AMOUNT
                await update.message.reply_text(
                    f"Great. Now type the SLH amount you want to transfer to {text}."
                )
                return

            # Transfer amount
            if state == STATE_AWAITING_TRANSFER_AMOUNT:
                context.user_data["state"] = None

                try:
                    amount = float(text.replace(",", ""))
                except ValueError:
                    await update.message.reply_text(
                        "Could not read amount. Try again with /transfer."
                    )
                    return

                if amount <= 0:
                    await update.message.reply_text(
                        "Amount must be greater than zero."
                    )
                    return

                target_username = context.user_data.get("transfer_target_username")
                if not target_username:
                    await update.message.reply_text(
                        "Target not found. Try again with /transfer."
                    )
                    return

                receiver = (
                    db.query(models.User)
                    .filter(models.User.username == target_username)
                    .first()
                )
                if not receiver:
                    await update.message.reply_text(
                        "No user with that username in the system. "
                        "They must send /start once before receiving transfers."
                    )
                    return

                try:
                    tx = crud.internal_transfer(
                        db, sender=user, receiver=receiver, amount_slh=amount
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

            # Default
            await update.message.reply_text(
                "Command not recognized. Use /help to see available commands."
            )

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
