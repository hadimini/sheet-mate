import logging
import os

from processors.excel_generator import TimeSheetGenerator
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.application = Application.builder().token(token).build()
        self.time_sheet_generator = TimeSheetGenerator()
        self.set_up_handlers()

    def set_up_handlers(self):
        """Set up Telegram bot command handlers"""
        self.application.add_handler(CommandHandler('start', self.start_command))
        self.application.add_handler(CommandHandler("timesheet", self.timesheet_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            'Welcome to Sheet Mate! Use /timesheet to get your timesheet template'
        )

    async def timesheet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /timesheet command - generate and send Excel file"""
        chat_id = update.effective_chat.id

        try:
            file_path = await self.time_sheet_generator.generate_timesheet(
                employee_name=f"User_{chat_id}",
            )

            # Send file via telegram
            with open(file_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=os.path.basename(file_path),
                    caption="📊 Your timesheet template. Fill it and send it back!",
                )

            # Cleanup
            os.unlink(file_path)

        except Exception as e:
            logger.error(f'Error generating timesheet: {str(e)}')
            await update.message.reply_text('❌ Error generating timesheet. Please try again.')

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle when user sends filled Excel file"""
        # TODO!!!!
        pass

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        await update.message.reply_text(
            "🤖 I'm Sheet Mate bot! Use /timesheet to get your timesheet template."
        )


    async def start_polling(self):
        """Start the bot polling"""
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
