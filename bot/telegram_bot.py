import asyncio
import logging
import os

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

from fastapi_app.services.employee import EmployeeService
from processors.excel_generator import TimeSheetGenerator

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, token: str, webhook_url: str | None = None):
        self.token = token
        self.webhook_url = webhook_url
        self.application = Application.builder().token(token).build()
        self.time_sheet_generator = TimeSheetGenerator()
        self.employee_service = EmployeeService()
        self.set_up_handlers()
        self._initialized = False  # Track initialization state

    def set_up_handlers(self):
        """Set up Telegram bot command handlers"""
        self.application.add_handler(CommandHandler('start', self.start_command))
        self.application.add_handler(CommandHandler('timesheet', self.timesheet_command))
        self.application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        telegram_id = str(user.id)
        name = f'{user.first_name} {user.last_name or ""}'.strip()

        try:
            employee = await self.employee_service.get_or_create_employee(
                telegram_id=telegram_id,
                name=name
            )

            # Check if employee has email
            if employee and employee.email is None:
                welcome_message = (
                    f'Welcome to Sheet Mate, {user.first_name}! 🎉\n\n'
                    f'We need your email to complete your registration.\n'
                    f'Please reply with your email address:'
                )
                # Store state to expect email next
                context.user_data['awaiting_email'] = True
                context.user_data['telegram_id'] = telegram_id  # ← THIS WAS MISSING
            else:
                welcome_message = (
                    f'Welcome back, {user.first_name}! 👋\n\n'
                    f'Use /timesheet to get your timesheet template'
                )

            await update.message.reply_text(welcome_message)

        except Exception as e:
            logger.error(f'Error in start command: {e}')
            await update.message.reply_text(
                'Welcome to Sheet Mate! Use /timesheet to get your timesheet template'
            )

    async def timesheet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /timesheet command - generate and send Excel file"""
        user = update.effective_user
        employee = await self.employee_service.get_employee_by_telegram_id(telegram_id=str(user.id))

        try:
            file_path = await self.time_sheet_generator.generate_timesheet(employee_name=employee.name)

            # Send file via telegram
            with open(file_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=os.path.basename(file_path),
                    caption='📊 Your timesheet template. Fill it and send it back!',
                )

            # Cleanup
            os.unlink(file_path)

        except Exception as e:
            logger.error(f'Error generating timesheet: {str(e)}')
            await update.message.reply_text('❌ Error generating timesheet. Please try again.')

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle when user sends filled Excel file"""
        # TODO: Implement document processing
        document = update.message.document
        file_name = document.file_name

        if file_name and file_name.endswith(('.xlsx', '.xls')):
            await update.message.reply_text(
                f'📄 Received your timesheet: {file_name}\n\n'
                f'Processing your timesheet...'
            )
            # TODO: Add your timesheet processing logic here
        else:
            await update.message.reply_text(
                '❌ Please send an Excel file (.xlsx or .xls)'
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages including email collection"""
        if context.user_data.get('awaiting_email'):
            email_text = update.message.text.strip()

            try:
                # This will now validate the email and handle errors
                await self.employee_service.update_employee_email(
                    telegram_id=context.user_data['telegram_id'],
                    email=email_text
                )

                await update.message.reply_text(
                    f'Perfect! ✅\n\n'
                    f'Email {email_text} has been saved.\n\n'
                    f'You\'re all set up! Use /timesheet to get your timesheet template.'
                )

                # Clear the state
                context.user_data['awaiting_email'] = False
                del context.user_data['telegram_id']

            except ValueError as e:
                await update.message.reply_text(
                    f'❌ {str(e)}\n\nPlease provide a valid email address:'
                )
            except Exception as e:
                logger.error(f'Error saving email: {e}')
                await update.message.reply_text(
                    'Sorry, there was an error saving your email. Please try /start again.'
                )
        else:
            # Handle other regular messages
            await update.message.reply_text(
                'I didn\'t understand that. Use /start to begin or /timesheet for your timesheet.'
            )

    async def setup_webhook(self):
        """Setup webhook with Telegram"""
        if not self.webhook_url:
            raise ValueError('Webhook URL not set')

        # Initialize the application first
        await self.application.initialize()
        await self.application.start()
        self._initialized = True

        # Remove any existing webhook first to avoid conflicts
        await self.application.bot.delete_webhook()
        await asyncio.sleep(1)  # Brief pause

        # Set new webhook
        await self.application.bot.set_webhook(
            url=self.webhook_url,
            drop_pending_updates=True  # Clear any pending updates
        )
        logger.info(f'Webhook URL set to {self.webhook_url}')

    async def remove_webhook(self):
        """Remove webhook from Telegram"""
        await self.application.bot.delete_webhook()
        logger.info('Webhook removed')

        # Shutdown the application
        if self._initialized:
            await self.application.stop()
            await self.application.shutdown()
            self._initialized = False

    async def process_update(self, update_data: dict):
        """Process incoming webhook update"""
        if not self._initialized:
            logger.error('Bot not initialized - cannot process update')
            return

        update = Update.de_json(update_data, self.application.bot)
        await self.application.process_update(update)
