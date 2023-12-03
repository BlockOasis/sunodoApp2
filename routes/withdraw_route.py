import logging
from cartesi import Rollup, RollupData

from model.bank_db import bank_db
from helpers.setting import settings
from helpers.utils import str2hex, create_erc20_transfer_voucher
from helpers.inputs import WithdrawInput

# Configure logging
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# {'action': 'withdraw', 'amount': '500000000000000'}
def withdraw(json_router):
    @json_router.advance({'action': 'withdraw'})
    def withdraw(rollup: Rollup, data: RollupData) -> bool:
        LOGGER.info("Withdraw request")

        payload = WithdrawInput.parse_obj(data.json_payload())
        
        user = data.metadata.msg_sender
        amount = payload.amount

        # remove from wallet
        try: 
            bank_db.withdraw(user,amount)
        except Exception as e:
            msg = f"Could not Withdraw {amount} for user {user}. Error: {e}"
            LOGGER.error(msg)
            rollup.report(str2hex(msg))
            return False

        # generate voucher
        voucher = create_erc20_transfer_voucher(settings.TOKEN_ERC20_ADDRESS,user,amount)
        rollup.voucher(voucher)

        # send notice with current balance
        rollup.notice(str2hex(f"{{\"action\":\"withdraw\",\"address\":\"{user}\",\"balance\":\"{bank_db.balance(user)}\"}}"))

        LOGGER.info(f"Withdrawing {amount} for user {user}")

        return True
