import logging
from helpers.utils import to_jsonhex
from cartesi import Rollup, RollupData

from model.bank_db import bank_db
from model.claims_db import claims_db, Status
from helpers.setting import settings
from helpers.inputs import DisputeInput
from model.user_db import users_db

# Configure logging
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def generate_dispute(json_router):
    # def decode_dispute_input(data: RollupData):
    #     """
    #     Decodes the JSON payload from the RollupData object to extract fields required for handling a dispute.
    #     Fields extracted include the claim ID, staking amount, and preparation CID.

    #     Args:
    #         data (RollupData): The RollupData object containing the JSON payload.

    #     Returns:
    #         dict: A dictionary containing the extracted fields: claim_id, staking_amount, and prep_CID.
    #     """
        
    #     # Extracting fields from payload
    #     decoded_data: dict = data.json_payload()

    #     claim_id = decoded_data.get("claimID")
    #     staking_amount = decoded_data.get("stakingAmount")
    #     prep_CID = decoded_data.get("prep_CID")

    #     """
    #     Example Payload:
    #     {
    #         "handle": "dispute",
    #         "claimID": "12345",
    #         "stakingAmount": "400000000000000000",
    #         "prep_CID": "QmExampleCID"
    #     }
    #     """

    #     return {
    #         "claim_id": claim_id,
    #         "staking_amount": staking_amount,
    #         "prep_CID": prep_CID,
    #     }

    def check_validator_stake(address: str, staking_amount: int):
        """
        Checks if the validator's wallet has enough balance to cover the required stake amount.
        Additionally, verifies if the provided staking amount matches the required validator staking amount.

        Args:
            address (str): The wallet address of the validator.
            staking_amount (int): The amount of stake provided for validation.

        Returns:
            tuple: A tuple containing a boolean (True if conditions are met, False otherwise) and a message string.
        """
        
        try:
            current_balance = bank_db.balance(address)
            if current_balance < settings.VALIDATOR_STAKING:
                msg = "Insufficient funds for staking"
                LOGGER.error(
                    f"{msg}. Required: {settings.VALIDATOR_STAKING}, Available: {current_balance}"
                )
                return False, msg
            elif staking_amount != settings.VALIDATOR_STAKING:
                msg = "Staking Amount is not equal to the required Validator Staking Amount."
                LOGGER.error(
                    f"{msg} Required: {settings.VALIDATOR_STAKING}, Staking Amount: {staking_amount}"
                )
                return False, msg
            LOGGER.info(
                f"Sufficient funds for staking. Required: {settings.VALIDATOR_STAKING}, Available: {current_balance}"
            )
            return True, ""
        except Exception as e:
            LOGGER.error(f"Error checking validator stake: {e}")
            raise

    def check_claim_exists_and_verify_CID(claim_id: str, expected_prep_CID: str):
        """
        Verifies if a claim exists in the database with the given ID and if it has the expected preparation CID.

        Args:
            claim_id (str): The ID of the claim to check.
            expected_prep_CID (str): The expected preparation CID associated with the claim.

        Returns:
            tuple: A tuple containing a boolean (True if claim exists with matching prep_CID, False otherwise) and a message string.
        """
        
        try:
            claim = claims_db.get_claim(claim_id)
            if claim is None:
                msg = f"No claim found with ID: {claim_id}"
                LOGGER.info(msg)
                return False, msg
            if claim.prep_CID != expected_prep_CID:
                msg = f"Claim with ID: {claim_id} found, but prep_CID does not match. Expected: {expected_prep_CID}, Found: {claim.prep_CID}"
                LOGGER.info(msg)
                return False, msg
            LOGGER.info(
                f"Claim found with ID: {claim_id} and matching prep_CID: {expected_prep_CID}"
            )
            return True, ""
        except Exception as e:
            LOGGER.error(f"Error checking if claim exists and verifying prep_CID: {e}")
            # Depending on your error handling strategy, you might raise the exception or return False
            raise

    def check_claim_eligible_for_dispute(claim_id: str, disputing_party_address: str):
        """
        Checks if a claim is eligible for dispute by verifying its status and ensuring the claim is not raised by the disputing party.

        Args:
            claim_id (str): The ID of the claim to check.
            disputing_party_address (str): The wallet address of the party initiating the dispute.

        Returns:
            tuple: A tuple containing a boolean (True if the claim is eligible for dispute, False otherwise) and a message string.
        """
        
        try:
            claim = claims_db.get_claim(claim_id)
            # Check if Status is Open
            if claim.status != Status.OPEN:
                msg = f"Claim with ID: {claim_id} found, but status '{claim.status}' is not eligible for dispute."
                LOGGER.info(msg)
                return False, msg
            # Verify not a self dispute
            if claim.user_address == disputing_party_address:
                msg = "Cannot dispute own claim"
                LOGGER.info(msg)
                return False, msg
            LOGGER.info(
                f"Claim with ID: {claim_id} is in an eligible status ('OPEN') for dispute."
            )
            return True
        except Exception as e:
            LOGGER.error(f"Error checking claim status: {e}")
            raise

    def transfer_stake_to_locked_account(user_wallet_address: str, stake_amount: int):
        """
        Transfers the required stake amount from the user's wallet to a locked account for staking purposes.

        Args:
            user_wallet_address (str): The wallet address of the user initiating the dispute.
            stake_amount (int): The amount of stake to be transferred.

        Returns:
            tuple: A tuple containing a boolean (True if the transfer is successful, False otherwise) and a message string.
        """
        
        try:
            if bank_db.balance(user_wallet_address) < stake_amount:
                msg = f"Insufficient funds for staking in user's wallet. Required: {stake_amount}, Available: {bank_db.balance(user_wallet_address)}"
                LOGGER.error(msg)
                return False, msg

            bank_db.transfer(
                user_wallet_address, settings.LOCKED_ASSET_ADDRESS, stake_amount
            )
            LOGGER.info(
                f"Transferred {stake_amount} from {user_wallet_address} to locked account {settings.LOCKED_ASSET_ADDRESS}"
            )
            return True, ""
        except Exception as e:
            LOGGER.error(f"Failed to transfer stake to locked account: {e}")
            return False

    @json_router.advance({"handle": "dispute"})
    def handle_dispute(rollup: Rollup, data: RollupData):
        """
        Handles the dispute request by executing several validation checks, transferring the required stake to a locked account,
        and updating the claim status in the database to reflect the dispute.

        Args:
            rollup (Rollup): The Rollup context.
            data (RollupData): Data related to the dispute request.

        Returns:
            bool: True if the dispute handling process is successful, False otherwise.
        """

        LOGGER.debug(f"Handling Dispute: {data}")

        # Decode Input
        payload = DisputeInput.parse_obj(data.json_payload())
        # decoded = decode_dispute_input(data)
        # claim_id, staking_amount, prep_CID = (
        #     decoded["claim_id"],
        #     decoded["staking_amount"],
        #     decoded["prep_CID"],
        # )

        # Check Balance for Validator Stake
        disputing_party_address = data.metadata.msg_sender
        valid, message = check_validator_stake(disputing_party_address, payload.staking_amount)
        if not valid:
            rollup.report(to_jsonhex({"error": message}))
            return False
        LOGGER.info("✅ Staking Amount Check")

        # Check if Claim Exists and Verify prep_CID
        valid, message = check_claim_exists_and_verify_CID(payload.claimID, payload.prep_CID)
        if not valid:
            rollup.report(to_jsonhex({"error": message}))
            return False
        LOGGER.info("✅ Claim and Preprocced CID Check")

        # Check Claim Eligibility for Dispute
        valid, message = check_claim_eligible_for_dispute(
            payload.claimID, disputing_party_address
        )
        if not valid:
            rollup.report(to_jsonhex({"error": message}))
        LOGGER.info("✅ Claim Status Check")

        # Transfer Balance to Lock Account
        valid, message = transfer_stake_to_locked_account(
            disputing_party_address, payload.staking_amount
        )
        if not valid:
            rollup.report(to_jsonhex({"error": message}))
        LOGGER.info("✅ Amount Stake Check")

        # Initiate Dispute on Claim
        updated_claim = claims_db.initiate_dispute(payload.claimID, disputing_party_address)
        if updated_claim is None:
            rollup.report(to_jsonhex({"error": "Failed to initiate dispute on claim"}))
            return False
        LOGGER.info("✅ Update Claim Check")
        
        # Update user db of claimer
        update_user = users_db.get_user(claims_db.get_claim(payload.claimID).user_address)
        update_user.open_disputes[payload.claimID] = None
        del update_user.open_claims[payload.claimID]
        LOGGER.info("✅ Update User DB Check")

        rollup.report(
            f"Dispute initiated on claim ID {payload.claimID} by user {disputing_party_address}\nTime Left to resolve dispute: {settings.DISPUTE_EPOCH}"
        )

        return True
