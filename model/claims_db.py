# from pydantic import BaseModel, Field
from typing import Dict, List, Optional
# from enum import Enum

from .model import Claim, Status, DataChunks

class ClaimsDatabase:
    def __init__(self):
        self.claims: Dict[int, Claim] = {}
        self.latest_id: int = 0

    def create_claim(self, user_address: str, value: int, data_chunks: Optional[DataChunks] = None) -> Claim:
        """
        Creates a new claim and adds it to the database.
        """
        self.latest_id += 1
        new_claim = Claim(
            user_address=user_address,
            disputing_user_address=None,
            value=value,
            last_edited=... , # Insert the current timestamp here
            status=Status.OPEN,
            data_chunks=data_chunks
        )
        self.claims[self.latest_id] = new_claim
        return new_claim

    def initiate_dispute(self, claim_id: int, disputing_user_address: str, reason: str) -> Optional[Claim]:
        """
        Initiates a dispute on a specific claim.
        """
        claim = self.claims.get(claim_id)
        if claim:
            claim.disputing_user_address = disputing_user_address
            claim.status = Status.DISPUTING
            claim.last_edited = ... # Insert the current timestamp here
            # You might also want to add the dispute reason to the claim
            return claim
        return None

    def finalize_claim(self, claim_id: int, final_status: Status) -> Optional[Claim]:
        """
        Finalizes a claim with a given status.
        """
        claim = self.claims.get(claim_id)
        if claim:
            claim.status = final_status
            claim.last_edited = ... # Insert the current timestamp here
            return claim
        return None

    def get_claim(self, claim_id: int) -> Optional[Claim]:
        """
        Retrieves a claim by its ID.
        """
        return self.claims.get(claim_id)

    def get_all_claims(self) -> List[Claim]:
        """
        Retrieves all claims in the database.
        """
        return list(self.claims.values())

    # Additional methods can be added as needed for your application
