import logging
import os

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

from fastapi_app.services.employee import EmployeeService
from processors.excel_generator import TimeSheetGenerator

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.application = Application.builder().token(token).build()
        self.time_sheet_generator = TimeSheetGenerator()
        self.employees_service = EmployeeService()
        self.set_up_handlers()

    def set_up_handlers(self):
        """Set up Telegram bot command handlers"""
        self.application.add_handler(CommandHandler('start', self.start_command))
        self.application.add_handler(CommandHandler('timesheet', self.timesheet_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        telegram_id = str(user.id)
        name = f'{user.first_name} {user.last_name or ""}'.strip()

        try:
            employee = await self.employees_service.get_or_create_employee(
                telegram_id=telegram_id,
                name=name
            )

            # Check if employee has email - FIXED LOGIC
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
        chat_id = update.effective_chat.id

        try:
            file_path = await self.time_sheet_generator.generate_timesheet(
                employee_name=f'User_{chat_id}',
            )

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
        # TODO!!!!
        pass

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages including email collection"""
        if context.user_data.get('awaiting_email'):
            email_text = update.message.text.strip()

            try:
                # This will now validate the email and handle errors
                await self.employees_service.update_employee_email(
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

    async def start_polling(self):
        """Start the bot polling"""
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
