import logging
from cartesi import DApp, Rollup, RollupData, JSONRouter, URLRouter

from model.bank import Bank
from model.user_db import users_db
from model.claims_db import claims_db

from helpers.setting import settings
from helpers.utils import to_jsonhex

from routes.hello_route import register_hello_routes
from routes.register_deposite_route import register_deposit_routes

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

dapp = DApp()
json_router = JSONRouter()
dapp.add_router(json_router)
url_router = URLRouter()
dapp.add_router(url_router)

bank = Bank()


# def process_deposit_and_add_user(rollup: Rollup, data: RollupData) -> dict:
#     LOGGER.info("Proccesing Deposite")
#     binary = hex2bin(data.payload)

#     erc20_deposit = decode_erc20_deposit(binary)

#     token_address = erc20_deposit["token_address"]
#     depositor = erc20_deposit["depositor"]
#     amount = erc20_deposit["amount"]

#     if token_address.lower() != settings.TOKEN_ERC20_ADDRESS.lower():
#         voucher = create_erc20_transfer_voucher(token_address, depositor, amount)
#         LOGGER.info(f"Token not accepted, sending it back, voucher {voucher}")
#         rollup.voucher(voucher)
#         return True

#     # Check if user exists, if not, create a new user
#     if not users_db.get_user(depositor):
#         LOGGER.info(f"Creating new user for address: {depositor}")
#         users_db.create_user(depositor)

#     # add to wallet
#     try:
#         LOGGER.info("Handling wallet deposite")
#         bank.deposit(depositor, amount)
#     except Exception as e:
#         msg = f"Could not deposit {amount} for user {depositor}. Error: {e}"
#         LOGGER.error(msg)
#         rollup.report(str2hex(msg))
#         return False

#     # send notice with current balance
#     LOGGER.info(
#         f'Sending notice for deposited amount: {{"action":"deposit","address":"{depositor}","balance":"{bank.balance(depositor)}"}}'
#     )
#     rollup.notice(
#         str2hex(
#             f'{{"action":"deposit","address":"{depositor}","balance":"{bank.balance(depositor)}"}}'
#         )
#     )

#     return True


##################
# Testing Routes #
##################

register_hello_routes(url_router, json_router)

#######################################
# default register and deposite route #
#######################################

register_deposit_routes(dapp, users_db, bank, settings)

# @dapp.advance()
# def default_handler(rollup: Rollup, data: RollupData) -> bool:
#     LOGGER.info("Running Default Handler")

#     # handle deposits
#     if data.metadata.msg_sender.lower() == settings.PORTAL_ERC20_ADDRESS.lower():
#         LOGGER.info(f"Processing Erc20 deposit: {data}")
#         return process_deposit_and_add_user(rollup, data)

#     msg = "Nothing to do here"
#     LOGGER.warning(msg)
#     rollup.report(str2hex(msg))
#     return False


# @json_router.advance({"action": "setTokenAddress"})
# def set_token_address(rollup: Rollup, data: RollupData):
#     if STATE["is_token_address_set"]:
#         # Address has already been set, report and do nothing
#         rollup.report(to_jsonhex({"error": "TOKEN_ERC20_ADDRESS already set"}))
#         return False

#     # Extract the new address from the JSON payload
#     data = data.json_payload()
#     new_address = data["address"]

#     # Update the setting and the state flag
#     settings.TOKEN_ERC20_ADDRESS = new_address
#     STATE["is_token_address_set"] = True

#     # Report the new address setting
#     rollup.report(to_jsonhex({"TOKEN_ERC20_ADDRESS": new_address}))
#     return True


# @json_router.advance({})
# def handle_create_claim(rollup, data, payload, erc20_contract, depositor, value):
#     LOGGER.debug("Handling Create claim")
#     # payload = CreateContestInput.parse_obj(payload)
#     # contest = contests.create_contest(
#     #     input=payload,
#     #     timestamp=data.metadata.timestamp,
#     #     host_wallet=depositor,
#     #     initial_prize_pool=value,
#     # )
#     # LOGGER.debug("Created contest '%s'", repr(contest))
#     return True


#################
# Claim Handler #
#################


@json_router.advance({"handle": "claim"})
def handle_claim(rollup: Rollup, data: RollupData):
    LOGGER.debug("Handling Claim")
    data = data.json_payload()  # Parsing the data from JSON payload
    prep_CID = data.get("cidPrep")
    comp_CID = data.get("cidComp")
    collateral = data.get("coll")
    comp_proof = data.get("compProof")

    if collateral is None or collateral != settings.COLLATERAL_AMOUNT:
        message = f"Collateral amount should be equal {settings.COLLATERAL_AMOUNT}"
        rollup.report(
            to_jsonhex({"error": message})
        )  # Reporting the error in JSON hex format
        raise ValueError(message)

    claim_value = int(collateral)

    # Check if claim already exists
    if claims_db.get_claim(prep_CID):
        raise ValueError("HandleClaim: Claim already exists")

    # Check if user has enough funds
    user_wallet_address = data["msg_sender"]
    if bank.balance(user_wallet_address) < settings.COLLATERAL_AMOUNT:
        message = f"Insufficient funds for collateral in user's wallet.\nCurrent Balance: {bank.balance(user_wallet_address)}"
        rollup.report(to_jsonhex({"error": message}))
        return False

    # Lock the collateral amount by transferring it to a locked asset address
    try:
        bank.transfer(
            user_wallet_address,
            settings.LOCKED_ASSET_ADDRESS,
            settings.COLLATERAL_AMOUNT,
        )
    except Exception as e:
        message = f"Failed to lock collateral: {e}"
        rollup.report(to_jsonhex({"error": message}))
        return False

    # Create a new claim
    new_claim_id = claims_db.get_next_claim_id()
    new_claim = claims_db.create_claim(
        prep_CID=prep_CID,
        user_address=data["msg_sender"],
        timestamp_of_claim=data["timestamp"],  # Ensure this is correctly formatted
        comp_proof=comp_proof,
        comp_CID=comp_CID,
        value=claim_value,
    )

    # Update user's open claims
    user = users_db.get_user(
        data["msg_sender"]
    )  # Assuming get_user is defined elsewhere
    if user:
        user.open_claims[str(new_claim_id)] = None
        users_db.update_user(data["msg_sender"], open_claims=user.open_claims)

    rollup.notice(
        to_jsonhex({"key": new_claim_id, "claim": new_claim.dict()})
    )  # Reporting success

    return True


if __name__ == "__main__":
    dapp.run()
