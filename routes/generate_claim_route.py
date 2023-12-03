import logging

from helpers.utils import to_jsonhex
from cartesi import Rollup, RollupData

from model.bank_db import bank_db

from model.user_db import users_db
from model.claims_db import claims_db

from helpers.setting import settings
from helpers.inputs import ClaimInput


LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def generate_claim(json_router):
    # def decode_payload(decoded_data, data: RollupData):
    #     """
    #     Decodes the JSON payload from the data and extracts necessary fields.

    #     Args:
    #         data (RollupData): The data object containing the JSON payload.

    #     Returns:
    #         dict: A dictionary containing extracted fields from the payload.
    #     """
    #     prep_CID = decoded_data.get("cidPrep")
    #     comp_CID = decoded_data.get("cidComp")
    #     collateral = decoded_data.get("coll")
    #     comp_proof = decoded_data.get("compProof")
    #     user_wallet_address = data.metadata.msg_sender
    #     timestamp = data.metadata.timestamp

    #     """ Example:
    #     {"handle": "claim","cidPrep": "QmdsL7GxAPRbYh9U7mG6ctnjhbChC7Yws4oriSxUafQ41R","cidComp": "QmdsL7GxAPRbYh9U7mG6ctnjhbChC7Yws4oriSxUafQ41R","coll": "1000000000000000000","compProof": "QmdsL7GxAPRbYh9U7mG6ctnjhbChC7Yws4oriSxUa"}
    #     """

    #     return {
    #         "prep_CID": prep_CID,
    #         "comp_CID": comp_CID,
    #         "collateral": collateral,
    #         "comp_proof": comp_proof,
    #         "user_wallet_address": user_wallet_address,
    #         "timestamp": timestamp,
    #     }

    def validate_collateral(collateral: int):
        if collateral is None or collateral != settings.COLLATERAL_AMOUNT:
            message = f"Collateral amount should be equal {settings.COLLATERAL_AMOUNT}"
            return False, message
        return True, ""

    def check_existing_claim(prep_CID: str):
        if claims_db.get_claim_by_prep_CID(prep_CID):
            return False, "Claim already exists"
        return True, ""

    def check_and_lock_funds(user_wallet_address: str):
        if bank_db.balance(user_wallet_address) < settings.COLLATERAL_AMOUNT:
            message = f"Insufficient funds for collateral in user's wallet. Current Balance: {bank_db.balance(user_wallet_address)}"
            return False, message

        try:
            bank_db.transfer(
                user_wallet_address,
                settings.LOCKED_ASSET_ADDRESS,
                settings.COLLATERAL_AMOUNT,
            )
            return True, ""
        except Exception as e:
            return False, f"Failed to lock collateral: {e}"

    def create_and_register_claim(
        prep_CID: str,
        user_address: str,
        timestamp: str,
        comp_proof: str,
        comp_CID: str,
        value: int,
    ):
        new_claim_id = claims_db.get_next_claim_id()
        new_claim = claims_db.create_claim(
            prep_CID=prep_CID,
            user_address=user_address,
            timestamp_of_claim=timestamp,  # Ensure this is correctly formatted
            comp_proof=comp_proof,
            comp_CID=comp_CID,
            value=value,
        )
        return new_claim_id, new_claim

    def update_user_open_claims(user_wallet_address: str, new_claim_id: int):
        user = users_db.get_user(user_wallet_address)
        if user:
            user.open_claims[str(new_claim_id)] = None
            users_db.update_user(user_wallet_address, open_claims=user.open_claims)

    @json_router.advance({"handle": "claim"})
    def handle_claim(rollup: Rollup, data: RollupData):
        LOGGER.info(f"Handling Claim: {data}")
        payload = ClaimInput.parse_obj(data.json_payload())        

        # 1. Validate Collateral
        valid, message = validate_collateral(payload.collateral)
        if not valid:
            rollup.report(to_jsonhex({"error": message}))
            return False
        LOGGER.info("✅ Collateral Validated")

        # 2. Check Existing Claim
        valid, message = check_existing_claim(payload.CID_prep)
        if not valid:
            rollup.report(to_jsonhex({"error": message}))
            return False
        LOGGER.info("✅ Checked Existing Claims")

        # 3. Check and Lock Funds
        valid, message = check_and_lock_funds(data.metadata.msg_sender)
        if not valid:
            rollup.report(to_jsonhex({"error": message}))
            return False
        LOGGER.info("Funds locked")

        # 4. Create and Register Claim
        new_claim_id, new_claim = create_and_register_claim(
            payload.prep_CID,
            data.metadata.msg_sender,
            data.metadata.timestamp,
            payload.comp_proof,
            payload.comp_CID,
            int(payload.collateral),
        )
        LOGGER.info("✅ Claim created")

        # 5. Update User Open Claims
        update_user_open_claims(data.metadata.msg_sender, new_claim_id)
        LOGGER.info("Updated user database with open claim")

        rollup.notice(to_jsonhex({"key": new_claim_id, "claim": new_claim.dict()}))
        return True
