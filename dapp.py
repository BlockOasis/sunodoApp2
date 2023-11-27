import json
import logging

from pydantic import BaseSettings

from cartesi import DApp, Rollup, RollupData, JSONRouter, URLRouter
from eth_abi import encode

from model.bank import Bank
from model.model import Status

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

dapp = DApp()
json_router = JSONRouter()
dapp.add_router(json_router)
url_router = URLRouter()
dapp.add_router(url_router)

bank = Bank()


# This dapp will read and write from this global state dict
STATE = {}

####################
# Helper Functions #
####################

def str2hex(str):
    """Encodes a string as a hex string"""
    return "0x" + str.encode("utf-8").hex()


def to_jsonhex(data):
    """Encode as a JSON hex"""
    return str2hex(json.dumps(data))

def hex2bin(hexstr: str):
    return bytes.fromhex(hexstr[2:])

def bin2hex(binary):
    return "0x" + binary.hex()


def decode_erc20_deposit(binary):
    # ret = binary[:1]
    token_address = binary[1:21]
    depositor = binary[21:41]
    amount = int.from_bytes(binary[41:73], "big")
    data = binary[73:]
    erc20_deposit = {
        "depositor":bin2hex(depositor),
        "token_address":bin2hex(token_address),
        "amount":amount,
        "data":data
    }
    LOGGER.info(erc20_deposit)
    return erc20_deposit

def create_erc20_transfer_voucher(token_address,receiver,amount):
    # Function to be called in voucher [token_address].transfer([address receiver],[uint256 amount])
    data = encode(['address', 'uint256'], [receiver,amount])
    voucher_payload = bin2hex(settings.ERC20_TRANSFER_FUNCTION_SELECTOR + data)
    voucher = {"destination": token_address, "payload": voucher_payload}
    return voucher

def process_deposit(rollup: Rollup, data: RollupData) -> dict:
    binary = hex2bin(data.payload)

    erc20_deposit = decode_erc20_deposit(binary)

    token_address = erc20_deposit["token_address"]
    depositor = erc20_deposit["depositor"]
    amount = erc20_deposit["amount"]

    if token_address.lower() != settings.accepted_erc20_token.lower():  
        voucher = create_erc20_transfer_voucher(token_address,depositor,amount)
        LOGGER.info(f"Token not accepted, sending it back, voucher {voucher}")
        rollup.voucher(voucher)
        return True

    # add to wallet
    try: 
        bank.deposit(depositor,amount)
    except Exception as e:
        msg = f"Could not deposit {amount} for user {depositor}. Error: {e}"
        LOGGER.error(msg)
        rollup.report(str2hex(msg))
        return False

    # send notice with current balance
    rollup.notice(str2hex(f"{{\"action\":\"deposit\",\"address\":\"{depositor}\",\"balance\":\"{bank.balance(depositor)}\"}}"))

    return True


class Settings(BaseSettings):
    PORTAL_ERC20_ADDRESS: str = "0x9C21AEb2093C32DDbC53eEF24B873BDCd1aDa1DB"
    TOKEN_ERC20_ADDRESS: str = "0xc6e7DF5E7b4f2A278906862b61205850344D4e7d" #"0x4A679253410272dd5232B3Ff7cF5dbB88f295319"
    ERC20_TRANSFER_FUNCTION_SELECTOR = b'\xa9\x05\x9c\xbb'

settings = Settings()


##################
# Testing Routes #
##################


@url_router.advance("hello/")
def hello_world_advance(rollup: Rollup, data: RollupData) -> bool:
    rollup.notice(str2hex("Hello World"))
    return True


@url_router.inspect("hello/")
def hello_world_inspect(rollup: Rollup, data: RollupData) -> bool:
    rollup.report(str2hex("Hello World"))
    return True


@json_router.advance({"hello": "world"})
def handle_advance_set(rollup: Rollup, data: RollupData):
    data = data.json_payload()
    key = data["key"]
    value = data["value"]

    STATE[key] = value

    rollup.report(to_jsonhex({"key": key, "value": value}))
    return True


#######################
# default claim route #
#######################


@dapp.advance()
def default_handler(rollup: Rollup, data: RollupData) -> bool:
    LOGGER.info("Running Default Handler")

    # handle deposits
    if data.metadata.msg_sender.lower() == settings.ERC20_PORTAL_ADDRESS.lower():   
        LOGGER.info(f"Processing Erc20 deposit: {rollup}\n{data}") 
        return process_deposit(rollup, data)

    msg = ("Nothing to do here")
    LOGGER.warning(msg)
    rollup.report(str2hex(msg))
    return False



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
    claim_id = data.get("id")
    claim_value_float = data.get("value")

    if (
        claim_id is None
        or not isinstance(claim_value_float, float)
        or claim_value_float > 1000000
    ):
        message = "HandleClaim: Not enough parameters, you must provide string 'id' and float 'value'"
        rollup.report(
            to_jsonhex({"error": message})
        )  # Reporting the error in JSON hex format
        raise ValueError(message)

    claim_value = int(claim_value_float)

    # Check if claim already exists
    if claim_id in claims:
        raise ValueError("HandleClaim: Claim already exists")

    claim = {
        "Status": Status.OPEN,
        "Value": claim_value,
        "timestamp": data[
            "timestamp"
        ],  
        "compProof": data["comp_hash"],
        "compCID": data["comp_cid"],
        "UserAddress": data[
            "msg_sender"
        ],  
    }
    claims[claim_id] = claim
    user = get_user(data["msg_sender"])  # Assuming get_user is defined elsewhere
    user["OpenClaims"][claim_id] = None

    rollup.report(to_jsonhex({"key": claim_id, "claim": claim}))  # Reporting success
    return True


# Global state dictionary
claims = {}


if __name__ == "__main__":
    dapp.run()
