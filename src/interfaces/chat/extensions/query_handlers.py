from src.interfaces.chat import purchase, sell, started, moderator, resume
from telebot import TeleBot


def register_callback_query_handlers(bot: TeleBot):
    """
    Register all callback query handlers
    """
    bot.register_callback_query_handler(
        callback=started.menu_handler,
        func=lambda data: "MENU_CUSTOMER" == data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_active=True
    )

    bot.register_callback_query_handler(
        callback=started.get_info_p2p,
        func=lambda data: "P2P_INFO" == data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False
    )

    bot.register_callback_query_handler(
        callback=started.menu_services_handler,
        func=lambda data: "MENU_SERVICES" == data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False
    )

    bot.register_callback_query_handler(
        callback=started.accept_term,
        func=lambda data: "ACCEPT_TERM" == data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False
    )

    bot.register_callback_query_handler(
        callback=resume.Resume.resume,
        func=lambda data: "MENU_RESUME" == data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_active=True
    )

    bot.register_callback_query_handler(
        callback=resume.Resume.add_address_lightning_address,
        func=lambda data: "ADD_LN_ADDRESS" == data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_active=True
    )

    bot.register_callback_query_handler(
        callback=resume.Resume.change_code_affiliate,
        func=lambda data: "CHANGE_AFFILIATE_CODE" == data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_active=True
    )

    bot.register_callback_query_handler(
        callback=resume.Resume.increase_level,
        func=lambda data: "INCREASE_LEVEL_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_active=True
    )

    bot.register_callback_query_handler(
        callback=purchase.Purchase.purchase_listing_handler,
        func=lambda data: "BUY_OPTION" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_active=True
    )

    bot.register_callback_query_handler(
        callback=sell.SELL.sell_listing_handler,
        func=lambda data: "SELL_OPTION" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_active=True
    )

    bot.register_callback_query_handler(
        callback=sell.SELL.sell_add_address_handler,
        func=lambda data: "SELL_SELECT_BTC_" \
            in data.data or \
                "SELL_SELECT_LUSDT_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_active=True
    )

    bot.register_callback_query_handler(
        callback=purchase.Purchase.purchase_custom_value_handler,
        func=lambda data: "BUY_VALUE_CUSTOM" == data.data,
        pass_bot=True,
        username_exists=True,
        is_active=True
    )

    bot.register_callback_query_handler(
        callback=sell.SELL.sell_custom_value_handler,
        func=lambda data: "SELL_VALUE_CUSTOM" == data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_active=True
    )

    bot.register_callback_query_handler(
        callback=purchase.Purchase.purchase_select_value_handler,
        func=lambda data: "BUY_VALUE_BTC" in data.data or \
            "BUY_VALUE_LN" in data.data or \
                "BUY_VALUE_LIQUID" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_active=True
    )

    bot.register_callback_query_handler(
        callback=purchase.Purchase.purchase_select_network_handler,
        func=lambda data: "BUY_VALUE_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_active=True
    )

    bot.register_callback_query_handler(
        callback=sell.SELL.sell_select_value_handler,
        func=lambda data: "SELL_VALUE_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_active=True
    )

    bot.register_callback_query_handler(
        callback=sell.SELL.sell_confirm_payment_invoice,
        func=lambda data: "CONFIRM_PAYMENT_INVOICE_" \
            in data.data \
                or "CONFIRM_PAYMENT_ADDRESS_LUSDT_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_active=True
    )

    bot.register_callback_query_handler(
        callback=moderator.Purchase.purchase_listing_handler,
        func=lambda data: "LIST_BUY_TX_PENDING" == data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False
    )

    bot.register_callback_query_handler(
        callback=moderator.Purchase.purchase_tx_pending_settled_or_cancel_cancel,
        func=lambda data: ("BUY_TX_CANCEL_CANCEL_" in data.data)
            or ("BUY_TX_FINALIZE_CANCEL_" in data.data),
        pass_bot=True,
        username_exists=True,
        is_blocked=False
    )

    bot.register_callback_query_handler(
        callback=moderator.Purchase.purchase_tx_pending_finalize_confirm,
        func=lambda data: "BUY_TX_FINALIZE_CONFIRM_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False
    )

    bot.register_callback_query_handler(
        callback=moderator.Purchase.purchase_tx_pending_cancel_confirm,
        func=lambda data: "BUY_TX_CANCEL_CONFIRM_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False
    )

    bot.register_callback_query_handler(
        callback=moderator.Purchase.purchase_tx_pending_settled_options,
        func=lambda data: "BUY_TX_FINALIZE_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False
    )

    bot.register_callback_query_handler(
        callback=moderator.Purchase.purchase_tx_pending_cancel_options,
        func=lambda data: "BUY_TX_CANCEL_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False
    )

    bot.register_callback_query_handler(
        callback=moderator.Purchase.purchase_get_tx_pending,
        func=lambda data: "BUY_TX_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False
    )

    bot.register_callback_query_handler(
        callback=moderator.Sell.sell_listing_handler,
        func=lambda data: "LIST_SELL_TX_PENDING" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False
    )

    bot.register_callback_query_handler(
        callback=moderator.Sell.sell_tx_pending_finalize_confirm,
        func=lambda data: "SELL_TX_FINALIZE_CONFIRM_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_operation=True
    )

    bot.register_callback_query_handler(
        callback=moderator.Sell.sell_tx_pending_cancel_confirm,
        func=lambda data: "SELL_TX_CANCEL_CONFIRM_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_operation=True
    )

    bot.register_callback_query_handler(
        callback=moderator.Sell.sell_tx_pending_settled_or_cancel_cancel,
        func=lambda data: ("SELL_TX_CANCEL_CANCEL_" in data.data)
            or ("SELL_TX_FINALIZE_CANCEL_" in data.data),
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_operation=True
    )

    bot.register_callback_query_handler(
        callback=moderator.Sell.sell_tx_pending_settled_options,
        func=lambda data: "SELL_TX_FINALIZE_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_operation=True
    )

    bot.register_callback_query_handler(
        callback=moderator.Sell.sell_tx_pending_cancel_options,
        func=lambda data: "SELL_TX_CANCEL_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_operation=True
    )

    bot.register_callback_query_handler(
        callback=moderator.Sell.sell_get_tx_pending,
        func=lambda data: "SELL_TX_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_operation=True
    )

    bot.register_callback_query_handler(
        callback=moderator.Moderator.general_statics_handler,
        func=lambda data: "GENERAL_STATICS" == data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_admin=True
    )

    bot.register_callback_query_handler(
        callback=moderator.Moderator.toggle_service_status_handler,
        func=lambda data: "ENABLE_OR_DISABLE_SERVICE" == data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_admin=True
    )

    bot.register_callback_query_handler(
        callback=moderator.Bank.listing_bank_accounts,
        func=lambda data: "CHANGE_BANK" == data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False
    )

    bot.register_callback_query_handler(
        callback=moderator.Bank.active_or_disable_account_bank,
        func=lambda data: "BANK_ACCOUNT_DISABLE_" in data.data or \
            "BANK_ACCOUNT_ACTIVATE_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False
    )

    bot.register_callback_query_handler(
        callback=moderator.Bank.get_account_bank,
        func=lambda data: "BANK_ACCOUNT_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False
    )

    bot.register_callback_query_handler(
        callback=moderator.User.block_or_unlock_user,
        func=lambda data: "BLOCK_" in data.data or \
            "UNLOCK_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_admin=True
    )

    bot.register_callback_query_handler(
        callback=moderator.User.approve_or_reject_document_user,
        func=lambda data: "APPROVE_ACCOUNT_" in data.data or \
            "REJECT_ACCOUNT_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_admin=True
    )

    bot.register_callback_query_handler(
        callback=moderator.User.get_list_users_pending_approval,
        func=lambda data: "LIST_USERS_PENDING_APPROVAL" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_admin=True
    )

    bot.register_callback_query_handler(
        callback=moderator.User.get_user_info,
        func=lambda data: "USER_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_admin=True
    )

    bot.register_callback_query_handler(
        callback=moderator.User.active_or_disable_operator,
        func=lambda data: "OPERATOR_DISABLE_" in data.data \
            or "OPERATOR_ACTIVE_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_admin=True
    )

    bot.register_callback_query_handler(
        callback=moderator.User.active_or_disable_partner,
        func=lambda data: "PARTNER_DISABLE_" in data.data \
            or "PARTNER_ACTIVE_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_admin=True
    )

    bot.register_callback_query_handler(
        callback=moderator.Bank.confirm_or_cancel_add_account,
        func=lambda data: "CONFIRM_ADD_ACCOUNT_" in \
            data.data or "CANCEL_ADD_ACCOUNT_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False
    )

    bot.register_callback_query_handler(
        callback=moderator.Transaction.get_transaction_tx_receipt_of_payment,
        func=lambda data: "TX_RECEIPT_OF_PAYMENT_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_admin=True
    )

    bot.register_callback_query_handler(
        callback=moderator.NFSe.confirm_or_roolback_nfse_processed,
        func=lambda data: "C_OR_R_NFSE_PROCESSED" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_admin=True
    )

    bot.register_callback_query_handler(
        callback=moderator.NFSe.get_unprocessed_nfse,
        func=lambda data: "UNPROCESSED_NFSE" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_admin=True
    )

    bot.register_callback_query_handler(
        callback=moderator.NFSe.nfse_reply_import,
        func=lambda data: "PROCESSED_NFSE" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_admin=True
    )

    bot.register_callback_query_handler(
        callback=moderator.Notify.notify_menu,
        func=lambda data: "MENU_NOTIFICATION" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_admin=True
    )

    bot.register_callback_query_handler(
        callback=moderator.Notify.notify_price,
        func=lambda data: "NOTIFICATION_PRICE" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_admin=True
    )

    bot.register_callback_query_handler(
        callback=moderator.Notify.notify_stop_service,
        func=lambda data: "NOTIFICATION_UNAVAILABLE_SERVICE" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_admin=True
    )

    bot.register_callback_query_handler(
        callback=moderator.Notify.notify_custom,
        func=lambda data: "NOTIFICATION_CUSTOM" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_admin=True
    )

    bot.register_callback_query_handler(
        callback=moderator.Notify.notify_all_users,
        func=lambda data: "SEND_ALL_MESSAGE_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_admin=True
    )

    bot.register_callback_query_handler(
        callback=moderator.Moderator.add_info_message_confirm,
        func=lambda data: "ADD_MSG_INFO_" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_admin=True
    )

    bot.register_callback_query_handler(
        callback=moderator.Moderator.download_rewards_affiliates,
        func=lambda data: "DOWNLOAD_REWARDS_AFFILIATES" in data.data,
        pass_bot=True,
        username_exists=True,
        is_blocked=False,
        is_admin=True
    )
