import json
from eth_abi import encode
from .setting import settings

def str2hex(string: str) -> str:
    """Encodes a string as a hex string"""
    return "0x" + string.encode("utf-8").hex()

def to_jsonhex(data: dict) -> str:
    """Encode as a JSON hex"""
    return str2hex(json.dumps(data))

def hex2bin(hexstr: str) -> bytes:
    """Converts a hex string to binary"""
    return bytes.fromhex(hexstr[2:])

def bin2hex(binary: bytes) -> str:
    """Converts binary data to a hex string"""
    return "0x" + binary.hex()

def decode_erc20_deposit(binary: bytes) -> dict:
    """Decodes ERC20 deposit data from binary format"""
    token_address = binary[1:21]
    depositor = binary[21:41]
    amount = int.from_bytes(binary[41:73], "big")
    data = binary[73:]
    return {
        "depositor": bin2hex(depositor),
        "token_address": bin2hex(token_address),
        "amount": amount,
        "data": data,
    }

def create_erc20_transfer_voucher(token_address: str, receiver: str, amount: int) -> dict:
    """Creates an ERC20 transfer voucher"""
    data = encode(["address", "uint256"], [receiver, amount])
    voucher_payload = bin2hex(settings.ERC20_TRANSFER_FUNCTION_SELECTOR + data)
    return {"destination": token_address, "payload": voucher_payload}
