from src.middlewares.features import featuresEnabled
from src.services.helpers import calculate_percentage
from src.services.redis import redis
from src.services.swap import swap
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from src.configs import (
    PURCHASE_FEERATE_PRICE,
    PURCHASE_MAX_VALUE,
    PURCHASE_MIN_VALUE,
    SELL_MIN_VALUE,
    SELL_MAX_VALUE,
    SUPPORT_CHANNEL
)
from datetime import datetime
from bitpreco import BitPreco
from telebot import TeleBot
from src import database

# Initialize BitPreco
bitpreco = BitPreco()

def home_handler(data: Message, bot: TeleBot):
    if "start" in data.text:
        ref = data.text.replace("/start ", "")
        if database.User\
            .select()\
            .where((database.User.affiliate_code == ref))\
                .exists():
            user = database.User\
                .select()\
                    .where((database.User.id == str(data.from_user.id))).get()
            if not user.affiliated_to and \
                    user.affiliate_code != ref:
                user.affiliated_to = ref
                user.save()

                message = "Digite qualquer coisa e envie para que o menu seja exibido:\n\n"
                message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
                return bot.send_message(data.from_user.id, message)
    else:
        services_status = redis.redis_get("services.status")
        if not services_status:
            services_status = {"disable": False}
            redis.redis_set("services.status", services_status)

        if not services_status.get("disable"):
            message = "<b>⚠️ Caro cliente, nosso bot está desabilitado no momento, voltaremos em breve.</b>\n\n"
        else:
            price = bitpreco.get_price()
            price["SELL"] += calculate_percentage(
                x=price["SELL"], 
                y=PURCHASE_FEERATE_PRICE
            )

            try:
                message_info = redis.redis_get("message.info.default")["message"]
            except:
                message_info = ""
            
            minimum_fee = swap.get_info()["fees"]["minimum_fee"]
            message = f"<b>Preço:</b> R$ {price['SELL']:,.2f} ({price['RATIO']:,.2f}% 24h)\n"
            message+= f"<b>Taxa Rede:</b> {minimum_fee} sat/vB\n\n"
            message+= "<b>Carteiras Indicadas:</b>\n"
            message+= "<b>⚡️ Lightning: Wallet of Satoshi</b>\n"
            message+= "<b>💧 Liquid: Green Wallet, Aqua Wallet</b>\n"
            message+= "<b>❌ Não usar: Muun, Phoenix, Breez, Blixt</b>\n\n"
            if message_info:
                message+= f"{message_info}\n\n"
        
        message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"

        keyboard = InlineKeyboardMarkup()
        if services_status.get("disable"):
            keyboard.add(InlineKeyboardButton("⛵ Menu", callback_data="MENU_CUSTOMER"))
        else:
            keyboard.add(InlineKeyboardButton("🛠️ Outros Serviços", callback_data="MENU_SERVICES"))

        if not services_status.get("disable"):
            with open("src/assets/service-disabled.jpg", "rb") as f:
                bot.send_photo(
                    data.from_user.id,
                    f, 
                    caption=message,
                    reply_markup=keyboard
                )    
        else:
            with open("src/assets/home.jpg", "rb") as f:
                bot.send_photo(
                    data.from_user.id,
                    f, 
                    caption=message,
                    reply_markup=keyboard
                )

@featuresEnabled("FEATURE_MENU")
def menu_handler(data: Message, bot: TeleBot):
    """
    Handles the customer listing message.
    Displays the available service options for the customer to choose from.
    """
    if not isinstance(data, Message):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("⚡️ Comprar Bitcoin", callback_data="BUY_OPTION"))
    keyboard.add(InlineKeyboardButton("💸 Vender Bitcoin", callback_data="SELL_OPTION"))
    keyboard.add(InlineKeyboardButton("📃 Minha Conta", callback_data="MENU_RESUME"))
    keyboard.add(InlineKeyboardButton("🛠️ Outros Serviços", callback_data="MENU_SERVICES"))
    keyboard.add(InlineKeyboardButton("🤕 Contate o Suporte", url=f"https://t.me/{SUPPORT_CHANNEL}"))

    message = "<b>Limites (Min/Máx)</b>\n"
    message+= f"<b>Compra:</b> R$ {PURCHASE_MIN_VALUE:,.2f} / R$ {PURCHASE_MAX_VALUE:,.2f}\n"
    message+= f"<b>Venda:</b> R$ {SELL_MIN_VALUE:,.2f} / R$ {SELL_MAX_VALUE:,.2f}\n\n"
    message+= "<b>Para prosseguir, escolha uma das opções abaixo:</b>\n\n" 
    message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
    with open("src/assets/menu.jpg", "rb") as f:
        bot.send_photo(
            data.from_user.id,
            f, 
            caption=message,
            reply_markup=keyboard
        )

def term_info(data: Message, bot: TeleBot):
    if not isinstance(data, Message):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass
    
    message = (
        "<b>Termos e Condições</b>\n\n"
        "Ao aceitar os termos e condições, você concorda com as seguintes disposições:\n\n"
        "1 - Todo depósito em BRL deve ser de origem própria; depósitos suspeitos serão estornados, resultando no bloqueio da conta. Reembolsos solicitados após o término do acordo podem acarretar medidas legais, para mitigar o uso malicioso do serviço uma verificação básica de usuário é nescessário.\n\n"
        "2 - Depósitos em BRL via nossa Chave PIX serão convertidos em Stablecoin lastreada em BRL para salvaguardar nosso serviço contra atividades maliciosas. Má fé pode resultar em medidas legais pela empresa processadora de pagamentos.\n\n"
        "3 - Você reconhece que o processador de pagamento pode reportar seus depósitos em BRL, resultando na aquisição de uma Stablecoin token na proporção de 1:1.\n\n"
        "4 - Toda ordem de compra exibe claramente as informações sobre o valor a ser recebido e pago. Ao efetuar o pagamento, você aceita as condições da ordem sem questionamentos posteriores.\n\n"
        "5 - Você concorda que erros nos endereços de envio de fundos, como Bitcoin, Líquid e Lightning, não são de responsabilidade do serviço."
    )
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Aceitar Termos", callback_data="ACCEPT_TERM"))
    bot.send_message(data.from_user.id, message, reply_markup=keyboard)

def accept_term(data: Message, bot: TeleBot):
    try:
        bot.delete_message(data.from_user.id, data.message.message_id)
    except:
        pass
    
    user = database.User.get(id=str(data.from_user.id))
    user.accepted_term = True
    user.accepted_term_date = datetime.now()
    user.save()
    
    message = "<b>Os termos e condições foram aceitos com sucesso.</b>"
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("⛵ Menu", callback_data="MENU_CUSTOMER"))
    return bot.send_message(data.from_user.id, message, reply_markup=keyboard)

def menu_services_handler(data: Message, bot: TeleBot):
    if not isinstance(data, Message):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

    message = "<b>Abaixo, você encontrará outros serviços adicionais:</b>"
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Nossa plataforma (WEB)", url="https://app.stackfy.xyz/login"))
    keyboard.add(InlineKeyboardButton("Swap de lightning para On-chain", url="https://t.me/StackBridgeBot"))
    keyboard.add(InlineKeyboardButton("P2P, compras com boletos e dépositos", callback_data="P2P_INFO"))
    with open("src/assets/other-services.jpg", "rb") as f:
        return bot.send_photo(
            data.from_user.id,
            f, 
            caption=message, 
            reply_markup=keyboard
        )

def get_info_p2p(data: Message, bot: TeleBot):
    try:
        bot.delete_message(data.from_user.id, data.message.message_id)
    except:
        pass

    message = (
        "<b>Olá, segue algumas condições de negociação de nosso serviço P2P:</b>\n\n"
        "<b>💵 VALOR MÍNIMO</b>\n\n"
        "<b>- BRL:</b> R$ 2.500,00\n"
        "Obs: valores menores que esses não serão considerados.\n\n"
        "<b>💳 MEIOS DE PAGAMENTOS</b>\n"
        "- Boleto\n"
        "- TED\n"
        "- PIX\n\n"
        "💰 TAXAS\n\n"
        "<b>Taxa serviço:</b> 10%\n"
        "<b>Taxa de rede:</b> Variável\n\n"
        "FAQ: Como funciona o método P2P?\n\n"
        "De uma forma mais pessoal possível, P2P é uma relação comercial de uma pessoa com outra. Você informa quanto deseja comprar e o P2P lhe informa quanto lhe envia de acordo com valor e cotação do momento."
    )
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Entrar em contato", url="https://t.me/stackfyp2p"))
    return bot.send_message(data.from_user.id, message, reply_markup=keyboard)