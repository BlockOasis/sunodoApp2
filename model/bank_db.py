from pydantic import BaseModel
import logging

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class Wallet(BaseModel):
    # note: it considers a single asset (and can't change asset)
    owner: str
    balance: int = 0
    # TODO: store pub keys


class BankDatabase:
    def __init__(self):
        self.wallets: dict[str, Wallet] = {}

    def _get_wallet(self, address: str) -> Wallet:
        addr = address.lower()
        wallet = self.wallets.get(addr)
        if wallet is None:
            new_wallet = Wallet(owner=addr)
            self.wallets[addr] = new_wallet
            wallet = new_wallet
        return wallet

    def deposit(self, address: str, amount: int):
        if amount <= 0:
            raise Exception("invalid amount")
        LOGGER.info(f"Depositing amount: {amount} from address: {address}")
        wallet = self._get_wallet(address)
        wallet.balance += amount

    def withdraw(self, address: str, amount: int):
        if amount <= 0:
            raise Exception("invalid amount")
        wallet = self._get_wallet(address)
        if wallet.balance < amount:
            raise Exception("insuficient funds")
        wallet.balance -= amount

    def transfer(self, sender: str, receiver: str, amount: int):
        if amount <= 0:
            raise Exception("invalid amount")
        self.withdraw(sender, amount)
        self.deposit(receiver, amount)

    def balance(self, address: str) -> int:
        wallet = self._get_wallet(address)
        return wallet.balance
bank_db = BankDatabase()
