from src.interfaces.chat import (
    purchase,
    sell,
    resume,
    started,
    moderator
)
from telebot import TeleBot

def register_message_handlers(bot: TeleBot):
    """
    Register all message handlers.
    """

    bot.register_message_handler(
        callback=started.term_info,
        content_types=["text"],
        pass_bot=True,
        username_exists=True,
        accepted_term=False,
        is_operation=False
    )

    bot.register_message_handler(
        callback=moderator.User.get_user_info,
        commands=["user"],
        content_types=["text"],
        pass_bot=True,
        username_exists=True,
        is_admin=True
    )

    bot.register_message_handler(
        callback=moderator.Transaction.get_transaction_tx,
        commands=["tx"],
        content_types=["text"],
        pass_bot=True,
        username_exists=True,
        is_admin=True
    )

    bot.register_message_handler(
        callback=moderator.NFSe.nfse_menu,
        commands=["nfse"],
        content_types=["text"],
        pass_bot=True,
        is_admin=True,
        is_blocked=False
    )

    bot.register_message_handler(
        callback=moderator.Bank.add_account,
        commands=["addbank"],
        content_types=["text"],
        pass_bot=True,
        username_exists=True,
        is_admin=True
    )

    bot.register_message_handler(
        callback=moderator.Moderator.add_info_message,
        commands=["addinfo"],
        content_types=["text"],
        pass_bot=True,
        username_exists=True,
        is_admin=True
    )

    bot.register_message_handler(
        callback=moderator.Notify.notify_custom_add,
        func=lambda data: (data.reply_to_message) and \
            "Envie a sua mensagem personalizada abaixo" in str(data.reply_to_message.text),        
        content_types=["text", "photo"],
        pass_bot=True,
        username_exists=True,
        is_admin=True
    )

    bot.register_message_handler(
        callback=moderator.Moderator.listing_handler,
        content_types=["text"],
        pass_bot=True,
        username_exists=True,
        is_operation=True
    )

    bot.register_message_handler(
        callback=purchase.Purchase.purchase_custom_add_value_handler,
        func=lambda data: (data.reply_to_message) \
            and "Qual valor você deseja comprar?" in str(data.reply_to_message.text),
        content_types=["text"],
        pass_bot=True,
        is_admin=False,
        is_user=True,
        username_exists=True,
        is_active=True,
        is_blocked=False
    )

    bot.register_message_handler(
        callback=sell.SELL.sell_custom_add_value_handler,
        func=lambda data: (data.reply_to_message) and \
            "Qual valor você deseja vender" in str(data.reply_to_message.text),
        content_types=["text"],
        pass_bot=True,
        is_admin=False,
        is_user=True,
        username_exists=True,
        is_active=True,
        is_blocked=False,
    )

    bot.register_message_handler(
        callback=purchase.Purchase.purchase_add_address_handler,
        func=lambda data: "lnbc" in str(data.caption).lower() or \
            "bc1" in str(data.caption).lower() or \
                "lq1" in str(data.caption).lower() or \
                    "vj" in str(data.caption).lower(),
        content_types=["photo"],
        pass_bot=True,
        username_exists=True,
        is_admin=False,
        is_active=True
    )

    bot.register_message_handler(
        callback=resume.Resume.increase_level,
        func=lambda data: str(data.text).startswith("LV"),
        content_types=["text"],
        pass_bot=True,
        username_exists=True,
        is_active=True,
        is_blocked=False,
        is_admin=False
    )

    bot.register_message_handler(
        callback=purchase.Purchase.purchase_add_address_handler,
        func=lambda data: str(data.text).lower().startswith("lnbc") or \
            str(data.text).lower().startswith("bc1") or \
                str(data.text).lower().startswith("lq1") or \
                    str(data.text).lower().startswith("vj"),
        content_types=["text"],
        pass_bot=True,
        username_exists=True,
        is_admin=False,
        is_active=True
    )

    bot.register_message_handler(
        callback=purchase.Purchase.purchase_add_receipt_handler,
        func=lambda data: True,
        content_types=["photo", "document"],
        pass_bot=True,
        username_exists=True,
        is_admin=False,
        is_blocked=False
    )

    bot.register_message_handler(
        callback=moderator.NFSe.load_processed_nfse,
        func=lambda data: ".csv" in data.document.file_name,
        content_types=["document"],
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_admin=True
    )

    bot.register_message_handler(
        callback=sell.SELL.sell_select_currency_handler,
        func=lambda data: ("BR.GOV.BCB.PIX" in data.text.upper()),
        content_types=["text"],
        pass_bot=True,
        username_exists=True,
        is_active=True,
        is_blocked=False,
        is_admin=False
    )

    bot.register_message_handler(
        callback=resume.Resume.change_code_affiliate,
        func=lambda data: (data.reply_to_message) and \
            ("codigo de indicação" in str(data.reply_to_message.text).lower()),
        content_types=["text"],
        pass_bot=True,
        username_exists=True,
        is_active=True,
        is_blocked=False,
        is_admin=False
    )

    bot.register_message_handler(
        callback=resume.Resume.add_address_lightning_address,
        func=lambda data: (data.reply_to_message) and \
            ("lightning address" in str(data.reply_to_message.text).lower()) and \
                ("@" in data.text),
        content_types=["text"],
        pass_bot=True,
        username_exists=True,
        is_active=True,
        is_blocked=False,
        is_admin=False
    )

    bot.register_message_handler(
        callback=started.home_handler,
        content_types=["text"],
        pass_bot=True,
        is_admin=False,
        username_exists=True,
        is_blocked=False
    )
