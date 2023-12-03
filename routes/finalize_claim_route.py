import logging
from typing import Optional
from cartesi import Rollup, RollupData


from model.bank_db import bank_db
from model.claims_db import claims_db, Status, Claim
from model.user_db import users_db
from helpers.setting import settings
from helpers.inputs import FinalizeInput

# Configure logging
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def finalize_claim(json_router):
    # def decode_finalize_input(data: RollupData):
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

    #     claim_id:int = int(decoded_data.get("claimID"))
    #     prep_CID = decoded_data.get("prep_CID")

    #     """
    #     Example Payload:
    #     {
    #         "handle": "finalize",
    #         "claimID": "12345",
    #         "prep_CID": "QmExampleCID"
    #     }
    #     """

    #     return {claim_id, prep_CID}


    @json_router.advance({"handle": "finalize"})
    def handle_finalize(rollup: Rollup, data: RollupData):
        LOGGER.info(f"Handling Finalize: {data}")

        # Extracting claim ID and prep_CID from the payload
        # claim_id, prep_CID = decode_finalize_input(data)
        payload = FinalizeInput.parse_obj(data.json_payload())
        
        if not (payload.claimID or payload.prep_CID):
            error_message = "❌ Not enough parameters, you must provide string 'claimID' and prep_CID"
            # Assuming a similar method to send reports or handle errors
            rollup.report(error_message)
            raise ValueError(error_message)

        # Check if claim exists
        claim: Optional[Claim] = claims_db.get_claim(payload.claimID)
        if not claim:
            msg = "❌ Claim doesn't exist"
            rollup.report(msg)
            raise ValueError(msg)

        if claim.status == Claim.OPEN:
            # Check if enough time passed
            if data.metadata.timestamp < claim.last_edited + settings.CLAIM_EPOCH:
                seconds_to_accept = (
                    claim.last_edited + settings.CLAIM_EPOCH - data.metadata.timestamp
                )
                msg = f"❌ Claim can't be finalized yet, {seconds_to_accept} more seconds to go"
                rollup.report(msg)
                raise ValueError(msg)

            # Finalize claim
            # finalized_claim = claims_db.finalize_claim(claim_id, Status.FINALIZED)
            claims_db.finalize_claim(payload.claimID, Status.FINALIZED)

            user = users_db.get_user(claim.user_address)
            user.total_claims += 1
            user.correct_claims += 1
            user.open_claims.pop(payload.claimID, None)
            msg = f"✅ Claimer DB updated: {user}"
            LOGGER.info(msg)
            
            # Transfer collateral and incentive to the claimer
            bank_db.transfer(settings.LOCKED_ASSET_ADDRESS, claim.user_address, settings.COLLATERAL_AMOUNT+settings.CLAIM_INCENTIVE)
            msg = "✅ Collateral transfered to the claimer"
            LOGGER.info(msg)

        elif claim.status == Claim.DISPUTING:
            # finalizing disputing claims is always lost dispute
            
            # Check if enough time passed
            if data.metadata.timestamp < claim.last_edited + settings.DISPUTE_EPOCH:
                seconds_to_accept = (
                    claim.last_edited + settings.DISPUTE_EPOCH - data.metadata.timestamp
                )
                msg = "❌ Claim can't be finalized yet, {seconds_to_accept} more seconds to go"
                rollup.report(msg)
                raise ValueError(msg)

            # Finalize claim
            claims_db.finalize_claim(payload.claimID, Status.DISPUTED)


            user = users_db.get_user(claim.user_address)
            user.total_claims += 1
            user.total_disputes += 1
            user.open_disputes.pop(payload.claimID, None)
            msg = f"✅ Claim user DB updated: {user}"
            LOGGER.info(msg)

            disputing_user = users_db.get_user(claim.disputing_user_address)
            disputing_user.total_disputes += 1
            disputing_user.won_disputes += 1
            msg = f"✅ Disputing user DB updated: {disputing_user}"
            LOGGER.info(msg)
            
            # Transfer Collateral to the disputer
            bank_db.transfer(settings.LOCKED_ASSET_ADDRESS, claim.disputing_user_address, settings.COLLATERAL_AMOUNT)
            msg = "✅ Collateral transfered to the disputer"
            LOGGER.info(msg)

        else:
            msg = "❌ Can only finalize Open or Disputing claims"
            rollup.report(msg)
            raise ValueError(msg)

        # Generate notice of finalization
        rollup.notice(f"Claim finalized!! Claim ID: {payload.claimID}, Claim: {claims_db.get_claim(payload.claimID)}")
        return True
