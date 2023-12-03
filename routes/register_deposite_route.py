import logging

from helpers.utils import (
    str2hex,
    hex2bin,
    create_erc20_transfer_voucher,
    decode_erc20_deposit,
)
from cartesi import Rollup, RollupData

from model.bank_db import bank_db

from model.user_db import users_db

from helpers.setting import settings

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def register_deposit(dapp):
    def process_deposit_and_add_user(rollup: Rollup, data):
        LOGGER.info("Processing Deposit")
        binary = hex2bin(data.payload)

        erc20_deposit = decode_erc20_deposit(binary)

        token_address = erc20_deposit["token_address"]
        depositor = erc20_deposit["depositor"]
        amount = erc20_deposit["amount"]

        if token_address.lower() != settings.TOKEN_ERC20_ADDRESS.lower():
            voucher = create_erc20_transfer_voucher(token_address, depositor, amount)
            LOGGER.info(f"Token not accepted, sending it back, voucher {voucher}")
            rollup.voucher(voucher)
            return True

        if not users_db.get_user(depositor):
            LOGGER.info(f"Creating new user for address: {depositor}")
            users_db.create_user(depositor)

        try:
            LOGGER.info("Handling wallet deposit")
            bank_db.deposit(depositor, amount)
        except Exception as e:
            msg = f"Could not deposit {amount} for user {depositor}. Error: {e}"
            LOGGER.error(msg)
            rollup.report(str2hex(msg))
            return False

        LOGGER.info(
            f'Sending notice for deposited amount: {{"action":"deposit","address":"{depositor}","balance":"{bank_db.balance(depositor)}"}}'
        )
        rollup.notice(
            str2hex(
                f'{{"action":"deposit","address":"{depositor}","balance":"{bank_db.balance(depositor)}"}}'
            )
        )

        return True

    @dapp.advance()
    def default_handler(rollup: Rollup, data: RollupData) -> bool:
        LOGGER.info("Running Default Handler")

        if data.metadata.msg_sender.lower() == settings.PORTAL_ERC20_ADDRESS.lower():
            LOGGER.info(f"Processing Erc20 deposit: {data}")
            return process_deposit_and_add_user(rollup, data)

        msg = "Nothing to do here"
        LOGGER.warning(msg)
        rollup.report(str2hex(msg))
        return False
