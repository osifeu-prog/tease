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

from app.core.config import settings
from app.database import SessionLocal
from app import crud, models

logger = logging.getLogger(__name__)

STATE_AWAITING_BNB_ADDRESS = "AWAITING_BNB_ADDRESS"
STATE_AWAITING_TRANSFER_TARGET = "AWAITING_TRANSFER_TARGET"
STATE_AWAITING_TRANSFER_AMOUNT = "AWAITING_TRANSFER_AMOUNT"


class InvestorWalletBot:
    """
    SLH Investor Gateway – Telegram bot logic.

    Responsibilities:
    - Off-chain SLH balance tracking per Telegram user
    - Linking BNB wallet address (BSC)
    - Internal off-chain transfers between investors
    - Admin crediting of balances
    - Investor-friendly menus & flows
    """

    def __init__(self):
        self.application: Application | None = None
        self.bot: Bot | None = None

    # --- Infrastructure helpers -------------------------------------------------

    def _db(self):
        return SessionLocal()

    async def initialize(self):
        """
        Must be called once from app.main lifespan.
        Creates the telegram-application instance and registers all handlers.
        """
        if not settings.BOT_TOKEN:
            logger.warning("BOT_TOKEN is not set, skipping Telegram bot initialization")
            return

        self.application = Application.builder().token(settings.BOT_TOKEN).build()
        self.bot = self.application.bot

        # Core investor commands
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("wallet", self.cmd_wallet))
        self.application.add_handler(CommandHandler("link_wallet", self.cmd_link_wallet))
        self.application.add_handler(CommandHandler("balance", self.cmd_balance))
        self.application.add_handler(CommandHandler("transfer", self.cmd_transfer))
        self.application.add_handler(CommandHandler("send_slh", self.cmd_send_slh))
        self.application.add_handler(CommandHandler("whoami", self.cmd_whoami))
        self.application.add_handler(CommandHandler("history", self.cmd_history))

        # Admin-only commands
        self.application.add_handler(CommandHandler("admin_credit", self.cmd_admin_credit))
        self.application.add_handler(CommandHandler("admin_menu", self.cmd_admin_menu))

        # Callback for inline buttons (main menu, wallet menu, admin menu)
        self.application.add_handler(
            CallbackQueryHandler(self.cb_wallet_menu, pattern="^(WALLET_|MENU_|ADMIN_)")
        )

        # Generic text handler (for address / amounts / usernames)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text)
        )

        # Webhook mode
        if settings.WEBHOOK_URL:
            webhook_url = f"{settings.WEBHOOK_URL.rstrip('/')}/webhook/telegram"
            await self.bot.set_webhook(webhook_url)
            logger.info(f"Webhook set to: {webhook_url}")
        else:
            logger.info("No WEBHOOK_URL set - you can run in polling mode locally")

        logger.info("InvestorWalletBot initialized")

    # --- Small helpers ----------------------------------------------------------

    def _ensure_user(self, update: Update) -> models.User:
        """
        Make sure the telegram user exists in DB and return the ORM instance.
        """
        db = self._db()
        try:
            tg_user = update.effective_user
            return crud.get_or_create_user(
                db, telegram_id=tg_user.id, username=tg_user.username
            )
        finally:
            db.close()

    def _is_admin(self, telegram_id: int) -> bool:
        return bool(settings.ADMIN_USER_ID) and str(telegram_id) == str(settings.ADMIN_USER_ID)

    async def _send_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """
        Send a rich inline keyboard for investors.
        """
        tg_user = update.effective_user
        is_admin = self._is_admin(tg_user.id)

        buttons = [
            [
                InlineKeyboardButton("💼 Wallet", callback_data="MENU_WALLET"),
                InlineKeyboardButton("📊 Balance", callback_data="MENU_BALANCE"),
            ],
            [
                InlineKeyboardButton("📜 History", callback_data="MENU_HISTORY"),
                InlineKeyboardButton("🔁 Transfer", callback_data="MENU_TRANSFER"),
            ],
            [
                InlineKeyboardButton("🔗 Link wallet", callback_data="MENU_LINK_WALLET"),
            ],
        ]

        if is_admin:
            buttons.append(
                [InlineKeyboardButton("⚙️ Admin panel", callback_data="ADMIN_MENU")]
            )

        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    # --- Commands ---------------------------------------------------------------

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = self._ensure_user(update)
        min_invest = 100_000

        wallet_status = user.bnb_address or "Not linked yet (use /link_wallet)."

        text = (
            "Welcome to the SLH Investor Gateway.\n\n"
            f"This bot is intended for strategic investors (minimum {min_invest:,.0f} ILS).\n\n"
            "With this bot you can:\n"
            "- Link your personal BNB wallet (BSC)\n"
            "- View your off-chain SLH balance\n"
            "- Transfer SLH units to other investors (off-chain)\n"
            "- Access external links for BNB purchase and staking info\n\n"
            "Current wallet status:\n"
            f"- Linked BNB address: {wallet_status}\n\n"
            "Next steps:\n"
            "1) Use /link_wallet to connect your BNB (BSC) address.\n"
            "2) Once your existing investment is recorded, you will see your SLH balance via /balance.\n"
            "3) Use /wallet to view full wallet details and ecosystem links.\n"
            "4) Use /whoami to see your ID, username and wallet status.\n"
        )

        await self._send_main_menu(update, context, text)

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "SLH Wallet Bot – Help\n\n"
            "Investor commands:\n"
            "/start   – Intro screen & main menu\n"
            "/wallet  – Wallet details and ecosystem links\n"
            "/link_wallet – Link your personal BNB address\n"
            "/balance – View SLH off-chain balance\n"
            "/transfer – Step-by-step transfer wizard\n"
            "/send_slh @user amount – Direct transfer in one command\n"
            "/history – View your latest internal SLH transactions\n"
            "/whoami – Show your investor profile\n\n"
            "Admin commands:\n"
            "/admin_credit <telegram_id> <amount_slh>\n"
            "/admin_menu – Quick overview of admin tools\n\n"
            "At this stage there is no redemption of principal – only usage of SLH units "
            "inside the ecosystem. BNB and gas remain in your own wallet via external providers."
        )
        await update.message.reply_text(text)

    async def cmd_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = self._ensure_user(update)
        addr = settings.COMMUNITY_WALLET_ADDRESS or "<community wallet not set>"
        token_addr = settings.SLH_TOKEN_ADDRESS or "<SLH token not set>"

        user_addr = user.bnb_address or "You have not linked a BNB address yet (see /link_wallet)."

        text_lines = [
            "SLH Wallet Overview",
            "",
            "Your BNB address (BSC):",
            f"{user_addr}",
            "",
            "Community wallet address (for deposits / tracking):",
            addr,
            "",
            "SLH token address:",
            token_addr,
            "",
            f"Each SLH nominally represents {settings.SLH_PRICE_NIS:.0f} ILS.",
            "",
        ]

        if settings.BSC_SCAN_BASE and addr and not addr.startswith("<"):
            text_lines.extend(
                [
                    "View community wallet on BscScan:",
                    f"{settings.BSC_SCAN_BASE.rstrip('/')}/address/{addr}",
                    "",
                ]
            )
        if settings.BSC_SCAN_BASE and token_addr and not token_addr.startswith("<"):
            text_lines.extend(
                [
                    "View SLH token on BscScan:",
                    f"{settings.BSC_SCAN_BASE.rstrip('/')}/token/{token_addr}",
                    "",
                ]
            )
        if settings.BUY_BNB_URL:
            text_lines.extend(
                [
                    "External BNB purchase link (optional):",
                    settings.BUY_BNB_URL,
                    "",
                ]
            )
        if settings.STAKING_INFO_URL:
            text_lines.extend(
                [
                    "BNB staking info:",
                    settings.STAKING_INFO_URL,
                    "",
                ]
            )
        if getattr(settings, "DOCS_URL", None):
            text_lines.extend(
                [
                    "SLH Investor Deck / Docs:",
                    settings.DOCS_URL,
                ]
            )

        await update.message.reply_text("\n".join(text_lines))

    async def cmd_link_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Link a BNB (BSC) address to the current Telegram user.

        Supports both:
        - /link_wallet 0x123...
        - /link_wallet  (then send address as next message)
        """
        self._ensure_user(update)

        # Case 1: address given inline as argument
        if context.args:
            candidate = context.args[0].strip()
            if candidate.startswith("0x") and len(candidate) >= 20:
                db = self._db()
                try:
                    tg_user = update.effective_user
                    user = crud.get_or_create_user(
                        db, telegram_id=tg_user.id, username=tg_user.username
                    )
                    crud.set_bnb_address(db, user, candidate)
                    await update.message.reply_text(
                        f"Your BNB address was saved:\n{candidate}"
                    )
                    return
                finally:
                    db.close()
            else:
                await update.message.reply_text(
                    "The address after /link_wallet does not look valid. "
                    "You can instead send /link_wallet and then paste your address."
                )
                return

        # Case 2: ask for the address in the next message
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
            text = (
                "SLH Off-Chain Balance\n\n"
                f"Current balance: {balance:.4f} SLH\n\n"
                "This reflects allocations recorded for you inside the system.\n"
                "There is no redemption yet – only future usage inside the ecosystem."
            )
            await update.message.reply_text(text)
        finally:
            db.close()

    async def cmd_transfer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Step-by-step transfer wizard:
        1) Ask for @username
        2) Ask for amount
        """
        self._ensure_user(update)
        await update.message.reply_text(
            "Transfer wizard started.\n"
            "Step 1/2 – please type the target Telegram username (e.g. @InvestorFriend)."
        )
        context.user_data["state"] = STATE_AWAITING_TRANSFER_TARGET

    async def cmd_send_slh(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Direct SLH transfer in a single command.

        Usage:
        /send_slh @username 10.5
        or:
        /send_slh 10.5 @username
        """
        self._ensure_user(update)
        tg_user = update.effective_user

        if len(context.args) != 2:
            await update.message.reply_text(
                "Usage: /send_slh @username amount\n"
                "Example: /send_slh @InvestorFriend 10.5"
            )
            return

        arg1, arg2 = context.args[0].strip(), context.args[1].strip()
        username = None
        amount_str = None

        # Determine which argument is username and which is amount
        if arg1.startswith("@"):
            username = arg1[1:]
            amount_str = arg2
        elif arg2.startswith("@"):
            username = arg2[1:]
            amount_str = arg1
        else:
            await update.message.reply_text(
                "One of the arguments must be a @username.\n"
                "Usage: /send_slh @username amount"
            )
            return

        # Parse amount
        try:
            amount = float(amount_str.replace(",", ""))
        except ValueError:
            await update.message.reply_text(
                "Could not read amount. Example: /send_slh @InvestorFriend 10.5"
            )
            return

        if amount <= 0:
            await update.message.reply_text("Amount must be greater than zero.")
            return

        db = self._db()
        try:
            sender = crud.get_or_create_user(
                db, telegram_id=tg_user.id, username=tg_user.username
            )

            receiver = (
                db.query(models.User)
                .filter(models.User.username == username)
                .first()
            )
            if not receiver:
                await update.message.reply_text(
                    f"No user with username @{username} in the system.\n"
                    "They must send /start once in the bot before receiving transfers."
                )
                return

            try:
                tx = crud.internal_transfer(
                    db, sender=sender, receiver=receiver, amount_slh=amount
                )
            except ValueError:
                await update.message.reply_text(
                    "Insufficient balance for this transfer."
                )
                return

            await update.message.reply_text(
                "SLH transfer completed:\n"
                f"{amount:.4f} SLH -> @{receiver.username or receiver.telegram_id}\n"
                f"Transaction ID: {tx.id}"
            )
        finally:
            db.close()

    async def cmd_whoami(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        db = self._db()
        try:
            tg_user = update.effective_user
            user = crud.get_or_create_user(
                db, telegram_id=tg_user.id, username=tg_user.username
            )
            balance = user.balance_slh or Decimal("0")
            addr = user.bnb_address or "Not linked yet (use /link_wallet)"
            text = (
                "Your SLH Investor Profile\n\n"
                f"Telegram ID: {tg_user.id}\n"
                f"Username: @{tg_user.username or 'N/A'}\n"
                f"BNB address: {addr}\n"
                f"SLH balance: {balance:.4f} SLH\n\n"
                "Share your Telegram ID with the SLH team if needed for allocations."
            )
            await update.message.reply_text(text)
        finally:
            db.close()

    async def cmd_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Show recent off-chain SLH transactions for the current user.
        This implementation is defensive: if the Transaction model or expected
        fields are missing, it will fail gracefully and not crash the bot.
        """
        db = self._db()
        try:
            tg_user = update.effective_user
            user = crud.get_or_create_user(
                db, telegram_id=tg_user.id, username=tg_user.username
            )

            # Try to access Transaction model
            try:
                Transaction = models.Transaction
            except AttributeError:
                await update.message.reply_text(
                    "Transaction history is not yet configured for this deployment."
                )
                return

            # Try several common schema patterns
            query = db.query(Transaction)
            filtered = False

            if hasattr(Transaction, "user_id"):
                query = query.filter(Transaction.user_id == user.id)
                filtered = True
            elif hasattr(Transaction, "from_user_id") and hasattr(Transaction, "to_user_id"):
                from sqlalchemy import or_
                query = query.filter(
                    or_(
                        Transaction.from_user_id == user.id,
                        Transaction.to_user_id == user.id,
                    )
                )
                filtered = True

            if not filtered:
                await update.message.reply_text(
                    "History view is not available with the current transaction schema."
                )
                return

            txs = (
                query.order_by(getattr(Transaction, "created_at", Transaction.id).desc())
                .limit(10)
                .all()
            )

            if not txs:
                await update.message.reply_text("No transactions recorded yet.")
                return

            lines = ["Your recent SLH transactions:", ""]
            for tx in txs:
                # amount
                if hasattr(tx, "amount_slh"):
                    amount = getattr(tx, "amount_slh")
                elif hasattr(tx, "amount"):
                    amount = getattr(tx, "amount")
                else:
                    amount = None

                # type
                tx_type = getattr(tx, "tx_type", "transfer")

                # created_at
                created = getattr(tx, "created_at", None)
                created_str = created.strftime("%Y-%m-%d %H:%M") if created else "N/A"

                line = f"- [{created_str}] {tx_type}"
                if amount is not None:
                    line += f" · {amount:.4f} SLH"

                lines.append(line)

            await update.message.reply_text("\n".join(lines))
        except Exception:
            logger.exception("Failed to load transaction history")
            await update.message.reply_text(
                "Could not load transaction history at the moment."
            )
        finally:
            db.close()

    async def cmd_admin_credit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        admin_id = settings.ADMIN_USER_ID
        if not admin_id or str(update.effective_user.id) != str(admin_id):
            await update.message.reply_text("This command is admin-only.")
            return

        parts = (update.message.text or "").split()
        if len(parts) != 3:
            await update.message.reply_text("Usage: /admin_credit <telegram_id> <amount_slh>")
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
                f"Credited {amount:.4f} SLH to user {target_id}.\nTransaction ID: {tx.id}"
            )
        finally:
            db.close()

    async def cmd_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Simple overview of admin tools and flows.
        """
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("This command is admin-only.")
            return

        text = (
            "SLH Investor – Admin Panel\n\n"
            "Available admin tools:\n"
            "- /admin_credit <telegram_id> <amount_slh> – credit SLH balance to an investor\n"
            "- /history – review your own recent operations\n"
            "- /send_slh – test investor-to-investor transfers\n\n"
            "Operational flow suggestion:\n"
            "1) Investor pays and shares Telegram ID with the SLH team.\n"
            "2) You use /admin_credit to allocate the SLH units off-chain.\n"
            "3) Investor links BNB via /link_wallet and sees allocation via /balance.\n"
            "4) Investors can transfer units internally with /transfer or /send_slh.\n"
        )
        await update.message.reply_text(text)

    # --- Callback buttons -------------------------------------------------------

    async def cb_wallet_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data

        # Wrap the callback message in an Update so we can reuse the same command handlers
        fake_update = Update(update.update_id, message=query.message)

        if data in ("WALLET_BALANCE", "MENU_BALANCE"):
            await self.cmd_balance(fake_update, context)
        elif data in ("WALLET_DETAILS", "MENU_WALLET"):
            await self.cmd_wallet(fake_update, context)
        elif data == "MENU_HISTORY":
            await self.cmd_history(fake_update, context)
        elif data == "MENU_TRANSFER":
            await self.cmd_transfer(fake_update, context)
        elif data == "MENU_LINK_WALLET":
            await self.cmd_link_wallet(fake_update, context)
        elif data == "WALLET_BUY_BNB":
            if settings.BUY_BNB_URL:
                await query.edit_message_text(
                    f"Suggested BNB provider:\n{settings.BUY_BNB_URL}"
                )
            else:
                await query.edit_message_text(
                    "BUY_BNB_URL not set in environment variables."
                )
        elif data == "ADMIN_MENU":
            if self._is_admin(query.from_user.id):
                # Show a compact inline admin hint + point to /admin_menu
                await query.edit_message_text(
                    "Admin panel\n\n"
                    "Use /admin_menu inside the bot to see all admin tools.\n"
                    "Main actions:\n"
                    "- /admin_credit – allocate SLH to investors\n"
                    "- /history – review recent operations\n"
                    "- /send_slh – test transfers between investor accounts"
                )
            else:
                await query.edit_message_text("You are not an admin in this bot.")

    # --- Free-text handler (states) ---------------------------------------------

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        state = context.user_data.get("state")
        text = (update.message.text or "").strip()
        db = self._db()
        try:
            tg_user = update.effective_user
            user = crud.get_or_create_user(
                db, telegram_id=tg_user.id, username=tg_user.username
            )

            # 1) Awaiting BNB address
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

            # 2) Transfer wizard – target username
            elif state == STATE_AWAITING_TRANSFER_TARGET:
                if not text.startswith("@"):
                    await update.message.reply_text(
                        "Please send a username starting with @username"
                    )
                    return
                context.user_data["transfer_target_username"] = text[1:]
                context.user_data["state"] = STATE_AWAITING_TRANSFER_AMOUNT
                await update.message.reply_text(
                    f"Step 2/2 – now type the SLH amount you want to transfer to {text}."
                )
                return

            # 3) Transfer wizard – amount
            elif state == STATE_AWAITING_TRANSFER_AMOUNT:
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

            # Default – fallback help
            await update.message.reply_text(
                "Command not recognized. Use /help to see available commands."
            )

        finally:
            db.close()


# Singleton instance used by app.main
_bot_instance = InvestorWalletBot()


async def initialize_bot():
    await _bot_instance.initialize()


async def process_webhook(update_dict: dict):
    if not _bot_instance.application:
        logger.error("Application is not initialized")
        return
    update = Update.de_json(update_dict, _bot_instance.application.bot)
    await _bot_instance.application.process_update(update)
